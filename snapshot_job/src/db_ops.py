"""Database operations for updating saved image information."""
import asyncio
from typing import Optional

from browseterm_db.operations.all_operations import ContainerOps
from browseterm_db.operations import OperationResult
from browseterm_db.common.config import DBConfig


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
            print(f"Successfully updated database: container {container_id} -> saved_image: {saved_image}")
        else:
            print(f"Failed to update database: {result.error}")
        
        return result
        
    except ValueError as e:
        error_msg = f"Validation error: {str(e)}"
        print(error_msg)
        return OperationResult(success=False, error=error_msg)
    
    except Exception as e:
        error_msg = f"Unexpected error updating database: {str(e)}"
        print(error_msg)
        return OperationResult(success=False, error=error_msg)
