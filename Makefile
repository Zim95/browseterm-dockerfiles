# Variables
include env.mk

build_ubuntu:
	./ubuntu_setup/ubuntu.build.sh $(USER_NAME) $(REPO_NAME)

build_snapshot_sidecar:
	./snapshot_sidecar/build.sh $(USER_NAME) $(REPO_NAME)

build_status_sidecar:
	./status_sidecar/infra/build.sh $(USER_NAME) $(REPO_NAME)

test_deployment_setup:
	./test_deployment/test_deployment_setup.sh $(NAMESPACE) $(CONTAINER_ID) $(DB_HOST) $(DB_PORT) $(DB_USERNAME) $(DB_PASSWORD) $(DB_DATABASE)

test_deployment_teardown:
	./test_deployment/test_deployment_teardown.sh $(NAMESPACE)

.PHONY: build_ubuntu build_snapshot_sidecar build_status_sidecar test_deployment_setup test_deployment_teardown
