# Browseterm Dockerfiles
These images are used to build the images for SSH containers that are used in browseterm.

# Currently supported images:
1. Ubuntu (`ssh_ubuntu`)
2. Status Sidecar (`status_sidecar`)
3. Snapshot Job (`snapshot_job`)

(`snapshot_sidecar` is deprecated.)

# How to build
1. Create an `env.mk` file at the root of the repository with the following contents:
  ```Makefile
  REPO_NAME=<docker-repo-name>
  USER_NAME=<docker-user-name>
  NAMESPACE=<kubernetes-namespace>
  HOST_DIR=<current-working-directory>

  CONTAINER_ID=<container-id-in-database>
  DB_HOST=<database-host>
  DB_PORT=<database-port>
  DB_USERNAME=<database-username>
  DB_PASSWORD=<database-password>
  DB_DATABASE=<database-database>
  ```

  > **Note:** `USER_NAME` and `REPO_NAME` alone suffice for `make build_all`. `CONTAINER_ID` and the `DB_*` vars are only needed for the (deprecated) `make test_deployment_setup`, NOT for building. `HOST_DIR` is not used by this top-level Makefile.

2. Now you should be able to use `make` commands to run the build.

3. You can run `make build_all` to build all the required images.

  > **KNOWN ISSUE:** `make build_snapshot_job` / `make build_all` call a non-existent `./snapshot_job/build.sh`. Workaround: `cd snapshot_job && make prod_build`.

# Running tests
The `snapshot_job` image has its own test suite. See [`snapshot_job/tests/README.md`](snapshot_job/tests/README.md) for full details (individual suites, real-DB integration tests, and setup).

To run all `snapshot_job` tests:
```bash
$ cd snapshot_job && poetry run python -m unittest discover -t . -s tests -p "test_*.py"
```
