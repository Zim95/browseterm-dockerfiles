# reaper

A Kubernetes **CronJob** that hibernates idle workspaces, completing the save → hibernate → resume
lifecycle. Structurally a sibling of `snapshot_job` / `status_sidecar` (a small in-cluster image
that talks to `browseterm-db`); functionally it's a scheduled sweep like `cert-manager`.

## What it does
Each run:
1. Queries `browseterm-db` for **RUNNING** containers whose `last_active_at` is older than
   `IDLE_THRESHOLD_SECONDS` (`ContainerOps.find_idle_containers`). `last_active_at` is stamped by
   **socket-ssh** on WS connect / heartbeat / disconnect.
2. For each: calls container-maker over gRPC — **`saveContainer`** (snapshot the fs to an image),
   then **`deleteContainer`** (free the pod). It reuses the exact save path the UI uses.
3. Sets the container's status to **`HIBERNATED`**.

The user resumes later via the existing `/resume-container` flow (recreate the pod from
`saved_image`). Failures are isolated per container; a non-zero exit surfaces any failure to the
CronJob.

## Layout
```
main.py                     entrypoint (asyncio, signal handlers, exit code)
src/config.py               env -> DBConfig + gRPC target + idle threshold
src/db_ops.py               find idle RUNNING containers; mark HIBERNATED
src/reaper.py               sweep: save -> delete -> hibernate (gRPC client of container-maker)
src/grpc_utils.py           mTLS gRPC channel/stub (copied from browseterm-server)
src/k8s_secrets.py          read the container-maker cert secret (copied from browseterm-server)
infra/deployment/           Dockerfile + entrypoint + deployment.yaml (SA/Role/RoleBinding/CronJob)
scripts/                    build + dev setup/teardown
tests/                      mocked unit tests (no cluster)
```
> `grpc_utils.py` / `k8s_secrets.py` are copied from `browseterm-server` because that repo isn't a
> packaged dependency. Keep them in sync manually.

## Build / deploy
```bash
make prod_build      # docker build + push {REPO_NAME}/reaper:latest  (needs USER_NAME + REPO_NAME)
make dev_setup       # envsubst deployment.yaml | kubectl apply  (CronJob + RBAC)
make dev_teardown
```

## Running tests
Mocked unit tests — the k8s client, DB ops, and the container-maker gRPC stub are all mocked, so
**no cluster is needed**:
```bash
poetry install
poetry run python -m unittest discover -t . -s tests -p "test_*.py" -v
# or: make test
```

## Prerequisites
- `browseterm-db` must have the `last_active_at` column (migration `f6a7b8c9d0e1`) and
  `find_idle_containers`.
- **socket-ssh** must stamp `last_active_at` — otherwise the column is always null and the reaper
  finds nothing (containers with a null `last_active_at` are intentionally skipped).
- The container-maker mTLS cert secret (`CONTAINER_MAKER_CERTS_SECRET_NAME`) must exist (minted by
  cert-manager) so the reaper can call container-maker.
