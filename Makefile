# Variables
include env.mk

# NOTE: snapshot_job, status_sidecar and reaper moved to the browseterm_workload repo.
# This repo now only builds the user-facing terminal image (ubuntu_setup).
build_ubuntu:
	./ubuntu_setup/ubuntu.build.sh $(USER_NAME) $(REPO_NAME)

build_all: build_ubuntu

test_deployment_setup:
	./test_deployment/test_deployment_setup.sh $(NAMESPACE) $(REPO_NAME) $(CONTAINER_ID) $(DB_HOST) $(DB_PORT) $(DB_USERNAME) $(DB_PASSWORD) $(DB_DATABASE)

test_deployment_teardown:
	./test_deployment/test_deployment_teardown.sh $(NAMESPACE)

.PHONY: build_ubuntu build_all test_deployment_setup test_deployment_teardown
