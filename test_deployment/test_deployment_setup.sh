#!/bin/bash

if [ $# -lt 4 ]; then
    echo "Usage: $0 <namespace> <repo-name> <container-id> <db-host> <db-port> <db-username> <db-password> <db-database>"
    exit 1
fi

NAMESPACE=$1
REPO_NAME=$2
CONTAINER_ID=$3
DB_HOST=$4
DB_PORT=$5
DB_USERNAME=$6
DB_PASSWORD=$7
DB_DATABASE=$8
export NAMESPACE=$NAMESPACE
export CONTAINER_ID=$CONTAINER_ID
export REPO_NAME=$REPO_NAME
export DB_HOST=$DB_HOST
export DB_PORT=$DB_PORT
export DB_USERNAME=$DB_USERNAME
export DB_PASSWORD=$DB_PASSWORD
export DB_DATABASE=$DB_DATABASE

YAML=./test_deployment/test_deployment.yaml

envsubst < $YAML | kubectl apply -n $NAMESPACE -f -
