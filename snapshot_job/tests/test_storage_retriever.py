"""
Test the snapshot storage retrievers.
"""
# builtins
from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock
import os
from pathlib import Path

# modules
from main import LocalSnapshotRetriever, MinioSnapshotRetriever
from browseterm_storage import StorageLayer


class TestLocalSnapshotRetriever(TestCase):
    """
    Test LocalSnapshotRetriever.
    Verifies that local snapshots return the path directly.
    """

    def setUp(self) -> None:
        self.retriever = LocalSnapshotRetriever()
        self.epoch = "1234567890"
        self.snapshot_path = f"/mnt/snapshot/test-namespace/test-pod/fs_snapshot_{self.epoch}.tar.gz"

    def test_get_snapshot_path_returns_same_path(self) -> None:
        """
        Test that LocalSnapshotRetriever returns the same path provided.
        """
        print('Test: test_get_snapshot_path_returns_same_path')
        result = self.retriever.get_snapshot_path(self.snapshot_path)
        self.assertEqual(result, self.snapshot_path)
        print('Local snapshot path returned correctly.')


class TestMinioSnapshotRetriever(TestCase):
    """
    Test MinioSnapshotRetriever.
    Verifies that MinIO snapshots are downloaded correctly.
    """

    def setUp(self) -> None:
        self.retriever = MinioSnapshotRetriever()
        self.epoch = "1234567890"
        self.minio_path = f"test-namespace/test-pod/fs_snapshot_{self.epoch}.tar.gz"
        self.expected_local_path = Path(f"/mnt/snapshot/test-namespace/test-pod/fs_snapshot_{self.epoch}.tar.gz")

    @patch('main.get_storage')
    @patch('os.getenv')
    @patch('pathlib.Path.write_bytes')
    @patch('pathlib.Path.mkdir')
    def test_download_from_minio(self, mock_mkdir, mock_write_bytes, mock_getenv, mock_get_storage) -> None:
        """
        Test that MinioSnapshotRetriever downloads from MinIO and writes locally.
        """
        print('Test: test_download_from_minio')
        
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: {
            'MINIO_ENDPOINT': 'minio:9000',
            'MINIO_ACCESS_KEY': 'test-access',
            'MINIO_SECRET_KEY': 'test-secret',
            'MINIO_BUCKET': 'snapshots',
            'MINIO_SECURE': 'false',
        }.get(key, default)
        
        # Mock storage
        mock_storage = MagicMock()
        mock_storage.read.return_value = b'fake tar data'
        mock_get_storage.return_value = mock_storage
        
        # Execute
        with patch('main.SNAPSHOT_DIR', '/mnt/snapshot'):
            with patch('main.NAMESPACE_NAME', 'test-namespace'):
                with patch('main.POD_NAME', 'test-pod'):
                    result = self.retriever.get_snapshot_path(self.minio_path)
        
        # Verify storage was called with correct layer
        mock_get_storage.assert_called_once_with(
            StorageLayer.MINIO,
            {
                'minio_endpoint': 'minio:9000',
                'minio_access_key': 'test-access',
                'minio_secret_key': 'test-secret',
                'minio_bucket': 'snapshots',
                'minio_secure': False,
            }
        )
        
        # Verify read was called with minio path
        mock_storage.read.assert_called_once_with(self.minio_path)
        
        print('MinIO snapshot downloaded correctly.')


if __name__ == '__main__':
    import unittest
    unittest.main()
