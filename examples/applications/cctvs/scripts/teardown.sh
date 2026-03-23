#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
NAMESPACE="${1:-cctvs}"

echo "Tearing down CCTVS from namespace: ${NAMESPACE}"
kubectl delete -k "${APP_DIR}/k8s/" -n "${NAMESPACE}" --ignore-not-found
echo "Teardown complete."
