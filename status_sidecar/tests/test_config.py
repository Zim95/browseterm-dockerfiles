'''
Unit test for status_sidecar config loading (no DB / no cluster).
Env is set BEFORE importing src.config because config.py reads it at import time
(and int(DB_PORT) would fail if unset).
'''
import os

os.environ["DB_HOST"] = "pg.example"
os.environ["DB_PORT"] = "6543"
os.environ["DB_USERNAME"] = "test-user"
os.environ["DB_PASSWORD"] = "test-pass"
os.environ["DB_DATABASE"] = "test-db"
os.environ["CONTAINER_ID"] = "cid-123"

from unittest import TestCase
import importlib
import src.config as config


class TestConfig(TestCase):
    def test_db_config_and_container_id_from_env(self) -> None:
        print('Test: test_db_config_and_container_id_from_env')
        importlib.reload(config)  # re-read the env set above
        self.assertEqual(config.DB_CONFIG.host, "pg.example")
        self.assertEqual(config.DB_CONFIG.port, 6543)
        self.assertEqual(config.DB_CONFIG.username, "test-user")
        self.assertEqual(config.DB_CONFIG.password, "test-pass")
        self.assertEqual(config.DB_CONFIG.database, "test-db")
        self.assertEqual(config.CONTAINER_ID, "cid-123")
        print('OK')
