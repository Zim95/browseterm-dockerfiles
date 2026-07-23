"""Configuration for the reaper CronJob (env -> constants)."""
import os

from browseterm_db.common.config import DBConfig

# Database (DB_* convention, same as snapshot_job / status_sidecar).
DB_CONFIG: DBConfig = DBConfig(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "5432")),
    username=os.getenv("DB_USERNAME"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_DATABASE"),
)

# Kubernetes namespace (cert-secret lookup + cross-namespace service access).
NAMESPACE: str = os.getenv("NAMESPACE", "browseterm")

# container-maker gRPC target.
CONTAINER_MAKER_HOST: str = os.getenv("CONTAINER_MAKER_HOST", "container-maker-development-service")
CONTAINER_MAKER_PORT: int = int(os.getenv("CONTAINER_MAKER_PORT", "50052"))
CONTAINER_MAKER_CERTS_SECRET_NAME: str = os.getenv(
    "CONTAINER_MAKER_CERTS_SECRET_NAME", "container-maker-development-service-certs"
)

# Idle policy: a RUNNING container whose last_active_at is older than this is hibernated.
# Default 1 week (per TODOPLAN §1); overridable via env.
IDLE_THRESHOLD_SECONDS: int = int(os.getenv("IDLE_THRESHOLD_SECONDS", str(7 * 24 * 3600)))
