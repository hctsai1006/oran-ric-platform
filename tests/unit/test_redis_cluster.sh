#!/bin/bash
# Redis Cluster Unit Test
# Tests Redis Cluster deployment and connectivity

set -e

echo "=========================================="
echo "Redis Cluster Unit Test"
echo "=========================================="
echo ""

# Test 1: Redis StatefulSet exists
echo "[1/3] Checking Redis Cluster StatefulSet..."
if kubectl get statefulset -n ricplt redis-cluster >/dev/null 2>&1; then
    echo "  ✅ Redis Cluster StatefulSet exists"
else
    echo "  ❌ Redis Cluster StatefulSet not found"
    exit 1
fi

# Test 2: Redis pods are running
echo "[2/3] Checking Redis pods status..."
READY_PODS=$(kubectl get pods -n ricplt -l app.kubernetes.io/instance=r4-redis-cluster --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l)

if [ "$READY_PODS" -ge 1 ]; then
    echo "  ✅ Redis pods running: $READY_PODS/3"
else
    echo "  ❌ No Redis pods running"
    exit 1
fi

# Test 3: Redis is accessible
echo "[3/3] Testing Redis connectivity..."
POD_NAME=$(kubectl get pods -n ricplt -l app.kubernetes.io/instance=r4-redis-cluster -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -n "$POD_NAME" ]; then
    if kubectl exec -n ricplt "$POD_NAME" -- redis-cli ping 2>&1 | grep -q "PONG"; then
        echo "  ✅ Redis responds to PING"
    else
        echo "  ❌ Redis PING failed"
        exit 1
    fi
else
    echo "  ❌ No Redis pod found"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Redis Cluster test passed"
echo "=========================================="
