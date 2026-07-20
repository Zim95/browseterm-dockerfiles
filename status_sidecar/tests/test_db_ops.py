'''
Unit tests for status_sidecar db_ops (no real DB — ContainerOps.update is mocked).
Env is set before import because src.config reads DB_* at import time.
'''
import os

os.environ.setdefault("DB_HOST", "h")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USERNAME", "u")
os.environ.setdefault("DB_PASSWORD", "p")
os.environ.setdefault("DB_DATABASE", "d")
os.environ.setdefault("CONTAINER_ID", "cid")

from unittest import TestCase
from unittest.mock import patch, MagicMock
import asyncio

import src.db_ops as db_ops
from src.db_ops import UpdateContainerStatus, update_container_status
from browseterm_db.models.containers import ContainerStatus


class TestUpdateContainerStatusValidation(TestCase):
    def test_missing_container_id_raises(self) -> None:
        print('Test: test_missing_container_id_raises')
        with self.assertRaises(ValueError):
            UpdateContainerStatus(container_id="", status="Running").validate()

    def test_missing_status_raises(self) -> None:
        print('Test: test_missing_status_raises')
        with self.assertRaises(ValueError):
            UpdateContainerStatus(container_id="c1", status="").validate()

    def test_valid_does_not_raise(self) -> None:
        print('Test: test_valid_does_not_raise')
        UpdateContainerStatus(container_id="c1", status="Running").validate()


class TestUpdateContainerStatus(TestCase):
    '''update_container_status maps the k8s pod phase → ContainerStatus and calls ContainerOps.update.'''

    def test_valid_update_maps_phase_and_calls_ops(self) -> None:
        print('Test: test_valid_update_maps_phase_and_calls_ops')
        mock_update = MagicMock(return_value=MagicMock(success=True))
        with patch.object(db_ops.container_ops, 'update', mock_update):
            result = asyncio.run(update_container_status(UpdateContainerStatus("c1", "Running")))
        self.assertTrue(result.success)
        self.assertTrue(mock_update.called)
        kwargs = mock_update.call_args.kwargs
        self.assertEqual(kwargs["filters"], {"id": "c1"})
        # the string phase is mapped to the ContainerStatus enum member
        self.assertEqual(kwargs["data"], {"status": ContainerStatus.RUNNING})

    def test_invalid_phase_returns_failure_without_calling_ops(self) -> None:
        print('Test: test_invalid_phase_returns_failure_without_calling_ops')
        mock_update = MagicMock()
        with patch.object(db_ops.container_ops, 'update', mock_update):
            # "Bogus" is not a valid ContainerStatus value -> ValueError inside, caught -> failure
            result = asyncio.run(update_container_status(UpdateContainerStatus("c1", "Bogus")))
        self.assertFalse(result.success)
        mock_update.assert_not_called()

    def test_missing_id_returns_failure_without_calling_ops(self) -> None:
        print('Test: test_missing_id_returns_failure_without_calling_ops')
        mock_update = MagicMock()
        with patch.object(db_ops.container_ops, 'update', mock_update):
            result = asyncio.run(update_container_status(UpdateContainerStatus("", "Running")))
        self.assertFalse(result.success)
        mock_update.assert_not_called()
