"""DB operations for the reaper: find idle RUNNING containers, mark them HIBERNATED.

Idle detection uses browseterm-db's ContainerOps.find_idle_containers, which filters on the
last_active_at column (stamped by socket-ssh on WS activity) — the real activity signal.
"""
import asyncio
from typing import List, Dict, Any

from browseterm_db.operations.all_operations import ContainerOps
from browseterm_db.operations import OperationResult
from browseterm_db.common.config import DBConfig
from browseterm_db.models.containers import ContainerStatus


async def find_idle_running_containers(
    db_config: DBConfig, idle_threshold_seconds: int
) -> List[Dict[str, Any]]:
    """Return RUNNING containers idle (no activity) for longer than the threshold."""
    container_ops = ContainerOps(db_config)
    result: OperationResult = await asyncio.to_thread(
        container_ops.find_idle_containers, idle_threshold_seconds
    )
    if not result.success:
        raise RuntimeError(f"Failed to query idle containers: {result.error}")
    return result.data or []


async def mark_hibernated(db_config: DBConfig, container_id: str) -> OperationResult:
    """Set a container's status to HIBERNATED."""
    if not container_id:
        return OperationResult(success=False, error="Container ID is required")
    container_ops = ContainerOps(db_config)
    return await asyncio.to_thread(
        container_ops.update,
        filters={"id": container_id},
        data={"status": ContainerStatus.HIBERNATED},
    )
