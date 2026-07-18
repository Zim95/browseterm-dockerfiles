"""
Test configuration module.
"""
# builtins
from unittest import TestCase
import os

# modules
from src.config import DB_CONFIG, CONTAINER_ID, REPO_NAME, REPO_PASSWORD, SNAPSHOT_DIR


class TestConfiguration(TestCase):
    """
    Test configuration loading from environment variables.
    """

    def test_db_config_loads_from_env(self) -> None:
        """
        Test that DB_CONFIG loads from environment variables.
        """
        print('Test: test_db_config_loads_from_env')
        
        # Set environment variables
        os.environ['DB_HOST'] = 'test-db-host'
        os.environ['DB_PORT'] = '5433'
        os.environ['DB_USERNAME'] = 'test-user'
        os.environ['DB_PASSWORD'] = 'test-pass'
        os.environ['DB_DATABASE'] = 'test-db'
        
        # Reload config module to pick up new env vars
        import importlib
        import src.config
        importlib.reload(src.config)
        
        self.assertEqual(src.config.DB_CONFIG.host, 'test-db-host')
        self.assertEqual(src.config.DB_CONFIG.port, 5433)
        self.assertEqual(src.config.DB_CONFIG.username, 'test-user')
        self.assertEqual(src.config.DB_CONFIG.password, 'test-pass')
        self.assertEqual(src.config.DB_CONFIG.database, 'test-db')
        
        print('DB configuration loaded correctly.')

    def test_snapshot_dir_construction(self) -> None:
        """
        Test that SNAPSHOT_DIR is constructed correctly.
        """
        print('Test: test_snapshot_dir_construction')
        
        # Set environment variables
        os.environ['NAMESPACE_NAME'] = 'test-namespace'
        os.environ['POD_NAME'] = 'test-pod'
        
        # Reload config module
        import importlib
        import src.config
        importlib.reload(src.config)
        
        expected_dir = "/mnt/snapshot/test-namespace/test-pod"
        self.assertEqual(src.config.SNAPSHOT_DIR, expected_dir)
        
        print('Snapshot directory constructed correctly.')


if __name__ == '__main__':
    import unittest
    unittest.main()
