import asyncio
import signal

from src.common.logging_setup import configure_logging, get_logger
from src.config import CONTAINER_ID
from src.db_ops import update_container_status
from src.pod_watcher import watch_pod_status


configure_logging("status-sidecar")
logger = get_logger("main")


async def main() -> None:
    """Main entry point."""
    logger.info("Starting pod status watcher...", extra={"container_id": CONTAINER_ID})

    # Get the event loop
    loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()

    # Create a task for watching pod status
    watch_task: asyncio.Task = asyncio.create_task(watch_pod_status(update_container_status))

    # Set up signal handlers for graceful shutdown using asyncio
    def signal_handler() -> None:
        logger.info("Received termination signal, shutting down gracefully...", extra={"container_id": CONTAINER_ID})
        watch_task.cancel()

    # Register signal handlers in the event loop (proper asyncio way)
    loop.add_signal_handler(signal.SIGTERM, signal_handler)
    loop.add_signal_handler(signal.SIGINT, signal_handler)

    try:
        await watch_task
    except asyncio.CancelledError:
        logger.info("Pod status watcher stopped.", extra={"container_id": CONTAINER_ID})


if __name__ == "__main__":
    asyncio.run(main())
