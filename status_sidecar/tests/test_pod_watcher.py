'''
Unit tests for status_sidecar pod_watcher.get_pod_info (no cluster).
Only the env/file resolution is tested; the k8s watch loop is not exercised.
Env is set before import because src.config (pulled in transitively) reads DB_* at import time.
'''
import os

os.environ.setdefault("DB_HOST", "h")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USERNAME", "u")
os.environ.setdefault("DB_PASSWORD", "p")
os.environ.setdefault("DB_DATABASE", "d")
os.environ.setdefault("CONTAINER_ID", "cid")

from unittest import TestCase
from unittest.mock import patch
import asyncio

from src import pod_watcher


class TestGetPodInfo(TestCase):
    def test_pod_name_from_env_and_namespace_from_env(self) -> None:
        print('Test: test_pod_name_from_env_and_namespace_from_env')
        # namespace secret file absent -> falls back to POD_NAMESPACE env
        with patch.dict(os.environ, {"POD_NAME": "my-pod", "POD_NAMESPACE": "my-ns"}), \
             patch("src.pod_watcher.os.path.exists", return_value=False):
            name, namespace = asyncio.run(pod_watcher.get_pod_info())
        self.assertEqual(name, "my-pod")
        self.assertEqual(namespace, "my-ns")

    def test_namespace_defaults_to_default_when_unset(self) -> None:
        print('Test: test_namespace_defaults_to_default_when_unset')
        # only POD_NAME set (so /etc/hostname is never read), no POD_NAMESPACE, no secret file
        with patch.dict(os.environ, {"POD_NAME": "p"}, clear=True), \
             patch("src.pod_watcher.os.path.exists", return_value=False):
            name, namespace = asyncio.run(pod_watcher.get_pod_info())
        self.assertEqual(name, "p")
        self.assertEqual(namespace, "default")
