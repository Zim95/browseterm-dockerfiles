# Browseterm Dockerfiles
These images are used to build the images for SSH containers that are used in browseterm.

# Currently supported images:
1. Ubuntu

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

2. Now you should be able to use `make` commands to run the build.

3. You can run `make build_all` to build all the required images.
