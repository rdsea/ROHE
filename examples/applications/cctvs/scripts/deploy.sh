#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
APP_NAME="cctvs"
GATEWAY_SVC="web-gateway"

NAMESPACE="${APP_NAME}"
REGISTRY="rdsea"
TAG="0.0.1"
CONTEXT=""
KUBECONFIG_PATH=""
LOAD_IMAGES=false

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Deploy ${APP_NAME} to a Kubernetes cluster."
    echo ""
    echo "Options:"
    echo "  --local              Deploy to local K8s (kind/k3d/minikube)"
    echo "  --remote CONTEXT     Deploy to remote K8s using the specified kubectl context"
    echo "  --kubeconfig PATH    Path to kubeconfig file (for remote clusters)"
    echo "  --namespace NS       Namespace to deploy to (default: ${NAMESPACE})"
    echo "  --registry REG       Image registry prefix (default: ${REGISTRY})"
    echo "  --tag TAG            Image tag (default: ${TAG})"
    echo "  --load-images        Load Docker images into local cluster (kind/k3d)"
    echo "  -h, --help           Show this help"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --local)
            CONTEXT="$(kubectl config current-context 2>/dev/null || echo "")"
            shift
            ;;
        --remote)
            CONTEXT="$2"
            shift 2
            ;;
        --kubeconfig)
            KUBECONFIG_PATH="$2"
            shift 2
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --tag)
            TAG="$2"
            shift 2
            ;;
        --load-images)
            LOAD_IMAGES=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

KUBECTL="kubectl"
if [[ -n "$KUBECONFIG_PATH" ]]; then
    export KUBECONFIG="$KUBECONFIG_PATH"
    echo "Using kubeconfig: ${KUBECONFIG_PATH}"
fi
if [[ -n "$CONTEXT" ]]; then
    KUBECTL="kubectl --context ${CONTEXT}"
    echo "Using context: ${CONTEXT}"
fi

echo "Verifying cluster connectivity..."
if ! $KUBECTL cluster-info &>/dev/null; then
    echo "ERROR: Cannot connect to Kubernetes cluster."
    exit 1
fi
echo "Connected to: $($KUBECTL cluster-info 2>/dev/null | head -1)"

IMAGES=$(grep -rh 'image:' "${APP_DIR}/k8s/" | awk '{print $2}' | sort -u)

if [[ "$LOAD_IMAGES" == true ]]; then
    echo ""
    echo "Loading images into local cluster..."
    if command -v kind &>/dev/null && kind get clusters 2>/dev/null | grep -q .; then
        CLUSTER_NAME=$(kind get clusters 2>/dev/null | head -1)
        for IMG in $IMAGES; do
            echo "  Loading ${IMG}..."
            kind load docker-image "${IMG}" --name "${CLUSTER_NAME}" 2>/dev/null || echo "  WARNING: ${IMG} not found locally"
        done
    elif command -v k3d &>/dev/null && k3d cluster list 2>/dev/null | grep -q .; then
        CLUSTER_NAME=$(k3d cluster list -o json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['name'])" 2>/dev/null || echo "k3s-default")
        for IMG in $IMAGES; do
            echo "  Loading ${IMG}..."
            k3d image import "${IMG}" -c "${CLUSTER_NAME}" 2>/dev/null || echo "  WARNING: ${IMG} not found locally"
        done
    else
        echo "  No kind/k3d detected. Skipping image loading."
    fi
fi

echo ""
echo "=== Deploying ${APP_NAME} ==="
echo "  Namespace: ${NAMESPACE}"
echo ""

$KUBECTL create namespace "${NAMESPACE}" --dry-run=client -o yaml | $KUBECTL apply -f -
$KUBECTL apply -k "${APP_DIR}/k8s/" -n "${NAMESPACE}"

echo ""
echo "Waiting for deployments to be ready (timeout: 300s)..."
$KUBECTL -n "${NAMESPACE}" wait --for=condition=available deployment --all --timeout=300s || {
    echo "WARNING: Some deployments did not become ready in time."
    $KUBECTL -n "${NAMESPACE}" get pods
    exit 1
}

echo ""
echo "=== Deployment Status ==="
$KUBECTL -n "${NAMESPACE}" get pods -o wide
echo ""
$KUBECTL -n "${NAMESPACE}" get services
echo ""
echo "Deployment complete."
echo ""
echo "To access the gateway:"
echo "  $KUBECTL -n ${NAMESPACE} port-forward svc/${GATEWAY_SVC} 8000:8000"
