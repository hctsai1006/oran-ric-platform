#!/bin/bash
################################################################################
# Resource Status Manager (RSM) Deployment Unit Test
# O-RAN SC J-Release
#
# This script verifies the RSM deployment is functioning correctly
################################################################################

NAMESPACE="ricplt"
RELEASE_NAME="r4-rsm"
POD_LABEL="app=ricplt-rsm"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Test function
run_test() {
    local test_name=$1
    local test_command=$2

    echo -e "${YELLOW}Running test: ${test_name}${NC}"

    if eval "$test_command"; then
        echo -e "${GREEN}[PASS] ${test_name}${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}[FAIL] ${test_name}${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

echo "========================================"
echo "RSM Deployment Unit Tests"
echo "========================================"
echo ""

# Test 1: Check if Helm release exists
run_test "Helm release exists" \
    "helm list -n ${NAMESPACE} | grep -q ${RELEASE_NAME}"

# Test 2: Check if RSM pod is running
run_test "RSM pod is running" \
    "kubectl get pods -n ${NAMESPACE} -l ${POD_LABEL} --no-headers | grep -q 'Running'"

# Test 3: Check if RSM pod is ready (1/1)
run_test "RSM pod is ready" \
    "kubectl get pods -n ${NAMESPACE} -l ${POD_LABEL} --no-headers | awk '{print \$2}' | grep -q '1/1'"

# Test 4: Check if RSM HTTP service exists
run_test "RSM HTTP service exists" \
    "kubectl get svc -n ${NAMESPACE} service-ricplt-rsm-http --no-headers | grep -q 'ClusterIP'"

# Test 5: Check if RSM RMR service exists
run_test "RSM RMR service exists" \
    "kubectl get svc -n ${NAMESPACE} service-ricplt-rsm-rmr --no-headers | grep -q 'ClusterIP'"

# Test 6: Check if RSM deployment has desired replicas
run_test "RSM deployment has correct replicas" \
    "kubectl get deployment -n ${NAMESPACE} deployment-ricplt-rsm --no-headers | awk '{print \$2}' | grep -q '1/1'"

# Test 7: Check if RSM configmap exists
run_test "RSM configmap exists" \
    "kubectl get configmap -n ${NAMESPACE} configmap-ricplt-rsm --no-headers | grep -q 'configmap-ricplt-rsm'"

# Test 8: Verify RSM configmap contains resourceStatusParams
run_test "RSM configmap contains resourceStatusParams" \
    "kubectl get configmap -n ${NAMESPACE} configmap-ricplt-rsm -o yaml | grep -q 'resourceStatusParams'"

# Test 9: Check if RSM pod has no restart count
run_test "RSM pod has no recent restarts" \
    "[ \$(kubectl get pods -n ${NAMESPACE} -l ${POD_LABEL} --no-headers | awk '{print \$4}') -eq 0 ]"

# Test 10: Check RSM logs for successful initialization
run_test "RSM initialized successfully" \
    "kubectl logs -n ${NAMESPACE} -l ${POD_LABEL} --tail=50 | grep -q 'RMR router has been initiated'"

# Test 11: Verify RSM HTTP port is 4800
run_test "RSM HTTP port is 4800" \
    "kubectl get svc -n ${NAMESPACE} service-ricplt-rsm-http -o jsonpath='{.spec.ports[0].port}' | grep -q '4800'"

# Test 12: Verify RSM RMR data port is 4801
run_test "RSM RMR data port is 4801" \
    "kubectl get svc -n ${NAMESPACE} service-ricplt-rsm-rmr -o jsonpath='{.spec.ports[?(@.name==\"rmrdata\")].port}' | grep -q '4801'"

# Test 13: Verify RSM image version
run_test "RSM uses correct image version" \
    "kubectl get deployment -n ${NAMESPACE} deployment-ricplt-rsm -o jsonpath='{.spec.template.spec.containers[0].image}' | grep -q 'ric-plt-resource-status-manager:3.0.1'"

# Test 14: Verify RSM pod has proper labels
run_test "RSM pod has correct labels" \
    "kubectl get pods -n ${NAMESPACE} -l ${POD_LABEL} --no-headers | wc -l | grep -q '1'"

# Test 15: Check if RSM configuration file exists
run_test "RSM configuration file exists" \
    "[ -f /home/mbwcl711_3060/thc1006/tmep/oran-ric-platform/config/ric-platform/rsm-values.yaml ]"

echo ""
echo "========================================"
echo "Test Summary"
echo "========================================"
echo -e "${GREEN}Tests Passed: ${TESTS_PASSED}${NC}"
echo -e "${RED}Tests Failed: ${TESTS_FAILED}${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed successfully!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please check the RSM deployment.${NC}"
    exit 1
fi
