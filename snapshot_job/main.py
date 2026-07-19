"""
Snapshot Job - Kubernetes Job for building and pushing container snapshots.

This job runs in a privileged container (isolated from user workloads) to:
1. Resolve the filesystem snapshot tar to a local path via browseterm-storage
   (local PVC passthrough, or MinIO download)
2. Unpack it, build a Docker image, push it to the registry
3. Record the result in Postgres (save_status + saved_image) via browseterm-db,
   which fires the container_save_status_change NOTIFY -> SSE to the frontend
4. Terminate after completion
"""
import asyncio
import os
import sys
import signal
from pathlib import Path

from browseterm_storage import StorageLayer, get_storage
from browseterm_db.models.containers import SaveStatus
from src.snapshot_builder import SnapshotBuilder
from src.db_ops import update_save_status
from src.config import DB_CONFIG, CONTAINER_ID, REPO_NAME, REPO_PASSWORD, SNAPSHOT_DIR, NAMESPACE_NAME, POD_NAME

# Storage path/key of the tar produced by container-maker (passed via env).
SNAPSHOT_PATH = os.getenv('SNAPSHOT_PATH')


def build_storage_config():
    """Build the (StorageLayer, config-dict) for browseterm-storage from the environment.

    browseterm-storage is the single abstraction that decides where the tar comes from:
    LOCAL reads it from the shared PVC, MINIO downloads it from object storage.
    """
    layer = StorageLayer(os.getenv('STORAGE_LAYER', 'local').lower())
    if layer == StorageLayer.MINIO:
        config = {
            'minio_endpoint': os.getenv('MINIO_ENDPOINT'),
            'minio_access_key': os.getenv('MINIO_ACCESS_KEY'),
            'minio_secret_key': os.getenv('MINIO_SECRET_KEY'),
            'minio_bucket': os.getenv('MINIO_BUCKET'),
            'minio_secure': os.getenv('MINIO_SECURE', 'false').lower() == 'true',
        }
    else:
        config = {'snapshot_dir': SNAPSHOT_DIR}
    return layer, config


async def main() -> None:
    """Main entry point for the snapshot job."""
    print(f"Starting snapshot job for container {CONTAINER_ID}")

    # Validate required environment variables
    if not CONTAINER_ID:
        print("ERROR: CONTAINER_ID environment variable is required")
        sys.exit(1)
    if not REPO_NAME or not REPO_PASSWORD:
        print("ERROR: REPO_NAME and REPO_PASSWORD environment variables are required")
        sys.exit(1)
    if not NAMESPACE_NAME or not POD_NAME:
        print("ERROR: NAMESPACE_NAME and POD_NAME environment variables are required")
        sys.exit(1)
    if not SNAPSHOT_PATH:
        print("ERROR: SNAPSHOT_PATH environment variable is required")
        sys.exit(1)

    # Mark the save as RUNNING (also clears any previous error). This NOTIFYs the frontend.
    await update_save_status(DB_CONFIG, CONTAINER_ID, SaveStatus.RUNNING.value)

    try:
        # Resolve the tar to a local path via browseterm-storage.
        storage_layer, storage_config = build_storage_config()
        storage = get_storage(storage_layer, storage_config)
        dest_dir = str(Path(SNAPSHOT_DIR) / NAMESPACE_NAME / POD_NAME)
        snapshot_tar_path = storage.localize(SNAPSHOT_PATH, dest_dir)
        print(f"Snapshot localized to {snapshot_tar_path} (storage={storage_layer.value})")

        builder = SnapshotBuilder(
            snapshot_path=snapshot_tar_path,
            container_id=CONTAINER_ID,
            repo_name=REPO_NAME,
            repo_password=REPO_PASSWORD,
            namespace_name=NAMESPACE_NAME,
            pod_name=POD_NAME,
            snapshot_dir=SNAPSHOT_DIR,
        )

        print("Step 1: Unpacking snapshot tar file...")
        await builder.unpack_tar()

        print("Step 2: Creating Dockerfile...")
        await builder.create_dockerfile()

        print("Step 3: Building Docker image...")
        image_name = await builder.build_image()

        print("Step 4: Tagging image...")
        await builder.tag_image(image_name)

        print("Step 5: Logging into Docker registry...")
        await builder.docker_login()

        print("Step 6: Pushing image to registry...")
        await builder.docker_push(image_name)

        print("Step 7: Cleaning up local images...")
        await builder.cleanup_images(image_name)

        # Record success: full pullable image ref + SUCCEEDED + last_saved_at.
        pushed_image = f"{REPO_NAME}/{image_name}"
        print(f"Step 8: Recording success in DB (saved_image={pushed_image})")
        result = await update_save_status(
            DB_CONFIG,
            CONTAINER_ID,
            SaveStatus.SUCCEEDED.value,
            saved_image=pushed_image,
            set_last_saved=True,
        )
        if not result.success:
            raise Exception(f"Failed to update database: {result.error}")

        print("✅ Snapshot job completed successfully!")
        print(f"   Image: {pushed_image}")
        print(f"   Container ID: {CONTAINER_ID}")

    except Exception as e:
        print(f"❌ Snapshot job failed: {e}")
        import traceback
        traceback.print_exc()
        # Best-effort: record FAILED so the frontend stops spinning and shows the error.
        try:
            await update_save_status(
                DB_CONFIG,
                CONTAINER_ID,
                SaveStatus.FAILED.value,
                save_error=str(e)[:1000],
            )
        except Exception as db_e:
            print(f"(also failed to record FAILED status: {db_e})")
        sys.exit(1)


if __name__ == "__main__":
    # Graceful shutdown handlers
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        sys.exit(1)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    asyncio.run(main())
