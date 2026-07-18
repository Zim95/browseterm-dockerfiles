# Snapshot Job
Kubernetes Job for building and pushing container snapshots without requiring privileged sidecars.

## Architecture
This job runs as an isolated, privileged Kubernetes Job that:
- Takes a filesystem snapshot tar file as input
- Builds a Docker image from the snapshot
- Pushes the image to a registry
- Updates the database with the saved image name
- Terminates after completion

## Environment Variables
- `CONTAINER_ID`: Database ID of the container
- `POD_NAME`: Name of the pod being snapshotted (container-maker sets this at runtime; set it manually only for standalone dev testing)
- `NAMESPACE_NAME`: Kubernetes namespace
- `REPO_NAME`: Docker registry repository name
- `REPO_PASSWORD`: Docker registry password
- `DB_HOST`: PostgreSQL host
- `DB_PORT`: PostgreSQL port
- `DB_USERNAME`: PostgreSQL username
- `DB_PASSWORD`: PostgreSQL password
- `DB_DATABASE`: PostgreSQL database name
- `SNAPSHOT_PATH`: Path to the filesystem snapshot tar file

## Security
This job runs with privileged access to use Docker, but is isolated from user workloads and terminates after completion.
