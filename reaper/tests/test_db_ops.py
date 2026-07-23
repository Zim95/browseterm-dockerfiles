# builtins
from unittest import TestCase
from unittest.mock import patch
import asyncio

# module under test
from src.db_ops import find_idle_running_containers, mark_hibernated

# browseterm-db
from browseterm_db.common.config import DBConfig
from browseterm_db.operations import OperationResult
from browseterm_db.models.containers import ContainerStatus


class TestFindIdleRunningContainers(TestCase):
    '''UNIT (mocked ContainerOps): the reaper delegates idle detection to browseterm-db's
    find_idle_containers and returns its rows.'''

    def setUp(self) -> None:
        self.cfg = DBConfig(host="h", port=5432, username="u", password="p", database="d")

    def test_delegates_to_find_idle_containers(self) -> None:
        rows = [{"id": "c-old", "user_id": "u1", "status": "Running"}]

        async def run():
            with patch("src.db_ops.ContainerOps") as MockOps:
                MockOps.return_value.find_idle_containers.return_value = OperationResult(success=True, data=rows)
                idle = await find_idle_running_containers(self.cfg, idle_threshold_seconds=3600)
                self.assertEqual([r["id"] for r in idle], ["c-old"])
                MockOps.return_value.find_idle_containers.assert_called_once_with(3600)
        asyncio.run(run())

    def test_raises_on_query_failure(self) -> None:
        async def run():
            with patch("src.db_ops.ContainerOps") as MockOps:
                MockOps.return_value.find_idle_containers.return_value = OperationResult(success=False, error="boom")
                with self.assertRaises(RuntimeError):
                    await find_idle_running_containers(self.cfg, idle_threshold_seconds=3600)
        asyncio.run(run())

    def test_mark_hibernated_updates_status(self) -> None:
        async def run():
            with patch("src.db_ops.ContainerOps") as MockOps:
                MockOps.return_value.update.return_value = OperationResult(success=True)
                res = await mark_hibernated(self.cfg, "c-1")
                self.assertTrue(res.success)
                MockOps.return_value.update.assert_called_once_with(
                    filters={"id": "c-1"}, data={"status": ContainerStatus.HIBERNATED})
        asyncio.run(run())

    def test_mark_hibernated_requires_id(self) -> None:
        async def run():
            res = await mark_hibernated(self.cfg, "")
            self.assertFalse(res.success)
        asyncio.run(run())
