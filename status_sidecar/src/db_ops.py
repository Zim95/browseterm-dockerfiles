# built-ins
from dataclasses import dataclass
import asyncio

# module
from src.config import DB_CONFIG
from browseterm_db.operations.all_operations import ContainerOps
from browseterm_db.operations import OperationResult
from browseterm_db.models.containers import ContainerStatus


container_ops: ContainerOps = ContainerOps(DB_CONFIG)


@dataclass
class UpdateContainerStatus:
    container_id: str  # The id of the container in the database.
    network: str  # The network of the container.
    status: str  # The status of the container.

    def validate(self) -> None:
        if not self.container_id:
            raise ValueError("Container ID is required")
        if not self.network:
            raise ValueError("Network is required")
        if not self.status:
            raise ValueError("Status is required")


async def update_container_status(update_container_status: UpdateContainerStatus) -> OperationResult:
    try:
        update_container_status.validate()
        result: OperationResult = await asyncio.to_thread(
            container_ops.update,
            filters={
                "container_id": update_container_status.container_id,
                "network": update_container_status.network,
            },
            data={
                "status": ContainerStatus(update_container_status.status),
            }
        )
        return result
    except ValueError as e:
        print(f"Error validating update container status: {e}")
        return OperationResult(success=False, error=str(e))
    except Exception as e:
        print(f"Error updating container status: {e}")
        return OperationResult(success=False, error=str(e))
