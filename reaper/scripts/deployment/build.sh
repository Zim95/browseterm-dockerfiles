#!/bin/bash
# Build + push the reaper image. Usage: ./scripts/deployment/build.sh <docker-username> <docker-repository>
if [ $# -lt 2 ]; then
    echo "Usage: $0 <docker-username> <docker-repository>"
    exit 1
fi

USERNAME=$1
REPOSITORY=$2
IMAGE_NAME=reaper
IMAGE_TAG=latest
DOCKERFILE=./infra/deployment/Dockerfile

docker login -u "$USERNAME"
docker image build --no-cache -t "$IMAGE_NAME:$IMAGE_TAG" -f "$DOCKERFILE" .
docker image tag "$IMAGE_NAME:$IMAGE_TAG" "$REPOSITORY/$IMAGE_NAME:$IMAGE_TAG"
docker push "$REPOSITORY/$IMAGE_NAME:$IMAGE_TAG"
