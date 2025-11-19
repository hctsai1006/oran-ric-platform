#!/bin/bash
# TDD Test: A1 Mediator Deployment
# Tests A1 Mediator service, deployment, and port accessibility

set -e

NAMESPACE="ricplt"
APP_LABEL="app=ricplt-a1mediator"
SERVICE_NAME="service-ricplt-a1mediator"
HTTP_PORT=10000
RMR_DATA_PORT=4562
RMR_ROUTE_PORT=4561

echo "=============================="
echo "A1 Mediator Deployment Tests"
echo "=============================="

# Test 1: A1 Mediator service exists
echo ""
echo "[TEST 1] Checking if A1 Mediator service exists..."
if kubectl get service ${SERVICE_NAME}-http -n ${NAMESPACE} >/dev/null 2>&1; then
    echo "✓ PASS: A1 Mediator HTTP service exists"
else
    echo "✗ FAIL: A1 Mediator HTTP service not found"
    exit 1
fi

if kubectl get service ${SERVICE_NAME}-rmr -n ${NAMESPACE} >/dev/null 2>&1; then
    echo "✓ PASS: A1 Mediator RMR service exists"
else
    echo "✗ FAIL: A1 Mediator RMR service not found"
    exit 1
fi

# Test 2: A1 Mediator deployment exists
echo ""
echo "[TEST 2] Checking if A1 Mediator deployment exists..."
if kubectl get deployment -l ${APP_LABEL} -n ${NAMESPACE} >/dev/null 2>&1; then
    DEPLOYMENT_NAME=$(kubectl get deployment -l ${APP_LABEL} -n ${NAMESPACE} -o jsonpath='{.items[0].metadata.name}')
    echo "✓ PASS: A1 Mediator deployment exists: ${DEPLOYMENT_NAME}"
else
    echo "✗ FAIL: A1 Mediator deployment not found"
    exit 1
fi

# Test 3: A1 Mediator pods are running
echo ""
echo "[TEST 3] Checking if A1 Mediator pods are running..."
POD_STATUS=$(kubectl get pods -l ${APP_LABEL} -n ${NAMESPACE} -o jsonpath='{.items[*].status.phase}')
if [[ "${POD_STATUS}" == *"Running"* ]]; then
    POD_COUNT=$(kubectl get pods -l ${APP_LABEL} -n ${NAMESPACE} --no-headers | wc -l)
    READY_COUNT=$(kubectl get pods -l ${APP_LABEL} -n ${NAMESPACE} -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}' | grep -o "True" | wc -l)
    echo "✓ PASS: A1 Mediator pods running (${READY_COUNT}/${POD_COUNT} ready)"
else
    echo "✗ FAIL: A1 Mediator pods not in Running state: ${POD_STATUS}"
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

# Test 5: RMR data port is accessible
echo ""
echo "[TEST 5] Checking if RMR data port ${RMR_DATA_PORT} is accessible..."
RMR_DATA_PORT_CHECK=$(kubectl get service ${SERVICE_NAME}-rmr -n ${NAMESPACE} -o jsonpath='{.spec.ports[?(@.name=="rmrdata")].port}')
if [[ "${RMR_DATA_PORT_CHECK}" == "${RMR_DATA_PORT}" ]]; then
    echo "✓ PASS: RMR data port ${RMR_DATA_PORT} is configured"
else
    echo "✗ FAIL: RMR data port mismatch. Expected: ${RMR_DATA_PORT}, Got: ${RMR_DATA_PORT_CHECK}"
    exit 1
fi

# Test 6: RMR route port is accessible
echo ""
echo "[TEST 6] Checking if RMR route port ${RMR_ROUTE_PORT} is accessible..."
RMR_ROUTE_PORT_CHECK=$(kubectl get service ${SERVICE_NAME}-rmr -n ${NAMESPACE} -o jsonpath='{.spec.ports[?(@.name=="rmrroute")].port}')
if [[ "${RMR_ROUTE_PORT_CHECK}" == "${RMR_ROUTE_PORT}" ]]; then
    echo "✓ PASS: RMR route port ${RMR_ROUTE_PORT} is configured"
else
    echo "✗ FAIL: RMR route port mismatch. Expected: ${RMR_ROUTE_PORT}, Got: ${RMR_ROUTE_PORT_CHECK}"
    exit 1
fi

# Test 7: Environment variables are configured
echo ""
echo "[TEST 7] Checking if required environment variables are configured..."
POD_NAME=$(kubectl get pods -l ${APP_LABEL} -n ${NAMESPACE} -o jsonpath='{.items[0].metadata.name}')

# Check environment variables by executing env inside the container
ENV_OUTPUT=$(kubectl exec ${POD_NAME} -n ${NAMESPACE} -- env 2>/dev/null)

# Check RMR_RTG_SVC
if echo "${ENV_OUTPUT}" | grep -q "RMR_RTG_SVC="; then
    RMR_RTG_SVC=$(echo "${ENV_OUTPUT}" | grep "RMR_RTG_SVC=" | cut -d= -f2)
    echo "✓ PASS: RMR_RTG_SVC is configured: ${RMR_RTG_SVC}"
else
    echo "✗ FAIL: RMR_RTG_SVC is not configured"
    exit 1
fi

# Check DBAAS_SERVICE_HOST
if echo "${ENV_OUTPUT}" | grep -q "DBAAS_SERVICE_HOST="; then
    DBAAS_HOST=$(echo "${ENV_OUTPUT}" | grep "DBAAS_SERVICE_HOST=" | cut -d= -f2)
    echo "✓ PASS: DBAAS_SERVICE_HOST is configured: ${DBAAS_HOST}"
else
    echo "✗ FAIL: DBAAS_SERVICE_HOST is not configured"
    exit 1
fi

# Check DBAAS_SERVICE_PORT
if echo "${ENV_OUTPUT}" | grep -q "DBAAS_SERVICE_PORT="; then
    DBAAS_PORT=$(echo "${ENV_OUTPUT}" | grep "DBAAS_SERVICE_PORT=" | cut -d= -f2)
    echo "✓ PASS: DBAAS_SERVICE_PORT is configured: ${DBAAS_PORT}"
else
    echo "✗ FAIL: DBAAS_SERVICE_PORT is not configured"
    exit 1
fi

# Test 8: A1 Mediator container image version
echo ""
echo "[TEST 8] Checking A1 Mediator container image version..."
IMAGE=$(kubectl get deployment -l ${APP_LABEL} -n ${NAMESPACE} -o jsonpath='{.items[0].spec.template.spec.containers[0].image}')
if [[ "${IMAGE}" == *"ric-plt-a1"* ]]; then
    echo "✓ PASS: A1 Mediator image is correct: ${IMAGE}"
else
    echo "✗ FAIL: A1 Mediator image is incorrect: ${IMAGE}"
    exit 1
fi

echo ""
echo "=============================="
echo "All A1 Mediator tests PASSED!"
echo "=============================="
