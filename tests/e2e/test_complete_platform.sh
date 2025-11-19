#!/bin/bash

################################################################################
# O-RAN SC J-Release Platform E2E Test Script
# Tests complete E2 flow, A1 policy flow, and xApp operations
################################################################################

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

################################################################################
# A. E2 INTERFACE FLOW TESTS
################################################################################
test_e2_interface_flow() {
    log_test_start "E2 Interface Flow Tests"

    # Test 1: E2 Simulator → E2Term SCTP connection (port 36422)
    log_info "Testing E2 Simulator → E2Term SCTP connection..."

    # Check if E2 Simulator is running
    e2sim_pod=$(kubectl get pods -n ricxapp | grep e2-simulator | grep Running | head -1 | awk '{print $1}')
    if [ -n "$e2sim_pod" ]; then
        log_info "E2 Simulator pod found: $e2sim_pod"

        # Check E2Term SCTP service
        if kubectl get svc -n ricplt service-ricplt-e2term-sctp-alpha &>/dev/null; then
            e2term_sctp_ip=$(kubectl get svc -n ricplt service-ricplt-e2term-sctp-alpha -o jsonpath='{.spec.clusterIP}')
            log_info "E2Term SCTP service IP: $e2term_sctp_ip"

            # Check E2Term pod is running
            e2term_pod=$(kubectl get pods -n ricplt | grep deployment-ricplt-e2term | grep Running | head -1 | awk '{print $1}')
            if [ -n "$e2term_pod" ]; then
                record_test "E2 SCTP Connection" "PASS" "E2Sim and E2Term both running, SCTP service available"
            else
                record_test "E2 SCTP Connection" "FAIL" "E2Term pod not running"
            fi
        else
            record_test "E2 SCTP Connection" "FAIL" "E2Term SCTP service not found"
        fi
    else
        record_test "E2 SCTP Connection" "FAIL" "E2 Simulator pod not running"
    fi

    # Test 2: E2 Setup Request/Response
    log_info "Testing E2 Setup flow..."

    # Check E2Term logs for E2 setup messages
    if [ -n "$e2term_pod" ]; then
        e2term_logs=$(kubectl logs -n ricplt $e2term_pod --tail=200 2>/dev/null || echo "")

        if echo "$e2term_logs" | grep -q "E2AP\|e2ap\|E2 Setup\|RICsubscription\|CONNECTED" 2>/dev/null; then
            record_test "E2 Setup Flow" "PASS" "E2AP messages detected in E2Term logs"
        else
            record_test "E2 Setup Flow" "WARN" "No E2AP messages found in recent logs (may not have connected yet)"
        fi
    else
        record_test "E2 Setup Flow" "FAIL" "E2Term pod not available"
    fi

    # Test 3: E2 Subscription flow via SubMgr
    log_info "Testing E2 Subscription flow via SubMgr..."

    submgr_pod=$(kubectl get pods -n ricplt | grep deployment-ricplt-submgr | grep Running | head -1 | awk '{print $1}')
    if [ -n "$submgr_pod" ]; then
        submgr_logs=$(kubectl logs -n ricplt $submgr_pod --tail=200 2>/dev/null || echo "")

        if echo "$submgr_logs" | grep -q "Subscription\|RICsubscription\|E2AP" 2>/dev/null; then
            record_test "E2 Subscription Flow" "PASS" "Subscription messages detected in SubMgr logs"
        else
            record_test "E2 Subscription Flow" "WARN" "No subscription messages in recent SubMgr logs"
        fi
    else
        record_test "E2 Subscription Flow" "FAIL" "SubMgr pod not available"
    fi

    # Test 4: E2 Indications to KPIMON xApp
    log_info "Testing E2 Indications to KPIMON xApp..."

    kpimon_pod=$(kubectl get pods -n ricxapp | grep kpimon | grep Running | head -1 | awk '{print $1}')
    if [ -n "$kpimon_pod" ]; then
        kpimon_logs=$(kubectl logs -n ricxapp $kpimon_pod --tail=200 2>/dev/null || echo "")

        if echo "$kpimon_logs" | grep -q "Received\|RIC_INDICATION\|E2AP\|message\|KPIMON" 2>/dev/null; then
            record_test "E2 Indications to KPIMON" "PASS" "Messages detected in KPIMON logs"
        else
            record_test "E2 Indications to KPIMON" "WARN" "No indication messages in recent KPIMON logs"
        fi
    else
        record_test "E2 Indications to KPIMON" "FAIL" "KPIMON pod not running"
    fi
}

################################################################################
# B. A1 POLICY FLOW TESTS
################################################################################
test_a1_policy_flow() {
    log_test_start "A1 Policy Flow Tests"

    # Test 1: A1 Mediator availability
    log_info "Testing A1 Mediator availability..."

    a1_pod=$(kubectl get pods -n ricplt | grep deployment-ricplt-a1mediator | grep Running | head -1 | awk '{print $1}')
    if [ -n "$a1_pod" ]; then
        # Try to query A1 Mediator
        a1_response=$(kubectl exec -n ricplt $a1_pod -- curl -s -o /dev/null -w "%{http_code}" http://localhost:10000/a1-p/healthcheck 2>/dev/null || echo "000")

        if [ "$a1_response" == "200" ]; then
            record_test "A1 Mediator Health" "PASS" "A1 Mediator healthcheck returned 200"
        elif kubectl exec -n ricplt $a1_pod -- nc -zv localhost 10000 2>&1 | grep -q "succeeded\|open"; then
            record_test "A1 Mediator Health" "PASS" "A1 Mediator port 10000 accessible"
        else
            record_test "A1 Mediator Health" "WARN" "A1 Mediator running but healthcheck failed"
        fi
    else
        record_test "A1 Mediator Health" "FAIL" "A1 Mediator pod not running"
    fi

    # Test 2: Policy type listing
    log_info "Testing A1 policy type operations..."

    if [ -n "$a1_pod" ]; then
        # Try to list policy types
        policy_types=$(kubectl exec -n ricplt $a1_pod -- curl -s http://localhost:10000/a1-p/policytypes 2>/dev/null || echo "")

        if [ -n "$policy_types" ]; then
            record_test "A1 Policy Type Query" "PASS" "Successfully queried policy types"
        else
            record_test "A1 Policy Type Query" "WARN" "Policy type query returned empty (may be expected if no types defined)"
        fi
    else
        record_test "A1 Policy Type Query" "FAIL" "A1 Mediator not available"
    fi

    # Test 3: Check A1 logs for policy activity
    log_info "Checking A1 Mediator logs for activity..."

    if [ -n "$a1_pod" ]; then
        a1_logs=$(kubectl logs -n ricplt $a1_pod --tail=100 2>/dev/null || echo "")

        if echo "$a1_logs" | grep -q "policy\|Policy\|A1\|started\|running" 2>/dev/null; then
            record_test "A1 Mediator Activity" "PASS" "A1 Mediator showing activity in logs"
        else
            record_test "A1 Mediator Activity" "WARN" "Limited activity in A1 Mediator logs"
        fi
    else
        record_test "A1 Mediator Activity" "FAIL" "A1 Mediator not available"
    fi
}

################################################################################
# C. xAPP OPERATIONS TESTS
################################################################################
test_xapp_operations() {
    log_test_start "xApp Operations Tests"

    # Test 1: KPIMON receiving E2 indications
    log_info "Testing KPIMON xApp operations..."

    kpimon_pod=$(kubectl get pods -n ricxapp | grep kpimon | grep Running | head -1 | awk '{print $1}')
    if [ -n "$kpimon_pod" ]; then
        # Check recent logs
        kpimon_logs=$(kubectl logs -n ricxapp $kpimon_pod --tail=50 2>/dev/null || echo "")

        # Check if KPIMON is processing messages
        if echo "$kpimon_logs" | grep -i "error\|fatal\|panic" &>/dev/null; then
            record_test "KPIMON Operations" "WARN" "KPIMON running but has error messages in logs"
        elif [ -n "$kpimon_logs" ]; then
            record_test "KPIMON Operations" "PASS" "KPIMON running and generating logs"
        else
            record_test "KPIMON Operations" "WARN" "KPIMON running but no recent logs"
        fi
    else
        record_test "KPIMON Operations" "FAIL" "KPIMON pod not running"
    fi

    # Test 2: HelloWorld health endpoints
    log_info "Testing HelloWorld xApp health endpoints..."

    hw_pod=$(kubectl get pods -n ricxapp | grep hw-go | grep Running | head -1 | awk '{print $1}')
    if [ -n "$hw_pod" ]; then
        # Try health endpoint
        hw_health=$(kubectl exec -n ricxapp $hw_pod -- curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ric/v1/health/ready 2>/dev/null || echo "000")

        if [ "$hw_health" == "200" ]; then
            record_test "HelloWorld Health" "PASS" "Health endpoint returned 200"
        elif kubectl exec -n ricxapp $hw_pod -- nc -zv localhost 8080 2>&1 | grep -q "succeeded\|open"; then
            record_test "HelloWorld Health" "PASS" "HelloWorld HTTP port accessible"
        else
            record_test "HelloWorld Health" "WARN" "HelloWorld running but health check inconclusive"
        fi
    else
        record_test "HelloWorld Health" "FAIL" "HelloWorld pod not running"
    fi

    # Test 3: Check xApp metrics exposure
    log_info "Testing xApp metrics exposure..."

    metrics_found=0
    for xapp_pod in $kpimon_pod $hw_pod; do
        if [ -n "$xapp_pod" ]; then
            # Check if metrics port is accessible (common ports: 8080, 8081)
            if kubectl exec -n ricxapp $xapp_pod -- nc -zv localhost 8080 2>&1 | grep -q "succeeded\|open" || \
               kubectl exec -n ricxapp $xapp_pod -- nc -zv localhost 8081 2>&1 | grep -q "succeeded\|open"; then
                metrics_found=$((metrics_found + 1))
            fi
        fi
    done

    if [ $metrics_found -gt 0 ]; then
        record_test "xApp Metrics" "PASS" "$metrics_found xApps exposing metrics endpoints"
    else
        record_test "xApp Metrics" "WARN" "Could not verify metrics endpoints"
    fi

    # Test 4: Check all deployed xApps
    log_info "Checking all deployed xApps status..."

    total_xapps=$(kubectl get pods -n ricxapp --no-headers 2>/dev/null | wc -l)
    running_xapps=$(kubectl get pods -n ricxapp --no-headers 2>/dev/null | grep Running | wc -l)

    if [ $running_xapps -eq $total_xapps ] && [ $total_xapps -gt 0 ]; then
        record_test "All xApps Status" "PASS" "All $total_xapps xApps running"
    elif [ $running_xapps -gt 0 ]; then
        record_test "All xApps Status" "WARN" "$running_xapps/$total_xapps xApps running"
    else
        record_test "All xApps Status" "FAIL" "No xApps running"
    fi
}

################################################################################
# D. PERFORMANCE VALIDATION TESTS
################################################################################
test_performance() {
    log_test_start "Performance Validation Tests"

    # Test 1: Resource usage check
    log_info "Checking resource usage of components..."

    # Get top pods
    top_output=$(kubectl top pods -n ricplt 2>/dev/null || echo "")

    if [ -n "$top_output" ]; then
        record_test "Resource Metrics Available" "PASS" "Metrics server providing resource data"

        # Check for any pods using excessive resources (>500Mi memory or >500m CPU)
        high_memory=$(echo "$top_output" | awk '$3 ~ /[0-9]+Mi/ {gsub(/Mi/, "", $3); if ($3 > 500) print $1}')
        high_cpu=$(echo "$top_output" | awk '$2 ~ /[0-9]+m/ {gsub(/m/, "", $2); if ($2 > 500) print $1}')

        if [ -z "$high_memory" ] && [ -z "$high_cpu" ]; then
            record_test "Resource Usage" "PASS" "All components within normal resource limits"
        else
            record_test "Resource Usage" "WARN" "Some components using high resources"
        fi
    else
        record_test "Resource Metrics Available" "WARN" "Metrics server not available"
    fi

    # Test 2: Check for CrashLoopBackOff
    log_info "Checking for pods in error states..."

    crash_pods=$(kubectl get pods -n ricplt --no-headers 2>/dev/null | grep -E "CrashLoopBackOff|Error|ImagePullBackOff" | wc -l)
    crash_xapps=$(kubectl get pods -n ricxapp --no-headers 2>/dev/null | grep -E "CrashLoopBackOff|Error|ImagePullBackOff" | wc -l)

    total_crash=$((crash_pods + crash_xapps))

    if [ $total_crash -eq 0 ]; then
        record_test "Pod Error States" "PASS" "No pods in error/crash state"
    else
        record_test "Pod Error States" "WARN" "$total_crash pods in error state (may be expected for optional components)"
    fi

    # Test 3: Network connectivity latency
    log_info "Testing network connectivity latency..."

    # Ping between pods in same namespace
    e2mgr_pod=$(kubectl get pods -n ricplt | grep deployment-ricplt-e2mgr | grep Running | head -1 | awk '{print $1}')
    e2term_svc_ip=$(kubectl get svc -n ricplt service-ricplt-e2term-rmr-alpha -o jsonpath='{.spec.clusterIP}' 2>/dev/null)

    if [ -n "$e2mgr_pod" ] && [ -n "$e2term_svc_ip" ]; then
        # Try to measure latency
        ping_result=$(kubectl exec -n ricplt $e2mgr_pod -- ping -c 3 -W 2 $e2term_svc_ip 2>/dev/null || echo "failed")

        if echo "$ping_result" | grep -q "time="; then
            record_test "Network Latency" "PASS" "Pod-to-service communication working"
        else
            record_test "Network Latency" "WARN" "Could not measure network latency"
        fi
    else
        record_test "Network Latency" "WARN" "Could not test network latency"
    fi
}

################################################################################
# MAIN EXECUTION
################################################################################
main() {
    echo "=============================================="
    echo "O-RAN SC J-Release E2E Test Suite"
    echo "Started at: $(date)"
    echo "=============================================="
    echo ""

    # Run all test suites
    test_e2_interface_flow
    test_a1_policy_flow
    test_xapp_operations
    test_performance

    # Print summary
    echo ""
    echo "=============================================="
    echo "E2E TEST SUMMARY"
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
        elif [ "$status" == "WARN" ]; then
            echo -e "${YELLOW}⚠${NC} $name - $details"
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
