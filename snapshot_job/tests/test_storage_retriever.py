"""
Test build_storage_config() from main.py.

The in-file SnapshotStorageRetriever / LocalSnapshotRetriever / MinioSnapshotRetriever
classes were removed; storage resolution now goes through browseterm-storage directly.
main.build_storage_config() maps the environment to the (StorageLayer, config-dict) that
get_storage() expects.
"""
# builtins
from unittest import TestCase
from unittest.mock import patch
import os

# modules
import main
from browseterm_storage import StorageLayer


class TestBuildStorageConfig(TestCase):
    """
    Test that build_storage_config() reads the environment and returns the
    correct (StorageLayer, config-dict) tuple for each storage layer.
    """

    def test_local_layer(self) -> None:
        """
        STORAGE_LAYER=local -> (StorageLayer.LOCAL, {'snapshot_dir': SNAPSHOT_DIR}).
        """
        print('Test: test_local_layer')

        with patch.dict(os.environ, {'STORAGE_LAYER': 'local'}, clear=False):
            layer, config = main.build_storage_config()

        self.assertEqual(layer, StorageLayer.LOCAL)
        self.assertEqual(config, {'snapshot_dir': main.SNAPSHOT_DIR})
        print('Local storage config built correctly.')

    def test_default_layer_is_local(self) -> None:
        """
        No STORAGE_LAYER set -> defaults to LOCAL.
        """
        print('Test: test_default_layer_is_local')

        env_without_layer = {k: v for k, v in os.environ.items() if k != 'STORAGE_LAYER'}
        with patch.dict(os.environ, env_without_layer, clear=True):
            layer, config = main.build_storage_config()

        self.assertEqual(layer, StorageLayer.LOCAL)
        self.assertEqual(config, {'snapshot_dir': main.SNAPSHOT_DIR})
        print('Default storage layer is local.')

    def test_minio_layer(self) -> None:
        """
        STORAGE_LAYER=minio -> (StorageLayer.MINIO, {minio config from MINIO_* env}).
        """
        print('Test: test_minio_layer')

        minio_env = {
            'STORAGE_LAYER': 'minio',
            'MINIO_ENDPOINT': 'minio:9000',
            'MINIO_ACCESS_KEY': 'test-access',
            'MINIO_SECRET_KEY': 'test-secret',
            'MINIO_BUCKET': 'snapshots',
            'MINIO_SECURE': 'true',
        }
        with patch.dict(os.environ, minio_env, clear=False):
            layer, config = main.build_storage_config()

        self.assertEqual(layer, StorageLayer.MINIO)
        self.assertEqual(
            config,
            {
                'minio_endpoint': 'minio:9000',
                'minio_access_key': 'test-access',
                'minio_secret_key': 'test-secret',
                'minio_bucket': 'snapshots',
                'minio_secure': True,
            },
        )
        print('MinIO storage config built correctly.')

    def test_minio_secure_defaults_false(self) -> None:
        """
        minio_secure is False unless MINIO_SECURE == 'true' (case-insensitive).
        """
        print('Test: test_minio_secure_defaults_false')

        minio_env = {
            'STORAGE_LAYER': 'MINIO',  # also verifies the .lower() on STORAGE_LAYER
            'MINIO_ENDPOINT': 'minio:9000',
            'MINIO_ACCESS_KEY': 'test-access',
            'MINIO_SECRET_KEY': 'test-secret',
            'MINIO_BUCKET': 'snapshots',
            'MINIO_SECURE': 'false',
        }
        with patch.dict(os.environ, minio_env, clear=False):
            layer, config = main.build_storage_config()

        self.assertEqual(layer, StorageLayer.MINIO)
        self.assertFalse(config['minio_secure'])
        print('MinIO secure flag defaults to False.')


if __name__ == '__main__':
    import unittest
    unittest.main()
