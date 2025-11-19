#!/bin/bash

# RTMgr Deployment Test Script
# Purpose: Verify RTMgr deployment following TDD principles

NAMESPACE="ricplt"
APP_LABEL="app=ricplt-rtmgr"
SERVICE_NAME="service-ricplt-rtmgr-http"
RMR_SERVICE_NAME="service-ricplt-rtmgr-rmr"
RMR_PORT=4561
HTTP_PORT=3800

echo "=========================================="
echo "RTMgr Deployment Test Suite"
echo "=========================================="

TEST_PASSED=0
TEST_FAILED=0

# Test 1: Check if RTMgr service exists
echo ""
echo "Test 1: Checking if RTMgr HTTP service exists..."
if kubectl get service $SERVICE_NAME -n $NAMESPACE &>/dev/null; then
    echo "✓ PASS: RTMgr HTTP service exists"
    ((TEST_PASSED++))
else
    echo "✗ FAIL: RTMgr HTTP service not found"
    ((TEST_FAILED++))
fi

# Test 2: Check if RTMgr RMR service exists
echo ""
echo "Test 2: Checking if RTMgr RMR service exists..."
if kubectl get service $RMR_SERVICE_NAME -n $NAMESPACE &>/dev/null; then
    echo "✓ PASS: RTMgr RMR service exists"
    ((TEST_PASSED++))
else
    echo "✗ FAIL: RTMgr RMR service not found"
    ((TEST_FAILED++))
fi

# Test 3: Check if RTMgr deployment exists
echo ""
echo "Test 3: Checking if RTMgr deployment exists..."
DEPLOYMENT_COUNT=$(kubectl get deployment -n $NAMESPACE -l $APP_LABEL --no-headers 2>/dev/null | wc -l)
if [ "$DEPLOYMENT_COUNT" -gt 0 ]; then
    echo "✓ PASS: RTMgr deployment exists (count: $DEPLOYMENT_COUNT)"
    ((TEST_PASSED++))
else
    echo "✗ FAIL: RTMgr deployment not found"
    ((TEST_FAILED++))
fi

# Test 4: Check if RTMgr pods are running
echo ""
echo "Test 4: Checking if RTMgr pods are running..."
RUNNING_PODS=$(kubectl get pods -n $NAMESPACE -l $APP_LABEL --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l)
if [ "$RUNNING_PODS" -gt 0 ]; then
    echo "✓ PASS: RTMgr pods are running (count: $RUNNING_PODS)"
    ((TEST_PASSED++))

    # Show pod details
    echo "  Pod details:"
    kubectl get pods -n $NAMESPACE -l $APP_LABEL --no-headers 2>/dev/null | while read line; do
        echo "    $line"
    done
else
    echo "✗ FAIL: No RTMgr pods are running"
    ((TEST_FAILED++))
fi

# Test 5: Check if RMR routing port is accessible
echo ""
echo "Test 5: Checking if RMR routing port ($RMR_PORT) is accessible..."
if kubectl get service $RMR_SERVICE_NAME -n $NAMESPACE -o jsonpath='{.spec.ports[?(@.port=='$RMR_PORT')].port}' 2>/dev/null | grep -q $RMR_PORT; then
    echo "✓ PASS: RMR routing port $RMR_PORT is accessible"
    ((TEST_PASSED++))
else
    echo "✗ FAIL: RMR routing port $RMR_PORT is not accessible"
    ((TEST_FAILED++))
fi

# Test 6: Check if HTTP API port is accessible
echo ""
echo "Test 6: Checking if HTTP API port ($HTTP_PORT) is accessible..."
if kubectl get service $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.spec.ports[?(@.port=='$HTTP_PORT')].port}' 2>/dev/null | grep -q $HTTP_PORT; then
    echo "✓ PASS: HTTP API port $HTTP_PORT is accessible"
    ((TEST_PASSED++))
else
    echo "✗ FAIL: HTTP API port $HTTP_PORT is not accessible"
    ((TEST_FAILED++))
fi

# Test 7: Check if pods are ready
echo ""
echo "Test 7: Checking if RTMgr pods are ready..."
READY_PODS=$(kubectl get pods -n $NAMESPACE -l $APP_LABEL -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}' 2>/dev/null | grep -o "True" | wc -l)
if [ "$READY_PODS" -gt 0 ]; then
    echo "✓ PASS: RTMgr pods are ready (count: $READY_PODS)"
    ((TEST_PASSED++))
else
    echo "✗ FAIL: RTMgr pods are not ready"
    ((TEST_FAILED++))
fi

# Summary
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "PASSED: $TEST_PASSED"
echo "FAILED: $TEST_FAILED"
echo "TOTAL:  $((TEST_PASSED + TEST_FAILED))"
echo "=========================================="

if [ $TEST_FAILED -gt 0 ]; then
    echo "Result: FAILED"
    exit 1
else
    echo "Result: SUCCESS"
    exit 0
fi
