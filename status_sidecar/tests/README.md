# status_sidecar tests

Unit tests (Python `unittest`, not pytest). Everything external is mocked — no cluster and no DB
are required:

- **test_config.py** — `DB_CONFIG` / `CONTAINER_ID` load from env.
- **test_db_ops.py** — `UpdateContainerStatus.validate()` + `update_container_status()` (mocks
  `ContainerOps.update`; checks the k8s pod phase → `ContainerStatus` enum mapping and the
  validation/error paths).
- **test_pod_watcher.py** — `get_pod_info()` env/file resolution (the k8s watch loop is not
  exercised).

## Running

With poetry (deps installed):
```bash
poetry run python -m unittest discover -s tests -p "test_*.py"
```

Or inside the built image (has the poetry venv + deps), mounting the current code:
```bash
docker run --rm --entrypoint bash \
  -v "$PWD/tests":/app/tests -v "$PWD/src":/app/src -v "$PWD/main.py":/app/main.py \
  -w /app zim95/status_sidecar:latest \
  -lc 'VPY=$(ls -d /root/.cache/pypoetry/virtualenvs/*/bin/python | head -1); $VPY -m unittest discover -s tests -p "test_*.py" -v'
```
