# Variables
include env.mk

build_ubuntu:
	./ubuntu_setup/ubuntu.build.sh $(USER_NAME) $(REPO_NAME)

build_snapshot_sidecar:
	@echo "WARNING: snapshot_sidecar is deprecated. Use build_snapshot_job instead."
	./snapshot_sidecar/build.sh $(USER_NAME) $(REPO_NAME)

build_snapshot_job:
	./snapshot_job/build.sh $(USER_NAME) $(REPO_NAME)

build_status_sidecar:
	./status_sidecar/infra/build.sh $(USER_NAME) $(REPO_NAME)

build_all: build_ubuntu build_snapshot_job build_status_sidecar

test_deployment_setup:
	./test_deployment/test_deployment_setup.sh $(NAMESPACE) $(REPO_NAME) $(CONTAINER_ID) $(DB_HOST) $(DB_PORT) $(DB_USERNAME) $(DB_PASSWORD) $(DB_DATABASE)

test_deployment_teardown:
	./test_deployment/test_deployment_teardown.sh $(NAMESPACE)

.PHONY: build_ubuntu build_snapshot_sidecar build_snapshot_job build_status_sidecar build_all test_deployment_setup test_deployment_teardown
