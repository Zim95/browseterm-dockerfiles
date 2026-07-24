# builtins
from unittest import TestCase
from unittest.mock import patch, MagicMock
import asyncio


def _row(cid: str, uid: str) -> dict:
    return {"id": cid, "user_id": uid, "status": "Running"}


class TestReaperSweep(TestCase):
    '''UNIT (mocked gRPC stub + DB helpers): assert the save->delete->hibernate order and
    per-container error isolation. No cluster.'''

    def _build_reaper(self):
        # Bypass __init__ (cert/channel setup); inject a mock stub.
        from src.reaper import Reaper
        reaper = Reaper.__new__(Reaper)
        reaper.stub = MagicMock()
        return reaper

    def test_happy_path_order_and_summary(self) -> None:
        from src import reaper as reaper_mod
        rows = [_row("c1", "u1")]

        async def run():
            reaper = self._build_reaper()
            calls = []
            reaper.stub.saveContainer.side_effect = lambda req, **kw: calls.append(("save", req.container_id, req.network_name))
            reaper.stub.deleteContainer.side_effect = lambda req, **kw: calls.append(("delete", req.container_id, req.network_name))
            with patch.object(reaper_mod, "find_idle_running_containers", return_value=rows), \
                 patch.object(reaper_mod, "mark_hibernated") as mock_hib:
                mock_hib.return_value = MagicMock(success=True)
                summary = await reaper.run()
                self.assertEqual(summary.hibernated, 1)
                self.assertEqual(summary.failed, 0)
                # save then delete, both with network_name == f"{user_id}-namespace"
                self.assertEqual(calls, [("save", "c1", "u1-namespace"), ("delete", "c1", "u1-namespace")])
        asyncio.run(run())

    def test_failure_is_isolated_per_container(self) -> None:
        from src import reaper as reaper_mod
        rows = [_row("c1", "u1"), _row("c2", "u2")]

        async def run():
            reaper = self._build_reaper()

            def save(req, **kw):
                if req.container_id == "c1":
                    raise Exception("save boom")
            reaper.stub.saveContainer.side_effect = save
            with patch.object(reaper_mod, "find_idle_running_containers", return_value=rows), \
                 patch.object(reaper_mod, "mark_hibernated") as mock_hib:
                mock_hib.return_value = MagicMock(success=True)
                summary = await reaper.run()
                self.assertEqual(summary.scanned, 2)
                self.assertEqual(summary.hibernated, 1)   # c2 still processed
                self.assertEqual(summary.failed, 1)       # c1 failed, did not abort the run
        asyncio.run(run())

    def test_no_idle_is_a_clean_noop(self) -> None:
        from src import reaper as reaper_mod

        async def run():
            reaper = self._build_reaper()
            with patch.object(reaper_mod, "find_idle_running_containers", return_value=[]), \
                 patch.object(reaper_mod, "mark_hibernated") as mock_hib:
                summary = await reaper.run()
                self.assertEqual((summary.scanned, summary.hibernated, summary.failed), (0, 0, 0))
                reaper.stub.saveContainer.assert_not_called()
                mock_hib.assert_not_called()
        asyncio.run(run())
