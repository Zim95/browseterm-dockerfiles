"""Configuration for snapshot job."""
import os
from browseterm_db.common.config import DBConfig


# Database configuration (same pattern as status_sidecar)
DB_CONFIG: DBConfig = DBConfig(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "5432")),
    username=os.getenv("DB_USERNAME"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_DATABASE")
)

# Container and snapshot configuration
CONTAINER_ID: str = os.getenv("CONTAINER_ID", "")
POD_NAME: str = os.getenv("POD_NAME", "")
NAMESPACE_NAME: str = os.getenv("NAMESPACE_NAME", "")

# Docker registry configuration
REPO_NAME: str = os.getenv("REPO_NAME", "")
REPO_PASSWORD: str = os.getenv("REPO_PASSWORD", "")

# Snapshot configuration
SNAPSHOT_BASE_DIR: str = "/mnt/snapshot"
SNAPSHOT_DIR: str = f"{SNAPSHOT_BASE_DIR}/{NAMESPACE_NAME}/{POD_NAME}" if NAMESPACE_NAME and POD_NAME else SNAPSHOT_BASE_DIR
SNAPSHOT_FILE_NAME: str = "full_fs_snapshot"
