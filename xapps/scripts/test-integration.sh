#!/bin/bash
# Integration test script for O-RAN xApps
# Version: 1.0.0

set -e

# Configuration
NAMESPACE="${NAMESPACE:-ricxapp}"
TEST_TIMEOUT="${TEST_TIMEOUT:-300}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}O-RAN xApp Integration Test Suite${NC}"
echo "Namespace: $NAMESPACE"
echo "Test Timeout: ${TEST_TIMEOUT}s"
echo ""

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run test
run_test() {
    local test_name=$1
    local test_command=$2
    
    echo -n "Testing $test_name... "
    
    if eval $test_command > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Function to test pod status
test_pod_status() {
    echo -e "${YELLOW}Testing Pod Status...${NC}"
    
    for xapp in kpimon qoe-predictor ran-control federated-learning; do
        run_test "$xapp pod running" \
            "kubectl get pod -n ${NAMESPACE} -l app=${xapp} -o jsonpath='{.items[0].status.phase}' | grep -q Running"
    done
    echo ""
}

# Function to test service endpoints
test_service_endpoints() {
    echo -e "${YELLOW}Testing Service Endpoints...${NC}"
    
    for xapp in kpimon qoe-predictor ran-control federated-learning; do
        run_test "$xapp service exists" \
            "kubectl get service ${xapp}-service -n ${NAMESPACE}"
    done
    echo ""
}

# Function to test health endpoints
test_health_endpoints() {
    echo -e "${YELLOW}Testing Health Endpoints...${NC}"
    
    local ports=(8080 8090 8100 8110)
    local xapps=(kpimon qoe-predictor ran-control federated-learning)
    
    for i in ${!xapps[@]}; do
        local xapp=${xapps[$i]}
        local port=${ports[$i]}
        
        # Get pod name
        pod=$(kubectl get pod -n ${NAMESPACE} -l app=${xapp} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        
        if [ -n "$pod" ]; then
            # Test alive endpoint
            run_test "$xapp /health/alive" \
                "kubectl exec -n ${NAMESPACE} ${pod} -- curl -f http://localhost:${port}/health/alive"
            
            # Test ready endpoint
            run_test "$xapp /health/ready" \
                "kubectl exec -n ${NAMESPACE} ${pod} -- curl -f http://localhost:${port}/health/ready"
        else
            echo -e "${RED}✗ $xapp pod not found${NC}"
            ((TESTS_FAILED+=2))
        fi
    done
    echo ""
}

# Function to test RMR connectivity
test_rmr_connectivity() {
    echo -e "${YELLOW}Testing RMR Connectivity...${NC}"
    
    # Check if E2Term is reachable
    run_test "E2Term service reachable" \
        "kubectl get service -n ricplt service-ricplt-e2term-rmr"
    
    # Check if A1 Mediator is reachable
    run_test "A1 Mediator service reachable" \
        "kubectl get service -n ricplt service-ricplt-a1mediator-rmr"
    
    echo ""
}

# Function to test Redis connectivity
test_redis_connectivity() {
    echo -e "${YELLOW}Testing Redis Connectivity...${NC}"
    
    # Check if Redis service exists
    run_test "Redis service exists" \
        "kubectl get service -n ricplt redis-service"
    
    # Test Redis connection from xApps
    for xapp in kpimon qoe-predictor ran-control federated-learning; do
        pod=$(kubectl get pod -n ${NAMESPACE} -l app=${xapp} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        
        if [ -n "$pod" ]; then
            run_test "$xapp Redis connectivity" \
                "kubectl exec -n ${NAMESPACE} ${pod} -- python3 -c 'import redis; r=redis.Redis(host=\"redis-service.ricplt\", port=6379); r.ping()'"
        fi
    done
    echo ""
}

# Function to test ConfigMaps
test_configmaps() {
    echo -e "${YELLOW}Testing ConfigMaps...${NC}"
    
    for xapp in kpimon qoe-predictor ran-control federated-learning; do
        run_test "$xapp ConfigMap exists" \
            "kubectl get configmap ${xapp}-config -n ${NAMESPACE}"
        
        # Check if config is mounted in pod
        pod=$(kubectl get pod -n ${NAMESPACE} -l app=${xapp} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        
        if [ -n "$pod" ]; then
            run_test "$xapp config mounted" \
                "kubectl exec -n ${NAMESPACE} ${pod} -- test -f /app/config/config.json"
        fi
    done
    echo ""
}

# Function to test resource limits
test_resource_limits() {
    echo -e "${YELLOW}Testing Resource Limits...${NC}"
    
    for xapp in kpimon qoe-predictor ran-control federated-learning; do
        run_test "$xapp resource limits set" \
            "kubectl get deployment ${xapp} -n ${NAMESPACE} -o jsonpath='{.spec.template.spec.containers[0].resources.limits}' | grep -q memory"
    done
    echo ""
}

# Function to test logs
test_logs() {
    echo -e "${YELLOW}Testing Log Output...${NC}"
    
    for xapp in kpimon qoe-predictor ran-control federated-learning; do
        pod=$(kubectl get pod -n ${NAMESPACE} -l app=${xapp} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        
        if [ -n "$pod" ]; then
            run_test "$xapp producing logs" \
                "kubectl logs -n ${NAMESPACE} ${pod} --tail=10 | grep -E '(INFO|DEBUG|WARNING|ERROR)'"
        fi
    done
    echo ""
}

# Function to test E2 subscription
test_e2_subscription() {
    echo -e "${YELLOW}Testing E2 Subscription Capability...${NC}"
    
    # Check if KPIMON can create subscriptions
    pod=$(kubectl get pod -n ${NAMESPACE} -l app=kpimon -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [ -n "$pod" ]; then
        run_test "KPIMON E2 subscription capability" \
            "kubectl exec -n ${NAMESPACE} ${pod} -- python3 -c 'from ricxappframe.xapp_frame import RmrXapp; print(\"E2 ready\")'"
    fi
    echo ""
}

# Function to test API endpoints
test_api_endpoints() {
    echo -e "${YELLOW}Testing REST API Endpoints...${NC}"
    
    local endpoints=(
        "kpimon:8080:/metrics"
        "qoe-predictor:8090:/metrics"
        "ran-control:8100:/metrics"
        "federated-learning:8110:/fl/status"
    )
    
    for endpoint in "${endpoints[@]}"; do
        IFS=':' read -r xapp port path <<< "$endpoint"
        pod=$(kubectl get pod -n ${NAMESPACE} -l app=${xapp} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        
        if [ -n "$pod" ]; then
            run_test "$xapp API $path" \
                "kubectl exec -n ${NAMESPACE} ${pod} -- curl -f http://localhost:${port}${path}"
        fi
    done
    echo ""
}

# Function to run stress test
run_stress_test() {
    echo -e "${YELLOW}Running Stress Test...${NC}"
    
    # Generate load on KPIMON
    pod=$(kubectl get pod -n ${NAMESPACE} -l app=kpimon -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [ -n "$pod" ]; then
        echo "Generating test load on KPIMON..."
        kubectl exec -n ${NAMESPACE} ${pod} -- bash -c "
            for i in {1..100}; do
                curl -s http://localhost:8080/metrics > /dev/null 2>&1 &
            done
            wait
        " &
        
        sleep 5
        
        run_test "KPIMON handles concurrent requests" \
            "kubectl exec -n ${NAMESPACE} ${pod} -- curl -f http://localhost:8080/health/alive"
    fi
    echo ""
}

# Function to generate test report
generate_report() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Test Report${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
    
    total_tests=$((TESTS_PASSED + TESTS_FAILED))
    
    echo "Total Tests: $total_tests"
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "\n${GREEN}All tests passed successfully!${NC}"
        exit 0
    else
        echo -e "\n${RED}Some tests failed. Please check the deployment.${NC}"
        exit 1
    fi
}

# Main function
main() {
    echo "Starting Integration Tests..."
    echo "============================="
    echo ""
    
    # Check if xApps are deployed
    kubectl get deployment -n ${NAMESPACE} -l 'app in (kpimon,qoe-predictor,ran-control,federated-learning)' > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo -e "${RED}xApps are not deployed. Run deploy-all.sh first.${NC}"
        exit 1
    fi
    
    # Run test suites
    test_pod_status
    test_service_endpoints
    test_configmaps
    test_resource_limits
    test_health_endpoints
    test_rmr_connectivity
    test_redis_connectivity
    test_logs
    test_e2_subscription
    test_api_endpoints
    
    # Optional: Run stress test
    if [ "${RUN_STRESS_TEST}" == "true" ]; then
        run_stress_test
    fi
    
    # Generate report
    generate_report
}

# Run main function
main
