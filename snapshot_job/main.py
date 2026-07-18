"""
Snapshot Job - Kubernetes Job for building and pushing container snapshots.

This job runs in a privileged container (isolated from user workloads) to:
1. Unpack the filesystem snapshot tar file
2. Create a Dockerfile
3. Build a Docker image
4. Push the image to a registry
5. Update the database with the saved image name
6. Terminate after completion
"""
import asyncio
import os
import sys
import signal
from abc import ABC, abstractmethod
from pathlib import Path

from browseterm_storage import StorageLayer, get_storage
from src.snapshot_builder import SnapshotBuilder
from src.db_ops import update_saved_image
from src.config import DB_CONFIG, CONTAINER_ID, REPO_NAME, REPO_PASSWORD, SNAPSHOT_DIR, NAMESPACE_NAME, POD_NAME

# Get the snapshot path from environment (passed from SaveUtility)
SNAPSHOT_PATH = os.getenv('SNAPSHOT_PATH')


class SnapshotStorageRetriever(ABC):
    '''
    Abstract base class for snapshot storage retrievers.
    Handles retrieving snapshots from different storage backends.
    '''

    @abstractmethod
    def get_snapshot_path(self, snapshot_path: str) -> str:
        '''
        Get the local path to the snapshot tar file.
        :params: snapshot_path: str - Storage path (PVC path or MinIO key)
        :returns: str - Local filesystem path to the tar file
        '''
        pass


class LocalSnapshotRetriever(SnapshotStorageRetriever):
    '''
    Retriever for local PVC storage.
    Snapshot already exists on the shared PVC volume.
    '''

    def get_snapshot_path(self, snapshot_path: str) -> str:
        '''
        Return the snapshot path directly (already on local filesystem).
        :params: snapshot_path: str - Local PVC path
        :returns: str - Same path (already local)
        '''
        print(f"Using local snapshot: {snapshot_path}")
        return snapshot_path


class MinioSnapshotRetriever(SnapshotStorageRetriever):
    '''
    Retriever for MinIO storage.
    Downloads snapshot from MinIO to local filesystem.
    '''

    def get_snapshot_path(self, snapshot_path: str) -> str:
        '''
        Download snapshot from MinIO and return local path.
        :params: snapshot_path: str - MinIO object key
        :returns: str - Local filesystem path to downloaded tar
        '''
        minio_storage_config = {
            'minio_endpoint': os.getenv('MINIO_ENDPOINT'),
            'minio_access_key': os.getenv('MINIO_ACCESS_KEY'),
            'minio_secret_key': os.getenv('MINIO_SECRET_KEY'),
            'minio_bucket': os.getenv('MINIO_BUCKET'),
            'minio_secure': os.getenv('MINIO_SECURE', 'false').lower() == 'true',
        }
        storage = get_storage(StorageLayer.MINIO, minio_storage_config)
        
        # Read snapshot from MinIO using the path provided
        tar_bytes = storage.read(snapshot_path)

        epoch = os.getenv('SNAPSHOT_EPOCH')
        if not epoch:
            import time
            epoch = str(int(time.time()))
        local_tar_path = Path(SNAPSHOT_DIR) / NAMESPACE_NAME / POD_NAME / f"fs_snapshot_{epoch}.tar.gz"
        local_tar_path.parent.mkdir(parents=True, exist_ok=True)
        local_tar_path.write_bytes(tar_bytes)
        print(f"Downloaded snapshot from MinIO: {snapshot_path} -> {local_tar_path}")
        return str(local_tar_path)


async def main() -> None:
    """Main entry point for the snapshot job."""
    print(f"Starting snapshot job for container {CONTAINER_ID}")
    
    # Validate environment variables
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
    
    # Get snapshot from storage based on configured storage layer
    storage_layer_str = os.getenv('STORAGE_LAYER', 'local').lower()
    storage_layer = StorageLayer(storage_layer_str)
    
    # Use strategy pattern to retrieve snapshot
    retriever_map = {
        StorageLayer.LOCAL: LocalSnapshotRetriever(),
        StorageLayer.MINIO: MinioSnapshotRetriever()
    }
    retriever = retriever_map.get(storage_layer)
    if retriever is None:
        print(f"ERROR: Unsupported STORAGE_LAYER: {storage_layer}")
        sys.exit(1)
    
    snapshot_tar_path = retriever.get_snapshot_path(SNAPSHOT_PATH)

    # Create snapshot builder with all environment variables
    builder = SnapshotBuilder(
        snapshot_path=snapshot_tar_path,
        container_id=CONTAINER_ID,
        repo_name=REPO_NAME,
        repo_password=REPO_PASSWORD,
        namespace_name=NAMESPACE_NAME,
        pod_name=POD_NAME,
        snapshot_dir=SNAPSHOT_DIR
    )
    
    try:
        # Step 1: Unpack the tar file
        print("Step 1: Unpacking snapshot tar file...")
        await builder.unpack_tar()
        
        # Step 2: Create Dockerfile
        print("Step 2: Creating Dockerfile...")
        await builder.create_dockerfile()
        
        # Step 3: Build Docker image
        print("Step 3: Building Docker image...")
        image_name = await builder.build_image()
        
        # Step 4: Tag image
        print("Step 4: Tagging image...")
        await builder.tag_image(image_name)
        
        # Step 5: Login to Docker registry
        print("Step 5: Logging into Docker registry...")
        await builder.docker_login()
        
        # Step 6: Push image to registry
        print("Step 6: Pushing image to registry...")
        await builder.docker_push(image_name)
        
        # Step 7: Cleanup local images
        print("Step 7: Cleaning up local images...")
        await builder.cleanup_images(image_name)
        
        # Step 8: Update database with saved_image
        print(f"Step 8: Updating database with saved image: {image_name}")
        result = await update_saved_image(
            db_config=DB_CONFIG,
            container_id=CONTAINER_ID,
            saved_image=image_name
        )
        
        if not result.success:
            print(f"ERROR: Failed to update database: {result.error}")
            sys.exit(1)
        
        print(f"✅ Snapshot job completed successfully!")
        print(f"   Image: {REPO_NAME}/{image_name}")
        print(f"   Container ID: {CONTAINER_ID}")
        
    except Exception as e:
        print(f"❌ Snapshot job failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        sys.exit(1)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run the main async function
    asyncio.run(main())
