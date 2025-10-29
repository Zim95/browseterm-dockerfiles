#!/bin/bash

if [ $# -lt 4 ]; then
    echo "Usage: $0 <namespace> <container-id> <db-host> <db-port> <db-username> <db-password> <db-database>"
    exit 1
fi

NAMESPACE=$1
CONTAINER_ID=$2
DB_HOST=$3
DB_PORT=$4
DB_USERNAME=$5
DB_PASSWORD=$6
DB_DATABASE=$7
export NAMESPACE=$NAMESPACE
export CONTAINER_ID=$CONTAINER_ID
export DB_HOST=$DB_HOST
export DB_PORT=$DB_PORT
export DB_USERNAME=$DB_USERNAME
export DB_PASSWORD=$DB_PASSWORD
export DB_DATABASE=$DB_DATABASE

YAML=./test_deployment/test_deployment.yaml

envsubst < $YAML | kubectl apply -n $NAMESPACE -f -
