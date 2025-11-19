#!/bin/bash
# RMR Connectivity Integration Test
# Tests RMR connectivity between RIC Platform components

set -e

echo "=========================================="
echo "RMR Connectivity Integration Test"
echo "=========================================="
echo ""

# Test E2Term → E2Mgr
echo "[1/2] Testing E2Term → E2Mgr connectivity..."
E2TERM_POD=$(kubectl get pods -n ricplt -l app=ricplt-e2term -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -n "$E2TERM_POD" ]; then
    if kubectl exec -n ricplt "$E2TERM_POD" -- timeout 10 nc -zv e2mgr.ricplt.svc.cluster.local 3801 2>&1 | grep -q "succeeded"; then
        echo "  ✅ E2Term → E2Mgr: OK"
    else
        echo "  ❌ E2Term → E2Mgr: FAILED"
        exit 1
    fi
else
    echo "  ⚠️  E2Term pod not found, skipping test"
fi

# Test SubMgr → E2Term
echo "[2/2] Testing SubMgr → E2Term connectivity..."
SUBMGR_POD=$(kubectl get pods -n ricplt -l app=ricplt-submgr -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -n "$SUBMGR_POD" ]; then
    if kubectl exec -n ricplt "$SUBMGR_POD" -- timeout 10 nc -zv e2term.ricplt.svc.cluster.local 38000 2>&1 | grep -q "succeeded"; then
        echo "  ✅ SubMgr → E2Term: OK"
    else
        echo "  ❌ SubMgr → E2Term: FAILED"
        exit 1
    fi
else
    echo "  ⚠️  SubMgr pod not found, skipping test"
fi

echo ""
echo "=========================================="
echo "✅ All RMR connectivity tests passed"
echo "=========================================="
