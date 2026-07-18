# Variables
include env.mk

# Development

dev_build:
	./scripts/development/development-build.sh $(USER_NAME) $(REPO_NAME)

dev_setup:
	./scripts/development/development-setup.sh $(NAMESPACE) $(HOST_DIR) $(REPO_NAME)

dev_teardown:
	./scripts/development/development-teardown.sh $(NAMESPACE)

# Production

prod_build:
	./scripts/deployment/build.sh $(USER_NAME) $(REPO_NAME)

.PHONY: dev_build dev_setup dev_teardown prod_build
