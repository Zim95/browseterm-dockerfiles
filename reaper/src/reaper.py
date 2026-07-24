"""Reaper: hibernate idle RUNNING containers.

For each idle RUNNING container:
  1. container-maker.saveContainer   -> snapshot the pod's filesystem to an image
  2. container-maker.deleteContainer -> delete the pod to free cluster resources
  3. DB status -> HIBERNATED
Failures are isolated per container so one bad container doesn't abort the sweep; a run summary
is returned and printed.
"""
import asyncio
from dataclasses import dataclass, field
from typing import List

import grpc
from container_maker_spec.service_pb2_grpc import ContainerMakerAPIStub
from container_maker_spec.types_pb2 import SaveContainerRequest as GRPCSaveContainerRequest
from container_maker_spec.types_pb2 import DeleteContainerRequest as GRPCDeleteContainerRequest

from src.config import (
    DB_CONFIG, NAMESPACE, CONTAINER_MAKER_HOST, CONTAINER_MAKER_PORT,
    CONTAINER_MAKER_CERTS_SECRET_NAME, IDLE_THRESHOLD_SECONDS,
)
from src.db_ops import find_idle_running_containers, mark_hibernated
from src.grpc_utils import GRPCUtils
from src.k8s_secrets import read_cert_from_k8s_secret
from src.logging_setup import get_logger, request_id_var

logger = get_logger("reaper")


def network_name_for(container_row: dict) -> str:
    """Mirror the server convention: network_name == f'{user_id}-namespace'."""
    return f"{container_row['user_id']}-namespace"


@dataclass
class RunSummary:
    scanned: int = 0
    hibernated: int = 0
    failed: int = 0
    errors: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (f"scanned={self.scanned} hibernated={self.hibernated} failed={self.failed}")


class Reaper:
    def __init__(self) -> None:
        # mTLS client certs from the k8s secret (same pattern as browseterm-server).
        client_key = read_cert_from_k8s_secret(CONTAINER_MAKER_CERTS_SECRET_NAME, NAMESPACE, 'client.key')
        client_cert = read_cert_from_k8s_secret(CONTAINER_MAKER_CERTS_SECRET_NAME, NAMESPACE, 'client.crt')
        ca_cert = read_cert_from_k8s_secret(CONTAINER_MAKER_CERTS_SECRET_NAME, NAMESPACE, 'ca.crt')
        self.grpc_utils = GRPCUtils(
            host=CONTAINER_MAKER_HOST, port=CONTAINER_MAKER_PORT,
            stub_class=ContainerMakerAPIStub, secure=True,
            client_key=client_key, client_cert=client_cert, ca_cert=ca_cert,
        )
        self.stub: ContainerMakerAPIStub = self.grpc_utils.stub

    async def _hibernate_one(self, row: dict, summary: RunSummary) -> None:
        container_id = row["id"]
        net = network_name_for(row)
        try:
            # gRPC metadata carries this reaper run's request_id so the save/delete it triggers are
            # traceable back to the reaper run in the logs.
            md = (("x-request-id", request_id_var.get()),)
            # 1. save (blocks until the snapshot Job finishes inside container-maker)
            await asyncio.to_thread(
                self.stub.saveContainer,
                GRPCSaveContainerRequest(container_id=container_id, network_name=net),
                metadata=md,
            )
            # 2. delete the pod / container resources (Service is left so resume can re-route)
            await asyncio.to_thread(
                self.stub.deleteContainer,
                GRPCDeleteContainerRequest(container_id=container_id, network_name=net),
                metadata=md,
            )
            # 3. mark HIBERNATED
            result = await mark_hibernated(DB_CONFIG, container_id)
            if not result.success:
                raise RuntimeError(f"DB update failed: {result.error}")
            summary.hibernated += 1
            logger.info("hibernated container", extra={"container_id": container_id})
        except grpc.RpcError as e:
            summary.failed += 1
            msg = f"{container_id}: gRPC error {e.code()}: {e.details()}"
            summary.errors.append(msg)
            logger.error("hibernate failed (gRPC)", extra={"container_id": container_id}, exc_info=True)
        except Exception as e:  # isolate failures per container
            summary.failed += 1
            msg = f"{container_id}: {e}"
            summary.errors.append(msg)
            logger.error("hibernate failed", extra={"container_id": container_id}, exc_info=True)

    async def run(self) -> RunSummary:
        summary = RunSummary()
        idle = await find_idle_running_containers(DB_CONFIG, IDLE_THRESHOLD_SECONDS)
        summary.scanned = len(idle)
        logger.info("found idle running containers",
                    extra={"count": summary.scanned, "threshold_seconds": IDLE_THRESHOLD_SECONDS})
        for row in idle:
            await self._hibernate_one(row, summary)
        logger.info("run complete",
                    extra={"scanned": summary.scanned, "hibernated": summary.hibernated, "failed": summary.failed})
        return summary
