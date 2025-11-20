#!/bin/bash
################################################################################
# O-RAN SC Release J - Grafana Dashboard Setup Script
#
# Purpose: Automatically configure Grafana with dual-path communication dashboard
# Author: O-RAN RIC Platform Team
# Date: 2025-11-20
#
# Usage:
#   ./scripts/setup-grafana-dashboard.sh [OPTIONS]
#
# Options:
#   -g, --grafana-url URL     Grafana URL (default: auto-detect from kubectl)
#   -u, --username USER       Grafana admin username (default: admin)
#   -p, --password PASS       Grafana admin password (default: oran-ric-admin)
#   -n, --namespace NS        Kubernetes namespace (default: ricplt)
#   -h, --help               Show this help message
#
# Examples:
#   # Auto-detect Grafana in cluster
#   ./scripts/setup-grafana-dashboard.sh
#
#   # Specify custom Grafana URL
#   ./scripts/setup-grafana-dashboard.sh -g http://grafana.example.com:3000
#
#   # Use port-forward to local Grafana
#   kubectl port-forward -n ricplt svc/grafana 3000:80 &
#   ./scripts/setup-grafana-dashboard.sh -g http://localhost:3000
#
################################################################################

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
GRAFANA_URL=""
GRAFANA_USER="admin"
GRAFANA_PASS="oran-ric-admin"
NAMESPACE="ricplt"
DASHBOARD_FILE="monitoring/grafana/dashboards/dual-path-communication.json"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

################################################################################
# Functions
################################################################################

print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  O-RAN SC Release J - Grafana Dashboard Setup                 ║${NC}"
    echo -e "${BLUE}║  Dual-Path Communication Monitoring                            ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}[Step]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

show_help() {
    sed -n '/^# Usage:/,/^################################################################################/p' "$0" | grep -v '##' | sed 's/^# //'
    exit 0
}

check_dependencies() {
    print_step "Checking dependencies..."

    local missing_deps=()

    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi

    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi

    if ! command -v kubectl &> /dev/null; then
        print_warning "kubectl not found - will use provided Grafana URL"
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing required dependencies: ${missing_deps[*]}"
        echo "Please install them and try again."
        exit 1
    fi

    print_success "All dependencies available"
}

auto_detect_grafana() {
    print_step "Auto-detecting Grafana in Kubernetes cluster..."

    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl not found - cannot auto-detect Grafana"
        return 1
    fi

    # Try to find Grafana service
    local grafana_svc=$(kubectl get svc -n ${NAMESPACE} -l app.kubernetes.io/name=grafana -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

    if [ -z "$grafana_svc" ]; then
        # Try alternative label
        grafana_svc=$(kubectl get svc -n ${NAMESPACE} -l app=grafana -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    fi

    if [ -z "$grafana_svc" ]; then
        print_warning "Could not auto-detect Grafana service in namespace ${NAMESPACE}"
        return 1
    fi

    local grafana_port=$(kubectl get svc -n ${NAMESPACE} ${grafana_svc} -o jsonpath='{.spec.ports[0].port}' 2>/dev/null)

    print_success "Found Grafana service: ${grafana_svc} on port ${grafana_port}"

    # Check if we can access it via port-forward
    print_step "Setting up port-forward to Grafana..."
    kubectl port-forward -n ${NAMESPACE} svc/${grafana_svc} 3000:${grafana_port} > /dev/null 2>&1 &
    local port_forward_pid=$!

    # Wait for port-forward to be ready
    sleep 2

    if ps -p $port_forward_pid > /dev/null; then
        GRAFANA_URL="http://localhost:3000"
        print_success "Port-forward established (PID: ${port_forward_pid})"
        echo "export GRAFANA_PORT_FORWARD_PID=${port_forward_pid}" > /tmp/grafana-port-forward.pid
        print_warning "Remember to kill port-forward process when done: kill ${port_forward_pid}"
        return 0
    else
        print_error "Failed to establish port-forward"
        return 1
    fi
}

test_grafana_connection() {
    print_step "Testing Grafana connection at ${GRAFANA_URL}..."

    local response=$(curl -s -o /dev/null -w "%{http_code}" \
        -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
        "${GRAFANA_URL}/api/health" 2>/dev/null || echo "000")

    if [ "$response" = "200" ]; then
        print_success "Successfully connected to Grafana"
        return 0
    else
        print_error "Failed to connect to Grafana (HTTP ${response})"
        print_error "Please check:"
        print_error "  - Grafana URL: ${GRAFANA_URL}"
        print_error "  - Username: ${GRAFANA_USER}"
        print_error "  - Password: ${GRAFANA_PASS}"
        return 1
    fi
}

check_prometheus_datasource() {
    print_step "Checking Prometheus datasource..."

    local datasources=$(curl -s -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
        "${GRAFANA_URL}/api/datasources" 2>/dev/null)

    local prometheus_count=$(echo "$datasources" | jq '[.[] | select(.type=="prometheus")] | length')

    if [ "$prometheus_count" -gt 0 ]; then
        local prometheus_name=$(echo "$datasources" | jq -r '[.[] | select(.type=="prometheus")][0].name')
        print_success "Prometheus datasource found: ${prometheus_name}"
        return 0
    else
        print_warning "No Prometheus datasource found"
        print_warning "Dashboard will be imported but may not work until datasource is configured"
        return 1
    fi
}

import_dashboard() {
    print_step "Importing dual-path communication dashboard..."

    local dashboard_path="${PROJECT_ROOT}/${DASHBOARD_FILE}"

    if [ ! -f "$dashboard_path" ]; then
        print_error "Dashboard file not found: ${dashboard_path}"
        return 1
    fi

    # Read dashboard JSON
    local dashboard_json=$(cat "$dashboard_path")

    # Create import payload
    local import_payload=$(jq -n \
        --argjson dashboard "$dashboard_json" \
        '{
            dashboard: $dashboard,
            overwrite: true,
            inputs: [],
            folderId: 0
        }')

    # Import dashboard
    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
        -d "$import_payload" \
        "${GRAFANA_URL}/api/dashboards/db")

    local status=$(echo "$response" | jq -r '.status // "error"')

    if [ "$status" = "success" ]; then
        local dashboard_uid=$(echo "$response" | jq -r '.uid')
        local dashboard_url="${GRAFANA_URL}/d/${dashboard_uid}"

        print_success "Dashboard imported successfully!"
        echo ""
        echo -e "${GREEN}Dashboard URL:${NC} ${dashboard_url}"
        echo ""
        return 0
    else
        local message=$(echo "$response" | jq -r '.message // "Unknown error"')
        print_error "Failed to import dashboard: ${message}"
        return 1
    fi
}

verify_dashboard() {
    print_step "Verifying dashboard installation..."

    local dashboards=$(curl -s -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
        "${GRAFANA_URL}/api/search?type=dash-db" 2>/dev/null)

    local dual_path_dashboard=$(echo "$dashboards" | jq '.[] | select(.uid=="oran-dual-path")')

    if [ -n "$dual_path_dashboard" ]; then
        local dashboard_title=$(echo "$dual_path_dashboard" | jq -r '.title')
        print_success "Dashboard verified: ${dashboard_title}"
        return 0
    else
        print_error "Dashboard verification failed"
        return 1
    fi
}

cleanup() {
    if [ -f /tmp/grafana-port-forward.pid ]; then
        source /tmp/grafana-port-forward.pid 2>/dev/null || true
        if [ -n "$GRAFANA_PORT_FORWARD_PID" ]; then
            if ps -p $GRAFANA_PORT_FORWARD_PID > /dev/null 2>&1; then
                print_step "Cleaning up port-forward (PID: ${GRAFANA_PORT_FORWARD_PID})..."
                kill $GRAFANA_PORT_FORWARD_PID 2>/dev/null || true
                print_success "Port-forward cleaned up"
            fi
        fi
        rm -f /tmp/grafana-port-forward.pid
    fi
}

################################################################################
# Main
################################################################################

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -g|--grafana-url)
            GRAFANA_URL="$2"
            shift 2
            ;;
        -u|--username)
            GRAFANA_USER="$2"
            shift 2
            ;;
        -p|--password)
            GRAFANA_PASS="$2"
            shift 2
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Set up cleanup trap
trap cleanup EXIT

# Main execution
print_header

check_dependencies

# Auto-detect Grafana if URL not provided
if [ -z "$GRAFANA_URL" ]; then
    if ! auto_detect_grafana; then
        print_error "Could not auto-detect Grafana URL"
        echo ""
        echo "Please provide Grafana URL manually:"
        echo "  $0 -g http://your-grafana-url:3000"
        exit 1
    fi
fi

# Test connection
if ! test_grafana_connection; then
    exit 1
fi

# Check datasource (warning only, don't fail)
check_prometheus_datasource || true

# Import dashboard
if ! import_dashboard; then
    exit 1
fi

# Verify installation
if ! verify_dashboard; then
    print_warning "Dashboard import succeeded but verification failed"
    print_warning "Please check Grafana manually"
fi

echo ""
print_success "Setup completed successfully!"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Next Steps:${NC}"
echo -e "  1. Open Grafana: ${GRAFANA_URL}"
echo -e "  2. Login with username: ${GRAFANA_USER}"
echo -e "  3. Navigate to Dashboards → O-RAN RIC - Dual-Path Communication"
echo -e "  4. Monitor your dual-path communication metrics"
echo ""
echo -e "${YELLOW}Dashboard Features:${NC}"
echo -e "  • Active communication path (RMR/HTTP) gauge"
echo -e "  • Failover event rate monitoring"
echo -e "  • Message success rate by path"
echo -e "  • Path health status indicators"
echo -e "  • Message latency comparison"
echo -e "  • Message throughput visualization"
echo -e "  • Consecutive failure tracking"
echo -e "  • Registered endpoints overview"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
