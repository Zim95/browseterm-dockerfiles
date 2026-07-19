"""
Test database operations.
"""
# builtins
from unittest import TestCase
from unittest.mock import Mock, patch, AsyncMock
import asyncio

# modules
from src.db_ops import update_saved_image, update_save_status
from browseterm_db.common.config import DBConfig
from browseterm_db.operations import OperationResult


class TestDatabaseOperations(TestCase):
    """
    Test database operations for updating saved images.
    """

    def setUp(self) -> None:
        self.db_config = DBConfig(
            host="testhost",
            port=5432,
            username="testuser",
            password="testpassword",
            database="testdatabase"
        )
        self.container_id = "test-container-123"
        self.saved_image = "test-pod-image:latest"

    def test_update_saved_image_success(self) -> None:
        """
        Test successful database update.
        """
        print('Test: test_update_saved_image_success')
        
        async def run_test():
            with patch('src.db_ops.ContainerOps') as MockContainerOps:
                # Mock successful update
                mock_ops = MockContainerOps.return_value
                mock_ops.update.return_value = OperationResult(
                    success=True,
                    error=None
                )
                
                result = await update_saved_image(
                    db_config=self.db_config,
                    container_id=self.container_id,
                    saved_image=self.saved_image
                )
                
                self.assertTrue(result.success)
                self.assertIsNone(result.error)
                
                # Verify update was called with correct params
                mock_ops.update.assert_called_once_with(
                    filters={"id": self.container_id},
                    data={"saved_image": self.saved_image}
                )
        
        asyncio.run(run_test())
        print('Database update success tested.')

    def test_update_saved_image_missing_container_id(self) -> None:
        """
        Test database update with missing container ID.
        """
        print('Test: test_update_saved_image_missing_container_id')
        
        async def run_test():
            result = await update_saved_image(
                db_config=self.db_config,
                container_id="",
                saved_image=self.saved_image
            )
            
            self.assertFalse(result.success)
            self.assertEqual(result.error, "Container ID is required")
        
        asyncio.run(run_test())
        print('Missing container ID handled correctly.')

    def test_update_saved_image_missing_image_name(self) -> None:
        """
        Test database update with missing image name.
        """
        print('Test: test_update_saved_image_missing_image_name')
        
        async def run_test():
            result = await update_saved_image(
                db_config=self.db_config,
                container_id=self.container_id,
                saved_image=""
            )
            
            self.assertFalse(result.success)
            self.assertEqual(result.error, "Saved image name is required")
        
        asyncio.run(run_test())
        print('Missing image name handled correctly.')

    def test_update_saved_image_database_error(self) -> None:
        """
        Test database update with database error.
        """
        print('Test: test_update_saved_image_database_error')
        
        async def run_test():
            with patch('src.db_ops.ContainerOps') as MockContainerOps:
                # Mock database error
                mock_ops = MockContainerOps.return_value
                mock_ops.update.return_value = OperationResult(
                    success=False,
                    error="Database connection failed"
                )
                
                result = await update_saved_image(
                    db_config=self.db_config,
                    container_id=self.container_id,
                    saved_image=self.saved_image
                )
                
                self.assertFalse(result.success)
                self.assertIn("Database connection failed", result.error)
        
        asyncio.run(run_test())
        print('Database error handled correctly.')


class TestUpdateSaveStatus(TestCase):
    """
    Test update_save_status, which drives the container's save-flow state.
    """

    def setUp(self) -> None:
        self.db_config = DBConfig(
            host="testhost",
            port=5432,
            username="testuser",
            password="testpassword",
            database="testdatabase"
        )
        self.container_id = "test-container-123"

    def test_status_only(self) -> None:
        """
        A status-only update sets save_status and clears save_error (None);
        it must NOT set saved_image or last_saved_at.
        """
        print('Test: test_status_only')

        async def run_test():
            with patch('src.db_ops.ContainerOps') as MockContainerOps:
                mock_ops = MockContainerOps.return_value
                mock_ops.update.return_value = OperationResult(success=True, error=None)

                result = await update_save_status(
                    db_config=self.db_config,
                    container_id=self.container_id,
                    save_status="Running",
                )

                self.assertTrue(result.success)
                mock_ops.update.assert_called_once_with(
                    filters={"id": self.container_id},
                    data={"save_status": "Running", "save_error": None},
                )

        asyncio.run(run_test())
        print('Status-only update tested.')

    def test_success_with_saved_image_and_last_saved(self) -> None:
        """
        Succeeded update carries saved_image and last_saved_at.
        """
        print('Test: test_success_with_saved_image_and_last_saved')

        async def run_test():
            with patch('src.db_ops.ContainerOps') as MockContainerOps:
                mock_ops = MockContainerOps.return_value
                mock_ops.update.return_value = OperationResult(success=True, error=None)

                result = await update_save_status(
                    db_config=self.db_config,
                    container_id=self.container_id,
                    save_status="Succeeded",
                    saved_image="repo/test-pod-image:latest",
                    set_last_saved=True,
                )

                self.assertTrue(result.success)
                self.assertEqual(mock_ops.update.call_count, 1)
                _, kwargs = mock_ops.update.call_args
                self.assertEqual(kwargs["filters"], {"id": self.container_id})
                data = kwargs["data"]
                self.assertEqual(data["save_status"], "Succeeded")
                self.assertIsNone(data["save_error"])
                self.assertEqual(data["saved_image"], "repo/test-pod-image:latest")
                self.assertIn("last_saved_at", data)

        asyncio.run(run_test())
        print('Succeeded update tested.')

    def test_failed_with_save_error(self) -> None:
        """
        Failed update records save_error and omits saved_image / last_saved_at.
        """
        print('Test: test_failed_with_save_error')

        async def run_test():
            with patch('src.db_ops.ContainerOps') as MockContainerOps:
                mock_ops = MockContainerOps.return_value
                mock_ops.update.return_value = OperationResult(success=True, error=None)

                result = await update_save_status(
                    db_config=self.db_config,
                    container_id=self.container_id,
                    save_status="Failed",
                    save_error="build failed",
                )

                self.assertTrue(result.success)
                mock_ops.update.assert_called_once_with(
                    filters={"id": self.container_id},
                    data={"save_status": "Failed", "save_error": "build failed"},
                )

        asyncio.run(run_test())
        print('Failed update tested.')

    def test_missing_container_id(self) -> None:
        """
        Missing container ID short-circuits without touching the DB.
        """
        print('Test: test_missing_container_id')

        async def run_test():
            with patch('src.db_ops.ContainerOps') as MockContainerOps:
                result = await update_save_status(
                    db_config=self.db_config,
                    container_id="",
                    save_status="Running",
                )

                self.assertFalse(result.success)
                self.assertEqual(result.error, "Container ID is required")
                MockContainerOps.return_value.update.assert_not_called()

        asyncio.run(run_test())
        print('Missing container ID handled correctly.')

    def test_database_error(self) -> None:
        """
        A DB failure is surfaced in the returned OperationResult.
        """
        print('Test: test_database_error')

        async def run_test():
            with patch('src.db_ops.ContainerOps') as MockContainerOps:
                mock_ops = MockContainerOps.return_value
                mock_ops.update.return_value = OperationResult(
                    success=False, error="Database connection failed"
                )

                result = await update_save_status(
                    db_config=self.db_config,
                    container_id=self.container_id,
                    save_status="Running",
                )

                self.assertFalse(result.success)
                self.assertIn("Database connection failed", result.error)

        asyncio.run(run_test())
        print('Database error handled correctly.')


if __name__ == '__main__':
    import unittest
    unittest.main()
