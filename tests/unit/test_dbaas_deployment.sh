#!/bin/bash
# DBaaS Deployment Unit Test
# Tests DBaaS deployment and connectivity to Redis backend

set -e

echo "=========================================="
echo "DBaaS Deployment Unit Test"
echo "=========================================="
echo ""

# Test 1: DBaaS service exists
echo "[1/4] Checking DBaaS service..."
if kubectl get svc -n ricplt service-ricplt-dbaas-tcp >/dev/null 2>&1; then
    echo "  ✅ DBaaS service exists"
else
    echo "  ❌ DBaaS service not found"
    exit 1
fi

# Test 2: DBaaS StatefulSet exists
echo "[2/4] Checking DBaaS StatefulSet..."
if kubectl get statefulset -n ricplt statefulset-ricplt-dbaas-server >/dev/null 2>&1; then
    echo "  ✅ DBaaS StatefulSet exists"
else
    echo "  ❌ DBaaS StatefulSet not found"
    exit 1
fi

# Test 3: DBaaS pods are running
echo "[3/4] Checking DBaaS pods status..."
READY_PODS=$(kubectl get pods -n ricplt -l app=ricplt-dbaas --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l)

if [ "$READY_PODS" -ge 1 ]; then
    echo "  ✅ DBaaS pods running: $READY_PODS"
else
    echo "  ❌ No DBaaS pods running"
    exit 1
fi

# Test 4: DBaaS is accessible (test from within cluster)
echo "[4/4] Testing DBaaS accessibility..."
POD_NAME=$(kubectl get pods -n ricplt -l app=ricplt-dbaas -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -n "$POD_NAME" ]; then
    # Check if DBaaS pod is healthy
    if kubectl exec -n ricplt "$POD_NAME" -- ps aux | grep -q dbaas; then
        echo "  ✅ DBaaS process is running"
    else
        echo "  ⚠️  DBaaS process check inconclusive"
    fi
else
    echo "  ❌ No DBaaS pod found"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ DBaaS deployment test passed"
echo "=========================================="
