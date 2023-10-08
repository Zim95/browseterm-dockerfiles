# WebtermLab Dockerfiles
Dockerfiles for webtermlab

# Building the images
- Build from the root directory always. This is because the `Dockerfiles` copy their respective `entrypoint.sh` files from the root directory.
- Here is the command to build.
  ```
  docker image build -t <image_name>:<image_tag> -f ./<directory_name>/<Dockerfile_name> .
  ```
- Example
  ```
  docker image build -t ssh_ubuntu:latest -f ./ubuntu_setup/Dockerfile.ubuntu .
  ```

# Push to repository
- To push to repository, please run the associated push script.
- For example, to push `ubuntu_setup`
  ```
  ./ubuntu_setup/ubuntu.push.sh
  ```
