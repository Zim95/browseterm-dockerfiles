# Browseterm Dockerfiles
These images are used to build the images for SSH containers that are used in browseterm.

# Currently supported images:
1. Ubuntu (`ssh_ubuntu`) — the user's actual Linux terminal container (SSH server).

> **Moved out:** `status_sidecar` (replaced by the central `status_monitor` Deployment) and
> `snapshot_job` now live in the **`browseterm_workload`** repo. This repo builds only the
> user-facing terminal image now.

# How to build
1. Create an `env.mk` file at the root of the repository with the following contents:
  ```Makefile
  REPO_NAME=<docker-repo-name>
  USER_NAME=<docker-user-name>
  NAMESPACE=<kubernetes-namespace>
  ```

  > **Note:** `USER_NAME` and `REPO_NAME` suffice for `make build_ubuntu` / `make build_all`.
  > (`make test_deployment_setup` additionally reads `CONTAINER_ID` and the `DB_*` vars from `env.mk`.)

2. Build the terminal image:
```bash
$ make build_ubuntu   # or: make build_all
```
