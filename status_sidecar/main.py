import asyncio
import signal

from src.db_ops import update_container_status
from src.pod_watcher import watch_pod_status



async def main() -> None:
    """Main entry point."""
    print("Starting pod status watcher...")
    
    # Get the event loop
    loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
    
    # Create a task for watching pod status
    watch_task: asyncio.Task = asyncio.create_task(watch_pod_status(update_container_status))

    # Set up signal handlers for graceful shutdown using asyncio
    def signal_handler() -> None:
        print("\nReceived termination signal, shutting down gracefully...")
        watch_task.cancel()

    # Register signal handlers in the event loop (proper asyncio way)
    loop.add_signal_handler(signal.SIGTERM, signal_handler)
    loop.add_signal_handler(signal.SIGINT, signal_handler)

    try:
        await watch_task
    except asyncio.CancelledError:
        print("Pod status watcher stopped.")


if __name__ == "__main__":
    asyncio.run(main())
