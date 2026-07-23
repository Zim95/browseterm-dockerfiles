#!/bin/bash
# Remove the reaper CronJob + RBAC. Best-effort.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
set -a; source ../env.mk 2>/dev/null || source env.mk; set +a

kubectl delete cronjob reaper -n "${NAMESPACE}" --ignore-not-found
kubectl delete rolebinding reaper-role-binding -n "${NAMESPACE}" --ignore-not-found
kubectl delete role reaper-role -n "${NAMESPACE}" --ignore-not-found
kubectl delete serviceaccount reaper-service-account -n "${NAMESPACE}" --ignore-not-found
echo "reaper teardown issued"
