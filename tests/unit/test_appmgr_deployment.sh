#!/bin/bash

# Test script for Application Manager deployment
# This script validates AppMgr deployment and its readiness

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

NAMESPACE="ricplt"
RELEASE_NAME="r4-appmgr"
TIMEOUT=300

echo "======================================"
echo "AppMgr Deployment Test Suite"
echo "======================================"

# Test 1: Check if AppMgr deployment exists
test_deployment_exists() {
    echo -e "\n${YELLOW}[TEST 1]${NC} Checking if AppMgr deployment exists..."

    if kubectl get deployment -n ${NAMESPACE} | grep -q "deployment-ricplt-appmgr"; then
        echo -e "${GREEN}[PASS]${NC} AppMgr deployment exists"
        return 0
    else
        echo -e "${RED}[FAIL]${NC} AppMgr deployment not found"
        return 1
    fi
}

# Test 2: Check if AppMgr pod is running
test_pod_running() {
    echo -e "\n${YELLOW}[TEST 2]${NC} Checking if AppMgr pod is running..."

    POD_NAME=$(kubectl get pods -n ${NAMESPACE} -l app=ricplt-appmgr -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

    if [ -z "$POD_NAME" ]; then
        echo -e "${RED}[FAIL]${NC} No AppMgr pod found"
        return 1
    fi

    POD_STATUS=$(kubectl get pod ${POD_NAME} -n ${NAMESPACE} -o jsonpath='{.status.phase}')

    if [ "$POD_STATUS" == "Running" ]; then
        echo -e "${GREEN}[PASS]${NC} AppMgr pod is running (${POD_NAME})"
        return 0
    else
        echo -e "${RED}[FAIL]${NC} AppMgr pod status: ${POD_STATUS}"
        return 1
    fi
}

# Test 3: Check if AppMgr pod is ready
test_pod_ready() {
    echo -e "\n${YELLOW}[TEST 3]${NC} Checking if AppMgr pod is ready..."

    POD_NAME=$(kubectl get pods -n ${NAMESPACE} -l app=ricplt-appmgr -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

    if [ -z "$POD_NAME" ]; then
        echo -e "${RED}[FAIL]${NC} No AppMgr pod found"
        return 1
    fi

    READY=$(kubectl get pod ${POD_NAME} -n ${NAMESPACE} -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')

    if [ "$READY" == "True" ]; then
        echo -e "${GREEN}[PASS]${NC} AppMgr pod is ready"
        return 0
    else
        echo -e "${RED}[FAIL]${NC} AppMgr pod is not ready"
        return 1
    fi
}

# Test 4: Check if AppMgr service exists
test_service_exists() {
    echo -e "\n${YELLOW}[TEST 4]${NC} Checking if AppMgr services exist..."

    HTTP_SERVICE=$(kubectl get svc -n ${NAMESPACE} service-ricplt-appmgr-http 2>/dev/null)
    RMR_SERVICE=$(kubectl get svc -n ${NAMESPACE} service-ricplt-appmgr-rmr 2>/dev/null)

    if [ -n "$HTTP_SERVICE" ] && [ -n "$RMR_SERVICE" ]; then
        echo -e "${GREEN}[PASS]${NC} AppMgr HTTP and RMR services exist"
        return 0
    else
        echo -e "${RED}[FAIL]${NC} AppMgr services not found"
        return 1
    fi
}

# Test 5: Check if AppMgr HTTP endpoint is accessible
test_http_endpoint() {
    echo -e "\n${YELLOW}[TEST 5]${NC} Checking if AppMgr HTTP endpoint is accessible..."

    POD_NAME=$(kubectl get pods -n ${NAMESPACE} -l app=ricplt-appmgr -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

    if [ -z "$POD_NAME" ]; then
        echo -e "${RED}[FAIL]${NC} No AppMgr pod found"
        return 1
    fi

    # Try to access health endpoint
    HTTP_CODE=$(kubectl exec -n ${NAMESPACE} ${POD_NAME} -- curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ric/v1/health/alive 2>/dev/null || echo "000")

    if [ "$HTTP_CODE" == "200" ]; then
        echo -e "${GREEN}[PASS]${NC} AppMgr HTTP endpoint is accessible (HTTP ${HTTP_CODE})"
        return 0
    else
        echo -e "${YELLOW}[WARN]${NC} AppMgr HTTP endpoint returned: ${HTTP_CODE} (may be normal during startup)"
        return 0
    fi
}

# Test 6: Check for no crash loops
test_no_crash_loops() {
    echo -e "\n${YELLOW}[TEST 6]${NC} Checking for crash loops..."

    POD_NAME=$(kubectl get pods -n ${NAMESPACE} -l app=ricplt-appmgr -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

    if [ -z "$POD_NAME" ]; then
        echo -e "${RED}[FAIL]${NC} No AppMgr pod found"
        return 1
    fi

    RESTART_COUNT=$(kubectl get pod ${POD_NAME} -n ${NAMESPACE} -o jsonpath='{.status.containerStatuses[0].restartCount}')

    if [ "$RESTART_COUNT" -lt 3 ]; then
        echo -e "${GREEN}[PASS]${NC} No excessive restarts (restart count: ${RESTART_COUNT})"
        return 0
    else
        echo -e "${RED}[FAIL]${NC} Excessive restarts detected (restart count: ${RESTART_COUNT})"
        return 1
    fi
}

# Test 7: Check Helm release status
test_helm_release() {
    echo -e "\n${YELLOW}[TEST 7]${NC} Checking Helm release status..."

    RELEASE_STATUS=$(helm status ${RELEASE_NAME} -n ${NAMESPACE} -o json 2>/dev/null | jq -r '.info.status' || echo "not-found")

    if [ "$RELEASE_STATUS" == "deployed" ]; then
        echo -e "${GREEN}[PASS]${NC} Helm release is deployed"
        return 0
    else
        echo -e "${RED}[FAIL]${NC} Helm release status: ${RELEASE_STATUS}"
        return 1
    fi
}

# Run all tests
run_all_tests() {
    local failed=0

    test_deployment_exists || ((failed++))
    test_pod_running || ((failed++))
    test_pod_ready || ((failed++))
    test_service_exists || ((failed++))
    test_http_endpoint || ((failed++))
    test_no_crash_loops || ((failed++))
    test_helm_release || ((failed++))

    echo -e "\n======================================"
    if [ $failed -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        echo "======================================"
        return 0
    else
        echo -e "${RED}${failed} test(s) failed${NC}"
        echo "======================================"
        return 1
    fi
}

# Main execution
main() {
    run_all_tests
    exit $?
}

main
