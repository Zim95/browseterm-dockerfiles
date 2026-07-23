"""Reaper CronJob entrypoint."""
import asyncio
import sys
import signal

from src.reaper import Reaper


async def main() -> None:
    print("[reaper] starting sweep")
    reaper = Reaper()
    summary = await reaper.run()
    # Non-zero exit if any container failed so the CronJob surfaces the problem.
    if summary.failed > 0:
        print(f"[reaper] completed with {summary.failed} failure(s)")
        sys.exit(1)
    print("[reaper] completed cleanly")


if __name__ == "__main__":
    def _sig(signum, frame):
        print(f"[reaper] received signal {signum}, exiting")
        sys.exit(1)
    signal.signal(signal.SIGTERM, _sig)
    signal.signal(signal.SIGINT, _sig)
    asyncio.run(main())
