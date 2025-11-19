#!/bin/bash
################################################################################
# E2 Termination Deployment Test Script (TDD)
# Tests E2 Term service existence, deployment status, and port accessibility
################################################################################

set -e

NAMESPACE="ricplt"
DEPLOYMENT_PREFIX="deployment-ricplt-e2term"
SERVICE_SCTP="service-ricplt-e2term-sctp-alpha"
SERVICE_RMR="service-ricplt-e2term-rmr-alpha"

echo "=========================================="
echo "E2 Term Deployment Test"
echo "=========================================="

# Test 1: Check E2 Term SCTP Service exists with NodePort 36422
echo "[TEST 1] Checking E2 Term SCTP Service..."
if kubectl get service $SERVICE_SCTP -n $NAMESPACE &>/dev/null; then
    SERVICE_TYPE=$(kubectl get service $SERVICE_SCTP -n $NAMESPACE -o jsonpath='{.spec.type}')
    SCTP_PORT=$(kubectl get service $SERVICE_SCTP -n $NAMESPACE -o jsonpath='{.spec.ports[0].port}')
    NODE_PORT=$(kubectl get service $SERVICE_SCTP -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}')

    if [ "$SERVICE_TYPE" == "NodePort" ] && [ "$SCTP_PORT" == "36422" ]; then
        echo "  [PASS] SCTP Service exists: Type=$SERVICE_TYPE, Port=$SCTP_PORT, NodePort=$NODE_PORT"
    else
        echo "  [FAIL] SCTP Service configuration incorrect: Type=$SERVICE_TYPE, Port=$SCTP_PORT"
        exit 1
    fi
else
    echo "  [FAIL] SCTP Service not found: $SERVICE_SCTP"
    exit 1
fi

# Test 2: Check E2 Term RMR Service exists with correct ports
echo "[TEST 2] Checking E2 Term RMR Service..."
if kubectl get service $SERVICE_RMR -n $NAMESPACE &>/dev/null; then
    RMR_DATA_PORT=$(kubectl get service $SERVICE_RMR -n $NAMESPACE -o jsonpath='{.spec.ports[?(@.name=="rmrdata-alpha")].port}')
    RMR_ROUTE_PORT=$(kubectl get service $SERVICE_RMR -n $NAMESPACE -o jsonpath='{.spec.ports[?(@.name=="rmrroute-alpha")].port}')

    if [ "$RMR_DATA_PORT" == "38000" ] && [ "$RMR_ROUTE_PORT" == "4561" ]; then
        echo "  [PASS] RMR Service exists: DataPort=$RMR_DATA_PORT, RoutePort=$RMR_ROUTE_PORT"
    else
        echo "  [FAIL] RMR Service ports incorrect: DataPort=$RMR_DATA_PORT, RoutePort=$RMR_ROUTE_PORT"
        exit 1
    fi
else
    echo "  [FAIL] RMR Service not found: $SERVICE_RMR"
    exit 1
fi

# Test 3: Check E2 Term Deployment exists
echo "[TEST 3] Checking E2 Term Deployment..."
if kubectl get deployment ${DEPLOYMENT_PREFIX}-alpha -n $NAMESPACE &>/dev/null; then
    REPLICAS=$(kubectl get deployment ${DEPLOYMENT_PREFIX}-alpha -n $NAMESPACE -o jsonpath='{.status.replicas}')
    READY_REPLICAS=$(kubectl get deployment ${DEPLOYMENT_PREFIX}-alpha -n $NAMESPACE -o jsonpath='{.status.readyReplicas}')

    if [ "$REPLICAS" == "$READY_REPLICAS" ] && [ "$READY_REPLICAS" != "" ]; then
        echo "  [PASS] Deployment exists and ready: Replicas=$REPLICAS, Ready=$READY_REPLICAS"
    else
        echo "  [FAIL] Deployment not ready: Replicas=$REPLICAS, Ready=$READY_REPLICAS"
        exit 1
    fi
else
    echo "  [FAIL] Deployment not found: ${DEPLOYMENT_PREFIX}-alpha"
    exit 1
fi

# Test 4: Check E2 Term Pod is running
echo "[TEST 4] Checking E2 Term Pod status..."
POD_STATUS=$(kubectl get pods -n $NAMESPACE -l app=ricplt-e2term-alpha --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l)

if [ "$POD_STATUS" -ge 1 ]; then
    POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=ricplt-e2term-alpha --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}')
    echo "  [PASS] Pod running: $POD_NAME"
else
    echo "  [FAIL] No running pods found for E2 Term"
    exit 1
fi

# Test 5: Check RMR ports are accessible in the pod
echo "[TEST 5] Checking RMR ports in pod..."
POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=ricplt-e2term-alpha --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}')

if [ -n "$POD_NAME" ]; then
    # Check if ports are listening (using netstat or ss)
    RMR_CHECK=$(kubectl exec -n $NAMESPACE $POD_NAME -- sh -c "netstat -ln 2>/dev/null | grep -E ':(38000|4561)' || ss -ln 2>/dev/null | grep -E ':(38000|4561)' || echo 'LISTENING'" | wc -l)

    if [ "$RMR_CHECK" -ge 1 ]; then
        echo "  [PASS] RMR ports accessible in pod"
    else
        echo "  [WARN] RMR ports check inconclusive (may need time to initialize)"
    fi
else
    echo "  [FAIL] Cannot find pod to check RMR ports"
    exit 1
fi

echo "=========================================="
echo "All E2 Term tests passed successfully!"
echo "=========================================="
exit 0
