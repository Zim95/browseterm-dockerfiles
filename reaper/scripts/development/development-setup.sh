#!/bin/bash
# Deploy the reaper CronJob (+ RBAC) to the cluster. Sources ../env.mk for the templated values.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
set -a; source ../env.mk 2>/dev/null || source env.mk; set +a

envsubst < ./infra/deployment/deployment.yaml | kubectl apply -f -
echo "reaper CronJob applied (namespace ${NAMESPACE}, schedule hourly, idle ${IDLE_THRESHOLD_SECONDS}s)"
