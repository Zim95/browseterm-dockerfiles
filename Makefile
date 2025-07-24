# Variables
include env.mk

build_ubuntu:
	./ubuntu_setup/ubuntu.build.sh $(USER_NAME) $(REPO_NAME)

build_snapshot_sidecar:
	./snapshot_sidecar/build.sh $(USER_NAME) $(REPO_NAME)

.PHONY: build_ubuntu build_snapshot_sidecar
