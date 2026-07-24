"""Reaper CronJob entrypoint."""
import asyncio
import sys
import signal

from src.logging_setup import configure_logging, get_logger, set_request_context
from src.reaper import Reaper

logger = get_logger("reaper.main")


async def main() -> None:
    logger.info("starting sweep")
    reaper = Reaper()
    summary = await reaper.run()
    # Non-zero exit if any container failed so the CronJob surfaces the problem.
    if summary.failed > 0:
        logger.warning("completed with failures", extra={"failed": summary.failed})
        sys.exit(1)
    logger.info("completed cleanly")


if __name__ == "__main__":
    # Structured JSON logs + a run-scoped request_id so every line of this sweep — and the
    # save/delete gRPC calls it makes — share one correlation id.
    configure_logging("reaper")
    set_request_context()  # mint a fresh request_id for this run

    def _sig(signum, frame):
        logger.info("received signal, exiting", extra={"signal": signum})
        sys.exit(1)
    signal.signal(signal.SIGTERM, _sig)
    signal.signal(signal.SIGINT, _sig)
    asyncio.run(main())
