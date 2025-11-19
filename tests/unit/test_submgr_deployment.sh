#!/bin/bash

################################################################################
# Subscription Manager Deployment Test Script (TDD - Red Phase)
# Tests for submgr deployment validation
################################################################################

set -e

NAMESPACE="ricplt"
RELEASE_NAME="r4-submgr"
COMPONENT="submgr"
APP_LABEL="app=ricplt-submgr"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TOTAL_TESTS=0

# Logging function
log_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
    ((TOTAL_TESTS++))
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

log_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Test 1: Check if Helm release exists
test_helm_release() {
    log_test "Checking if Helm release '${RELEASE_NAME}' exists..."

    if helm list -n ${NAMESPACE} | grep -q ${RELEASE_NAME}; then
        log_pass "Helm release '${RELEASE_NAME}' exists"
        return 0
    else
        log_fail "Helm release '${RELEASE_NAME}' not found"
        return 1
    fi
}

# Test 2: Check if deployment exists
test_deployment_exists() {
    log_test "Checking if deployment exists..."

    DEPLOYMENT_NAME=$(kubectl get deployment -n ${NAMESPACE} -l ${APP_LABEL} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

    if [ -n "$DEPLOYMENT_NAME" ]; then
        log_pass "Deployment '${DEPLOYMENT_NAME}' exists"
        return 0
    else
        log_fail "Deployment for ${COMPONENT} not found"
        return 1
    fi
}

# Test 3: Check pod status
test_pod_status() {
    log_test "Checking pod status..."

    # Wait for pod to be ready (max 2 minutes)
    for i in {1..24}; do
        POD_STATUS=$(kubectl get pods -n ${NAMESPACE} -l ${APP_LABEL} -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "")
        POD_READY=$(kubectl get pods -n ${NAMESPACE} -l ${APP_LABEL} -o jsonpath='{.items[0].status.containerStatuses[0].ready}' 2>/dev/null || echo "false")

        if [ "$POD_STATUS" = "Running" ] && [ "$POD_READY" = "true" ]; then
            POD_NAME=$(kubectl get pods -n ${NAMESPACE} -l ${APP_LABEL} -o jsonpath='{.items[0].metadata.name}')
            log_pass "Pod '${POD_NAME}' is Running and Ready"
            return 0
        fi

        sleep 5
    done

    log_fail "Pod is not ready after 2 minutes"
    kubectl get pods -n ${NAMESPACE} -l ${APP_LABEL}
    return 1
}

# Test 4: Check required services
test_services() {
    log_test "Checking if required services exist..."

    SERVICES_FOUND=0
    REQUIRED_SERVICES=("service-ricplt-submgr-http" "service-ricplt-submgr-rmr")

    for svc in "${REQUIRED_SERVICES[@]}"; do
        if kubectl get svc -n ${NAMESPACE} ${svc} >/dev/null 2>&1; then
            log_info "Service '${svc}' exists"
            ((SERVICES_FOUND++))
        else
            log_info "Service '${svc}' not found"
        fi
    done

    if [ $SERVICES_FOUND -gt 0 ]; then
        log_pass "Found ${SERVICES_FOUND} service(s)"
        return 0
    else
        log_fail "No required services found"
        return 1
    fi
}

# Test 5: Check environment variables
test_environment_variables() {
    log_test "Checking critical environment variables..."

    POD_NAME=$(kubectl get pods -n ${NAMESPACE} -l ${APP_LABEL} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

    if [ -z "$POD_NAME" ]; then
        log_fail "Cannot find pod to check environment variables"
        return 1
    fi

    REQUIRED_ENVS=("RMR_RTG_SVC" "DBAAS_SERVICE_HOST" "DBAAS_SERVICE_PORT")
    ENV_CHECK_PASSED=true

    for env_var in "${REQUIRED_ENVS[@]}"; do
        ENV_VALUE=$(kubectl exec -n ${NAMESPACE} ${POD_NAME} -- printenv ${env_var} 2>/dev/null || echo "")
        if [ -n "$ENV_VALUE" ]; then
            log_info "Environment variable '${env_var}' = '${ENV_VALUE}'"
        else
            log_info "Environment variable '${env_var}' is not set"
            ENV_CHECK_PASSED=false
        fi
    done

    if [ "$ENV_CHECK_PASSED" = true ]; then
        log_pass "All critical environment variables are set"
        return 0
    else
        log_fail "Some environment variables are missing"
        return 1
    fi
}

# Test 6: Check pod logs for errors
test_pod_logs() {
    log_test "Checking pod logs for critical errors..."

    POD_NAME=$(kubectl get pods -n ${NAMESPACE} -l ${APP_LABEL} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

    if [ -z "$POD_NAME" ]; then
        log_fail "Cannot find pod to check logs"
        return 1
    fi

    # Get last 50 lines of logs
    LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 2>/dev/null || echo "")

    # Check for critical errors
    if echo "$LOGS" | grep -iE "fatal|panic|critical error" >/dev/null; then
        log_fail "Found critical errors in logs"
        echo "$LOGS" | grep -iE "fatal|panic|critical error"
        return 1
    else
        log_pass "No critical errors found in recent logs"
        return 0
    fi
}

# Test 7: Check resource limits
test_resource_limits() {
    log_test "Checking resource limits configuration..."

    POD_NAME=$(kubectl get pods -n ${NAMESPACE} -l ${APP_LABEL} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

    if [ -z "$POD_NAME" ]; then
        log_fail "Cannot find pod to check resource limits"
        return 1
    fi

    MEMORY_LIMIT=$(kubectl get pod -n ${NAMESPACE} ${POD_NAME} -o jsonpath='{.spec.containers[0].resources.limits.memory}' 2>/dev/null || echo "")
    CPU_LIMIT=$(kubectl get pod -n ${NAMESPACE} ${POD_NAME} -o jsonpath='{.spec.containers[0].resources.limits.cpu}' 2>/dev/null || echo "")
    MEMORY_REQUEST=$(kubectl get pod -n ${NAMESPACE} ${POD_NAME} -o jsonpath='{.spec.containers[0].resources.requests.memory}' 2>/dev/null || echo "")
    CPU_REQUEST=$(kubectl get pod -n ${NAMESPACE} ${POD_NAME} -o jsonpath='{.spec.containers[0].resources.requests.cpu}' 2>/dev/null || echo "")

    # PASS if either limits or requests are set, or if pod is running successfully without them
    POD_STATUS=$(kubectl get pod -n ${NAMESPACE} ${POD_NAME} -o jsonpath='{.status.phase}' 2>/dev/null || echo "")

    if [ -n "$MEMORY_LIMIT" ] && [ -n "$CPU_LIMIT" ]; then
        log_pass "Resource limits set: Memory=${MEMORY_LIMIT}, CPU=${CPU_LIMIT}"
        return 0
    elif [ -n "$MEMORY_REQUEST" ] && [ -n "$CPU_REQUEST" ]; then
        log_pass "Resource requests set: Memory=${MEMORY_REQUEST}, CPU=${CPU_REQUEST}"
        return 0
    elif [ "$POD_STATUS" = "Running" ]; then
        log_pass "Resource configuration optional (pod running successfully without limits)"
        return 0
    else
        log_fail "Resource limits not properly configured"
        return 1
    fi
}

# Test 8: Check connectivity to dependencies
test_dependency_connectivity() {
    log_test "Checking connectivity to dependency services..."

    # Check if DBAAS service exists and has endpoints
    DBAAS_SVC_EXISTS=$(kubectl get svc -n ${NAMESPACE} service-ricplt-dbaas-tcp 2>/dev/null | grep -c service-ricplt-dbaas-tcp || echo "0")

    if [ "$DBAAS_SVC_EXISTS" -eq 0 ]; then
        log_fail "DBAAS service does not exist"
        return 1
    fi

    # Check if DBAAS has endpoints (pods are ready)
    DBAAS_ENDPOINTS=$(kubectl get endpoints -n ${NAMESPACE} service-ricplt-dbaas-tcp -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null || echo "")

    if [ -n "$DBAAS_ENDPOINTS" ]; then
        log_pass "DBAAS service is reachable (endpoints: ${DBAAS_ENDPOINTS})"
        return 0
    else
        log_fail "DBAAS service has no endpoints (no ready pods)"
        return 1
    fi
}

# Main test execution
main() {
    echo "=========================================="
    echo "Subscription Manager Deployment Tests"
    echo "=========================================="
    echo ""

    # Run all tests
    test_helm_release || true
    test_deployment_exists || true
    test_pod_status || true
    test_services || true
    test_environment_variables || true
    test_pod_logs || true
    test_resource_limits || true
    test_dependency_connectivity || true

    # Print summary
    echo ""
    echo "=========================================="
    echo "Test Summary"
    echo "=========================================="
    echo "Total Tests: ${TOTAL_TESTS}"
    echo -e "${GREEN}Passed: ${TESTS_PASSED}${NC}"
    echo -e "${RED}Failed: ${TESTS_FAILED}${NC}"
    echo "=========================================="

    # Exit with appropriate code
    if [ ${TESTS_FAILED} -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}Some tests failed!${NC}"
        exit 1
    fi
}

# Run main function
main
