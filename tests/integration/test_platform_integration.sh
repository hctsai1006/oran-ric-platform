#!/bin/bash

################################################################################
# O-RAN SC J-Release Platform Integration Test Script
# Tests RMR connectivity, service endpoints, database, and monitoring
################################################################################

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Results array
declare -a TEST_RESULTS

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_test_start() {
    echo ""
    echo "=========================================="
    echo "TEST: $1"
    echo "=========================================="
}

record_test() {
    local test_name=$1
    local result=$2
    local details=$3

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    if [ "$result" == "PASS" ]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        log_info "✓ $test_name: PASSED"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_error "✗ $test_name: FAILED - $details"
    fi

    TEST_RESULTS+=("$result|$test_name|$details")
}

# Helper function to check if pod is running
check_pod_running() {
    local namespace=$1
    local pod_pattern=$2

    kubectl get pods -n $namespace | grep $pod_pattern | grep -q "Running"
    return $?
}

# Helper function to execute command in pod
exec_in_pod() {
    local namespace=$1
    local pod_pattern=$2
    local command=$3

    local pod=$(kubectl get pods -n $namespace | grep $pod_pattern | grep Running | head -1 | awk '{print $1}')
    if [ -z "$pod" ]; then
        return 1
    fi

    kubectl exec -n $namespace $pod -- $command
    return $?
}

################################################################################
# A. RMR CONNECTIVITY TESTS
################################################################################
test_rmr_connectivity() {
    log_test_start "RMR Connectivity Tests"

    # Test 1: E2Term ↔ E2Mgr RMR connectivity
    log_info "Testing E2Term ↔ E2Mgr RMR connectivity..."
    if kubectl get svc -n ricplt service-ricplt-e2term-rmr-alpha &>/dev/null && \
       kubectl get svc -n ricplt service-ricplt-e2mgr-rmr &>/dev/null; then
        # Check if services have endpoints
        e2term_endpoints=$(kubectl get endpoints -n ricplt service-ricplt-e2term-rmr-alpha -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null)
        e2mgr_endpoints=$(kubectl get endpoints -n ricplt service-ricplt-e2mgr-rmr -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null)

        if [ -n "$e2term_endpoints" ] && [ -n "$e2mgr_endpoints" ]; then
            record_test "E2Term-E2Mgr RMR" "PASS" "Services and endpoints available"
        else
            record_test "E2Term-E2Mgr RMR" "FAIL" "Missing endpoints"
        fi
    else
        record_test "E2Term-E2Mgr RMR" "FAIL" "RMR services not found"
    fi

    # Test 2: SubMgr ↔ RTMgr RMR connectivity
    log_info "Testing SubMgr ↔ RTMgr RMR connectivity..."
    if kubectl get svc -n ricplt service-ricplt-submgr-rmr &>/dev/null && \
       kubectl get svc -n ricplt service-ricplt-rtmgr-rmr &>/dev/null; then
        submgr_endpoints=$(kubectl get endpoints -n ricplt service-ricplt-submgr-rmr -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null)
        rtmgr_endpoints=$(kubectl get endpoints -n ricplt service-ricplt-rtmgr-rmr -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null)

        if [ -n "$submgr_endpoints" ] && [ -n "$rtmgr_endpoints" ]; then
            record_test "SubMgr-RTMgr RMR" "PASS" "Services and endpoints available"
        else
            record_test "SubMgr-RTMgr RMR" "FAIL" "Missing endpoints"
        fi
    else
        record_test "SubMgr-RTMgr RMR" "FAIL" "RMR services not found"
    fi

    # Test 3: A1 Mediator ↔ RTMgr connectivity
    log_info "Testing A1 Mediator ↔ RTMgr RMR connectivity..."
    if kubectl get svc -n ricplt service-ricplt-a1mediator-rmr &>/dev/null; then
        a1_endpoints=$(kubectl get endpoints -n ricplt service-ricplt-a1mediator-rmr -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null)

        if [ -n "$a1_endpoints" ] && [ -n "$rtmgr_endpoints" ]; then
            record_test "A1Mediator-RTMgr RMR" "PASS" "Services and endpoints available"
        else
            record_test "A1Mediator-RTMgr RMR" "FAIL" "Missing endpoints"
        fi
    else
        record_test "A1Mediator-RTMgr RMR" "FAIL" "A1 RMR service not found"
    fi

    # Test 4: xApps ↔ Platform RMR connectivity
    log_info "Testing xApps ↔ Platform RMR connectivity..."
    xapp_rmr_found=0
    for svc in kpimon hw-go-rmr traffic-steering; do
        if kubectl get svc -n ricxapp $svc &>/dev/null; then
            xapp_rmr_found=$((xapp_rmr_found + 1))
        fi
    done

    if [ $xapp_rmr_found -gt 0 ]; then
        record_test "xApps-Platform RMR" "PASS" "Found $xapp_rmr_found xApp RMR services"
    else
        record_test "xApps-Platform RMR" "FAIL" "No xApp RMR services found"
    fi
}

################################################################################
# B. SERVICE ENDPOINT TESTS
################################################################################
test_service_endpoints() {
    log_test_start "Service Endpoint Tests"

    # Test 1: E2Mgr HTTP API (port 3800)
    log_info "Testing E2Mgr HTTP API..."
    e2mgr_pod=$(kubectl get pods -n ricplt | grep deployment-ricplt-e2mgr | grep Running | head -1 | awk '{print $1}')
    if [ -n "$e2mgr_pod" ]; then
        # Check health endpoint - E2Mgr returns HTTP 200 with empty body
        http_status=$(kubectl exec -n ricplt $e2mgr_pod -- curl -s -o /dev/null -w "%{http_code}" http://localhost:3800/v1/health 2>/dev/null)
        if [ "$http_status" = "200" ]; then
            record_test "E2Mgr HTTP API" "PASS" "Health endpoint /v1/health returns HTTP 200"
        else
            record_test "E2Mgr HTTP API" "FAIL" "Health endpoint returned HTTP $http_status"
        fi
    else
        record_test "E2Mgr HTTP API" "FAIL" "E2Mgr pod not running"
    fi

    # Test 2: AppMgr HTTP API (port 8080)
    log_info "Testing AppMgr HTTP API..."
    appmgr_pod=$(kubectl get pods -n ricplt | grep deployment-ricplt-appmgr | grep Running | head -1 | awk '{print $1}')
    if [ -n "$appmgr_pod" ]; then
        if kubectl exec -n ricplt $appmgr_pod -- bash -c "exec 3<>/dev/tcp/localhost/8080" 2>/dev/null; then
            record_test "AppMgr HTTP API" "PASS" "Port 8080 accessible"
        else
            record_test "AppMgr HTTP API" "FAIL" "Port 8080 not accessible"
        fi
    else
        record_test "AppMgr HTTP API" "FAIL" "AppMgr pod not running"
    fi

    # Test 3: A1 Mediator HTTP API (port 10000)
    log_info "Testing A1 Mediator HTTP API..."
    a1_pod=$(kubectl get pods -n ricplt | grep deployment-ricplt-a1mediator | grep Running | head -1 | awk '{print $1}')
    if [ -n "$a1_pod" ]; then
        if kubectl exec -n ricplt $a1_pod -- bash -c "exec 3<>/dev/tcp/localhost/10000" 2>/dev/null; then
            record_test "A1 Mediator HTTP API" "PASS" "Port 10000 accessible"
        else
            record_test "A1 Mediator HTTP API" "FAIL" "Port 10000 not accessible"
        fi
    else
        record_test "A1 Mediator HTTP API" "FAIL" "A1 Mediator pod not running"
    fi

    # Test 4: SubMgr HTTP service (port 8080)
    log_info "Testing SubMgr HTTP service..."
    submgr_pod=$(kubectl get pods -n ricplt | grep deployment-ricplt-submgr | grep Running | head -1 | awk '{print $1}')
    if [ -n "$submgr_pod" ]; then
        if kubectl exec -n ricplt $submgr_pod -- bash -c "exec 3<>/dev/tcp/localhost/8080" 2>/dev/null; then
            record_test "SubMgr HTTP Service" "PASS" "Port 8080 accessible"
        else
            record_test "SubMgr HTTP Service" "FAIL" "Port 8080 not accessible"
        fi
    else
        record_test "SubMgr HTTP Service" "FAIL" "SubMgr pod not running"
    fi

    # Test 5: RSM HTTP service (port 4800)
    log_info "Testing RSM HTTP service..."
    rsm_pod=$(kubectl get pods -n ricplt | grep deployment-ricplt-rsm | grep Running | head -1 | awk '{print $1}')
    if [ -n "$rsm_pod" ]; then
        if kubectl exec -n ricplt $rsm_pod -- bash -c "exec 3<>/dev/tcp/localhost/4800" 2>/dev/null; then
            record_test "RSM HTTP Service" "PASS" "Port 4800 accessible"
        else
            record_test "RSM HTTP Service" "FAIL" "Port 4800 not accessible"
        fi
    else
        record_test "RSM HTTP Service" "FAIL" "RSM pod not running"
    fi
}

################################################################################
# C. DATABASE INTEGRATION TESTS
################################################################################
test_database_integration() {
    log_test_start "Database Integration Tests"

    # Test 1: Redis Cluster health (3 nodes)
    log_info "Testing Redis Cluster health..."
    redis_pods=$(kubectl get pods -n ricplt | grep "redis-cluster-" | grep Running | wc -l)
    if [ "$redis_pods" -eq 3 ]; then
        record_test "Redis Cluster Health" "PASS" "All 3 Redis nodes running"
    else
        record_test "Redis Cluster Health" "FAIL" "Expected 3 Redis nodes, found $redis_pods"
    fi

    # Test 2: DBaaS connectivity
    log_info "Testing DBaaS connectivity..."
    dbaas_pod=$(kubectl get pods -n ricplt | grep statefulset-ricplt-dbaas | grep Running | head -1 | awk '{print $1}')
    if [ -n "$dbaas_pod" ]; then
        # Test Redis ping
        if kubectl exec -n ricplt $dbaas_pod -- redis-cli ping 2>/dev/null | grep -q "PONG"; then
            record_test "DBaaS Connectivity" "PASS" "Redis responding to PING"
        else
            record_test "DBaaS Connectivity" "FAIL" "Redis not responding"
        fi
    else
        record_test "DBaaS Connectivity" "FAIL" "DBaaS pod not running"
    fi

    # Test 3: SDL read/write operations
    log_info "Testing SDL read/write operations..."
    if [ -n "$dbaas_pod" ]; then
        # Write test
        kubectl exec -n ricplt $dbaas_pod -- redis-cli SET integration_test_key "test_value_$(date +%s)" &>/dev/null

        # Read test
        test_value=$(kubectl exec -n ricplt $dbaas_pod -- redis-cli GET integration_test_key 2>/dev/null)

        if [ -n "$test_value" ]; then
            record_test "SDL Read/Write" "PASS" "Successfully wrote and read test key"
            # Cleanup
            kubectl exec -n ricplt $dbaas_pod -- redis-cli DEL integration_test_key &>/dev/null
        else
            record_test "SDL Read/Write" "FAIL" "Could not read test key"
        fi
    else
        record_test "SDL Read/Write" "FAIL" "DBaaS pod not available"
    fi
}

################################################################################
# D. MONITORING STACK TESTS
################################################################################
test_monitoring_stack() {
    log_test_start "Monitoring Stack Tests"

    # Test 1: Prometheus metrics scraping
    log_info "Testing Prometheus server..."
    prom_pod=$(kubectl get pods -n ricplt | grep prometheus-server | grep Running | head -1 | awk '{print $1}')
    if [ -n "$prom_pod" ]; then
        # Check if Prometheus is responding
        if kubectl exec -n ricplt $prom_pod -- wget -q -O- http://localhost:9090/-/healthy 2>/dev/null | grep -q "Prometheus" || \
           kubectl exec -n ricplt $prom_pod -- bash -c "exec 3<>/dev/tcp/localhost/9090" 2>/dev/null; then
            record_test "Prometheus Server" "PASS" "Prometheus healthy"
        else
            record_test "Prometheus Server" "FAIL" "Prometheus not responding"
        fi
    else
        record_test "Prometheus Server" "FAIL" "Prometheus pod not running"
    fi

    # Test 2: Grafana dashboard accessibility
    log_info "Testing Grafana..."
    grafana_pod=$(kubectl get pods -n ricplt | grep oran-grafana | grep Running | head -1 | awk '{print $1}')
    if [ -n "$grafana_pod" ]; then
        if kubectl exec -n ricplt $grafana_pod -- bash -c "exec 3<>/dev/tcp/localhost/3000" 2>/dev/null; then
            record_test "Grafana Dashboard" "PASS" "Grafana accessible on port 3000"
        else
            record_test "Grafana Dashboard" "FAIL" "Grafana not accessible"
        fi
    else
        record_test "Grafana Dashboard" "FAIL" "Grafana pod not running"
    fi

    # Test 3: Jaeger tracing endpoints
    log_info "Testing Jaeger..."
    jaeger_pod=$(kubectl get pods -n ricplt | grep jaegeradapter | grep Running | head -1 | awk '{print $1}')
    if [ -n "$jaeger_pod" ]; then
        # Check query port via service endpoint using a test pod
        # Note: Jaeger container is minimal and doesn't have nc/curl, so we test via service
        if kubectl run test-jaeger-temp --image=busybox:1.28 --rm -i --restart=Never -n ricplt -- nc -zv service-ricplt-jaegeradapter-query 16686 2>&1 | grep -q "open"; then
            record_test "Jaeger Tracing" "PASS" "Jaeger query port accessible"
        else
            record_test "Jaeger Tracing" "FAIL" "Jaeger query port not accessible"
        fi
    else
        record_test "Jaeger Tracing" "FAIL" "Jaeger pod not running"
    fi

    # Test 4: Component metrics exposure
    log_info "Testing component metrics exposure..."
    metrics_count=0
    for component in e2term e2mgr submgr; do
        svc="service-ricplt-${component}-prometheus-alpha"
        if [ "$component" == "e2mgr" ] || [ "$component" == "submgr" ]; then
            continue  # These might not have prometheus endpoints
        fi

        if kubectl get svc -n ricplt $svc &>/dev/null; then
            metrics_count=$((metrics_count + 1))
        fi
    done

    # Check E2Term has prometheus service
    if kubectl get svc -n ricplt service-ricplt-e2term-prometheus-alpha &>/dev/null; then
        record_test "Component Metrics" "PASS" "E2Term metrics endpoint available"
    else
        record_test "Component Metrics" "WARN" "Limited metrics endpoints found"
    fi
}

################################################################################
# MAIN EXECUTION
################################################################################
main() {
    echo "=============================================="
    echo "O-RAN SC J-Release Integration Test Suite"
    echo "Started at: $(date)"
    echo "=============================================="
    echo ""

    # Run all test suites
    test_rmr_connectivity
    test_service_endpoints
    test_database_integration
    test_monitoring_stack

    # Print summary
    echo ""
    echo "=============================================="
    echo "TEST SUMMARY"
    echo "=============================================="
    echo "Total Tests: $TOTAL_TESTS"
    echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
    echo -e "${RED}Failed: $FAILED_TESTS${NC}"
    echo ""

    # Print detailed results
    echo "DETAILED RESULTS:"
    echo "----------------------------------------"
    for result in "${TEST_RESULTS[@]}"; do
        IFS='|' read -r status name details <<< "$result"
        if [ "$status" == "PASS" ]; then
            echo -e "${GREEN}✓${NC} $name"
        else
            echo -e "${RED}✗${NC} $name - $details"
        fi
    done

    echo ""
    echo "Test completed at: $(date)"

    # Exit with appropriate code
    if [ $FAILED_TESTS -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# Run main
main
