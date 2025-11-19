#!/bin/bash
# TDD Test: E2 Manager Deployment
# Tests E2 Manager service, deployment, and port accessibility

set -e

NAMESPACE="ricplt"
APP_LABEL="app=ricplt-e2mgr"
SERVICE_NAME="service-ricplt-e2mgr"
HTTP_PORT=3800
RMR_PORT=3801

echo "=============================="
echo "E2 Manager Deployment Tests"
echo "=============================="

# Test 1: E2 Manager service exists
echo ""
echo "[TEST 1] Checking if E2 Manager service exists..."
if kubectl get service ${SERVICE_NAME}-http -n ${NAMESPACE} >/dev/null 2>&1; then
    echo "✓ PASS: E2 Manager HTTP service exists"
else
    echo "✗ FAIL: E2 Manager HTTP service not found"
    exit 1
fi

if kubectl get service ${SERVICE_NAME}-rmr -n ${NAMESPACE} >/dev/null 2>&1; then
    echo "✓ PASS: E2 Manager RMR service exists"
else
    echo "✗ FAIL: E2 Manager RMR service not found"
    exit 1
fi

# Test 2: E2 Manager deployment exists
echo ""
echo "[TEST 2] Checking if E2 Manager deployment exists..."
if kubectl get deployment -l ${APP_LABEL} -n ${NAMESPACE} >/dev/null 2>&1; then
    DEPLOYMENT_NAME=$(kubectl get deployment -l ${APP_LABEL} -n ${NAMESPACE} -o jsonpath='{.items[0].metadata.name}')
    echo "✓ PASS: E2 Manager deployment exists: ${DEPLOYMENT_NAME}"
else
    echo "✗ FAIL: E2 Manager deployment not found"
    exit 1
fi

# Test 3: E2 Manager pods are running
echo ""
echo "[TEST 3] Checking if E2 Manager pods are running..."
POD_STATUS=$(kubectl get pods -l ${APP_LABEL} -n ${NAMESPACE} -o jsonpath='{.items[*].status.phase}')
if [[ "${POD_STATUS}" == *"Running"* ]]; then
    POD_COUNT=$(kubectl get pods -l ${APP_LABEL} -n ${NAMESPACE} --no-headers | wc -l)
    READY_COUNT=$(kubectl get pods -l ${APP_LABEL} -n ${NAMESPACE} -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}' | grep -o "True" | wc -l)
    echo "✓ PASS: E2 Manager pods running (${READY_COUNT}/${POD_COUNT} ready)"
else
    echo "✗ FAIL: E2 Manager pods not in Running state: ${POD_STATUS}"
    exit 1
fi

# Test 4: HTTP API port is accessible
echo ""
echo "[TEST 4] Checking if HTTP API port ${HTTP_PORT} is accessible..."
HTTP_PORT_CHECK=$(kubectl get service ${SERVICE_NAME}-http -n ${NAMESPACE} -o jsonpath='{.spec.ports[?(@.name=="http")].port}')
if [[ "${HTTP_PORT_CHECK}" == "${HTTP_PORT}" ]]; then
    echo "✓ PASS: HTTP API port ${HTTP_PORT} is configured"
else
    echo "✗ FAIL: HTTP API port mismatch. Expected: ${HTTP_PORT}, Got: ${HTTP_PORT_CHECK}"
    exit 1
fi

# Test 5: RMR port is accessible
echo ""
echo "[TEST 5] Checking if RMR port ${RMR_PORT} is accessible..."
RMR_PORT_CHECK=$(kubectl get service ${SERVICE_NAME}-rmr -n ${NAMESPACE} -o jsonpath='{.spec.ports[?(@.name=="rmrdata")].port}')
if [[ "${RMR_PORT_CHECK}" == "${RMR_PORT}" ]]; then
    echo "✓ PASS: RMR port ${RMR_PORT} is configured"
else
    echo "✗ FAIL: RMR port mismatch. Expected: ${RMR_PORT}, Got: ${RMR_PORT_CHECK}"
    exit 1
fi

echo ""
echo "=============================="
echo "All E2 Manager tests PASSED!"
echo "=============================="
