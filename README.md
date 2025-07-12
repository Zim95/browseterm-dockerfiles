# Browseterm Dockerfiles
These images are used to build the images for SSH containers that are used in browseterm.

# Currently supported images:
1. Ubuntu

# How to build
1. Create an `env.mk` file at the root of the repository with the following contents:
  ```Makefile
  REPO_NAME=<image-repository-name>
  USER_NAME=<respository-user-name>
  NAMESPACE=<repository-namespace>
  HOST_DIR=<current-working-directory>
  ```

2. Now you should be able to use `make` commands to run the build:
  a. Ubuntu:
    ```bash
    make build_ubuntu
    ```
