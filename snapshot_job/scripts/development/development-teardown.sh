#!/bin/bash

# Check if enough arguments are provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 <namespace>"
    exit 1
fi

YAML=./infra/development/development.yaml
NAMESPACE=$1

export NAMESPACE=$NAMESPACE

# Load shared env vars from env.mk if present (for DB, repo, etc.)
if [ -f ../env.mk ]; then
  set -a
  source ../env.mk
  set +a
fi

# Delete namespace-scoped resources with the provided namespace
envsubst < "$YAML" | kubectl delete -n "$NAMESPACE" -f -
