#!/bin/bash
# E2E test script for all 4 ROHE example applications.
# Usage:
#   ./e2e_test.sh                              # test current cluster
#   ./e2e_test.sh --context kind-rohe-local    # specify context

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KUBECTL="kubectl"
CONTEXT=""
PASS=0
FAIL=0

while [[ $# -gt 0 ]]; do
    case $1 in
        --context) CONTEXT="$2"; KUBECTL="kubectl --context $2"; shift 2 ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

if [[ -z "$CONTEXT" ]]; then
    CONTEXT="$(kubectl config current-context 2>/dev/null || true)"
    [[ -n "$CONTEXT" ]] && KUBECTL="kubectl --context $CONTEXT"
fi

pass() { PASS=$((PASS+1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL+1)); echo "  FAIL: $1"; }

echo "============================================"
echo "  ROHE E2E Pipeline Test ($CONTEXT)"
echo "============================================"
echo ""

PF_PIDS=""
cleanup() { [[ -n "$PF_PIDS" ]] && kill $PF_PIDS 2>/dev/null; wait $PF_PIDS 2>/dev/null; }
trap cleanup EXIT

PORT=9950

run_app_test() {
    local app="$1" ns="$2" gw_svc="$3" expected="$4" payload="$5"
    local gw_port=$PORT
    local orc_port=$((PORT+1))
    PORT=$((PORT+2))

    echo "--- ${app} (ns: ${ns}) ---"

    # Check pods
    local running
    running=$($KUBECTL -n "$ns" get pods --no-headers 2>/dev/null | grep -c "Running" || echo "0")
    if [[ "$running" -gt 0 ]]; then
        pass "${running} pods running"
    else
        fail "No running pods in ${ns}"
        echo ""
        return
    fi

    # Port forward
    $KUBECTL -n "$ns" port-forward "svc/${gw_svc}" "${gw_port}:8000" &>/dev/null &
    PF_PIDS="$PF_PIDS $!"
    $KUBECTL -n "$ns" port-forward svc/orchestrator "${orc_port}:9000" &>/dev/null &
    PF_PIDS="$PF_PIDS $!"
    sleep 4

    # Gateway health
    local gw_health
    gw_health=$(curl -sf "http://localhost:${gw_port}/health" 2>/dev/null || echo "")
    if echo "$gw_health" | grep -q '"ok"'; then
        pass "Gateway healthy"
    else
        fail "Gateway unreachable"
    fi

    # Orchestrator health
    local orc_health plans redis
    orc_health=$(curl -sf "http://localhost:${orc_port}/health" 2>/dev/null || echo "{}")
    plans=$(echo "$orc_health" | python3 -c "import sys,json; print(json.load(sys.stdin).get('plans_loaded',0))" 2>/dev/null || echo "0")
    redis=$(echo "$orc_health" | python3 -c "import sys,json; print(json.load(sys.stdin).get('redis_connected',False))" 2>/dev/null || echo "?")
    if [[ "$plans" -ge 1 ]]; then
        pass "Orchestrator: plans=${plans}, redis=${redis}"
    else
        fail "Orchestrator: plans=${plans}"
    fi

    # Full pipeline predict
    local result model_count
    result=$(curl -sf -X POST "http://localhost:${gw_port}/predict" \
        -H "Content-Type: application/json" -d "$payload" 2>/dev/null || echo "{}")

    model_count=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('model_count',0))" 2>/dev/null || echo "0")
    if [[ "$model_count" -ge "$expected" ]]; then
        pass "Pipeline: ${model_count} models (expected>=${expected})"
        echo "$result" | python3 -c "
import sys,json
d=json.load(sys.stdin)
e=d.get('ensemble_result',{})
top3=', '.join(f'{k}={v:.3f}' for k,v in list(e.items())[:3])
print(f'    Ensemble: {top3}')
for r in d.get('individual_results',[]):
    print(f'    {r[\"model\"]:20s} conf={r[\"confidence\"]:.4f}  {r[\"response_time_ms\"]:7.1f}ms')
" 2>/dev/null
    else
        fail "Pipeline: model_count=${model_count} (expected>=${expected})"
    fi

    echo ""
}

run_app_test "BTS" "bts" "gateway" "4" \
    '{"query_id":"e2e-bts","data":"bts-00001","modalities":["timeseries"]}'

run_app_test "CCTVS" "cctvs" "web-gateway" "5" \
    '{"query_id":"e2e-cctvs","data":"cctvs-00001","modalities":["image"]}'

run_app_test "ObjClass" "object-classification" "gateway" "4" \
    '{"query_id":"e2e-objclass","data":"objclass-00001","modalities":["image"]}'

run_app_test "SmartBuilding" "smart-building" "control-plane" "8" \
    '{"query_id":"e2e-sb","data":"sb-00001","modalities":["video","timeseries"]}'

echo "============================================"
TOTAL=$((PASS+FAIL))
if [[ "$FAIL" -eq 0 ]]; then
    echo "  ALL PASSED: ${PASS}/${TOTAL}"
else
    echo "  FAILED: ${FAIL}/${TOTAL} (${PASS} passed)"
fi
echo "============================================"

exit "$FAIL"
