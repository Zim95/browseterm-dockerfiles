include env.mk

# Build + push the reaper image (mirrors snapshot_job / status_sidecar).
prod_build:
	./scripts/deployment/build.sh $(USER_NAME) $(REPO_NAME)

# Deploy / remove the CronJob + RBAC.
dev_setup:
	./scripts/development/development-setup.sh

dev_teardown:
	./scripts/development/development-teardown.sh

# Run the tests (mocked; no cluster).
test:
	poetry run python -m unittest discover -t . -s tests -p "test_*.py" -v

.PHONY: prod_build dev_setup dev_teardown test
