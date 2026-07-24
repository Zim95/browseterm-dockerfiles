"""Database operations for updating saved image information."""
import asyncio
from datetime import datetime, timezone
from typing import Optional

from browseterm_db.operations.all_operations import ContainerOps
from browseterm_db.operations import OperationResult
from browseterm_db.common.config import DBConfig

from src.common.logging_setup import get_logger

logger = get_logger("db_ops")


async def update_saved_image(
    db_config: DBConfig,
    container_id: str,
    saved_image: str
) -> OperationResult:
    """
    Update the saved_image field in the database for a container.
    
    This follows the same pattern as the status_sidecar's database updates.
    
    :param db_config: Database configuration
    :param container_id: UUID of the container in the database
    :param saved_image: Name of the saved Docker image (e.g., "mycontainer-pod-image:latest")
    :return: OperationResult indicating success or failure
    """
    try:
        if not container_id:
            return OperationResult(
                success=False,
                error="Container ID is required"
            )
        
        if not saved_image:
            return OperationResult(
                success=False,
                error="Saved image name is required"
            )
        
        # Create container operations instance
        container_ops = ContainerOps(db_config)
        
        # Update the database
        result = await asyncio.to_thread(
            container_ops.update,
            filters={"id": container_id},
            data={"saved_image": saved_image}
        )
        
        if result.success:
            logger.info(
                "Successfully updated saved_image",
                extra={"container_id": container_id, "saved_image": saved_image},
            )
        else:
            logger.error(
                "Failed to update saved_image",
                extra={"container_id": container_id, "error": result.error},
            )

        return result

    except ValueError as e:
        error_msg = f"Validation error: {str(e)}"
        logger.error("Validation error updating saved_image", exc_info=True, extra={"container_id": container_id})
        return OperationResult(success=False, error=error_msg)

    except Exception as e:
        error_msg = f"Unexpected error updating database: {str(e)}"
        logger.error("Unexpected error updating saved_image", exc_info=True, extra={"container_id": container_id})
        return OperationResult(success=False, error=error_msg)


async def update_save_status(
    db_config: DBConfig,
    container_id: str,
    save_status: str,
    saved_image: Optional[str] = None,
    save_error: Optional[str] = None,
    set_last_saved: bool = False,
) -> OperationResult:
    """
    Update the container's save-flow state.

    Always sets save_status and save_error (save_error=None clears any previous error);
    optionally sets saved_image and last_saved_at. The container_save_status_change trigger
    fires the NOTIFY that browseterm-server relays to the frontend over SSE.

    :param save_status: one of SaveStatus values ("Pending"/"Running"/"Succeeded"/"Failed")
    """
    try:
        if not container_id:
            return OperationResult(success=False, error="Container ID is required")

        data = {"save_status": save_status, "save_error": save_error}
        if saved_image is not None:
            data["saved_image"] = saved_image
        if set_last_saved:
            data["last_saved_at"] = datetime.now(timezone.utc)

        container_ops = ContainerOps(db_config)
        result = await asyncio.to_thread(
            container_ops.update,
            filters={"id": container_id},
            data=data,
        )
        if result.success:
            logger.info(
                "Updated save state",
                extra={"container_id": container_id, "save_status": save_status},
            )
        else:
            logger.error(
                "Failed to update save state",
                extra={"container_id": container_id, "error": result.error},
            )
        return result

    except Exception as e:
        error_msg = f"Unexpected error updating save state: {str(e)}"
        logger.error("Unexpected error updating save state", exc_info=True, extra={"container_id": container_id})
        return OperationResult(success=False, error=error_msg)
