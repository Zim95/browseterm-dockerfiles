"""
Test database operations.
"""
# builtins
from unittest import TestCase
from unittest.mock import Mock, patch, AsyncMock
import asyncio

# modules
from src.db_ops import update_saved_image
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


if __name__ == '__main__':
    import unittest
    unittest.main()
