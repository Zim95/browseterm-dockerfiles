# built-ins
import asyncio
import os
from typing import Callable

# third-party
from kubernetes_asyncio import client, config, watch

# module
from src.common.logging_setup import get_logger
from src.db_ops import UpdateContainerStatus
from src.config import CONTAINER_ID

# browseterm-db
from browseterm_db.operations import OperationResult


logger = get_logger("pod_watcher")


async def get_pod_info() -> tuple[str, str]:
    """Get the current pod's name and namespace."""
    # Get pod name from hostname (in K8s, hostname equals pod name)
    pod_name: str = os.getenv("POD_NAME") or os.getenv("HOSTNAME") or open("/etc/hostname").read().strip()

    # Get namespace from mounted service account secret
    namespace_file: str = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
    namespace: str = ""
    if os.path.exists(namespace_file):
        with open(namespace_file, "r") as f:
            namespace = f.read().strip()
    else:
        namespace = os.getenv("POD_NAMESPACE", "default")
    return pod_name, namespace


async def watch_pod_status(callback: Callable) -> None:
    """Watch the current pod and print status changes."""
    # Load in-cluster configuration
    try:
        config.load_incluster_config()
        logger.info("Loaded in-cluster configuration", extra={"container_id": CONTAINER_ID})
    except Exception as e:
        logger.warning(
            "Failed to load in-cluster config, trying kubeconfig: %s", e,
            exc_info=True,
            extra={"container_id": CONTAINER_ID},
        )
        await config.load_kube_config()

    # Get current pod information
    pod_name, namespace = await get_pod_info()
    logger.info(
        "Watching pod: %s in namespace: %s", pod_name, namespace,
        extra={"container_id": CONTAINER_ID, "pod_name": pod_name, "namespace": namespace},
    )

    # Create API client
    v1: client.CoreV1Api = client.CoreV1Api()

    # Keep watching indefinitely with retry logic
    retry_delay: int = 5
    while True:
        try:
            # Watch the specific pod
            w: watch.Watch = watch.Watch()
            logger.info(
                "Starting watch stream for pod %s...", pod_name,
                extra={"container_id": CONTAINER_ID, "pod_name": pod_name, "namespace": namespace},
            )
            async for event in w.stream(
                func=v1.list_namespaced_pod,
                namespace=namespace,
                field_selector=f"metadata.name={pod_name}",
                timeout_seconds=0
            ):
                pod: client.V1Pod = event['object']
                update_container_status: UpdateContainerStatus = UpdateContainerStatus(
                    container_id=CONTAINER_ID,
                    status=pod.status.phase
                )
                logger.info(
                    "Updating container status: %s", update_container_status,
                    extra={
                        "container_id": CONTAINER_ID,
                        "pod_name": pod_name,
                        "namespace": namespace,
                        "status": pod.status.phase,
                    },
                )
                result: OperationResult = await callback(update_container_status)
                if not result.success:
                    logger.error(
                        "Error updating container status: %s", result.error,
                        extra={
                            "container_id": CONTAINER_ID,
                            "pod_name": pod_name,
                            "namespace": namespace,
                            "status": pod.status.phase,
                        },
                    )
                logger.info(
                    "Container status updated",
                    extra={
                        "container_id": CONTAINER_ID,
                        "pod_name": pod_name,
                        "namespace": namespace,
                        "status": pod.status.phase,
                    },
                )
        except asyncio.CancelledError:
            logger.info("Watch task cancelled, shutting down...", extra={"container_id": CONTAINER_ID})
            break
        except Exception as e:
            logger.error(
                "Error watching pod: %s", e,
                exc_info=True,
                extra={"container_id": CONTAINER_ID, "pod_name": pod_name, "namespace": namespace},
            )
            logger.info(
                "Retrying in %s seconds...", retry_delay,
                extra={"container_id": CONTAINER_ID},
            )
            await asyncio.sleep(retry_delay)
            continue
    await v1.api_client.close()
