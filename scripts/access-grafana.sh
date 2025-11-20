#!/bin/bash
################################################################################
# O-RAN SC Release J - Grafana Quick Access Script
#
# Purpose: Quick access to Grafana Dashboard with port-forwarding
# Usage: ./scripts/access-grafana.sh
################################################################################

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="ricplt"
SERVICE="oran-grafana"
LOCAL_PORT=3000
SERVICE_PORT=80
DASHBOARD_UID="oran-dual-path"
USERNAME="admin"
PASSWORD="oran-ric-admin"

print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║        O-RAN RIC Grafana Dashboard Quick Access               ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

cleanup() {
    if [ ! -z "$PORT_FORWARD_PID" ]; then
        if ps -p $PORT_FORWARD_PID > /dev/null 2>&1; then
            echo ""
            echo -e "${YELLOW}Stopping port-forward (PID: $PORT_FORWARD_PID)...${NC}"
            kill $PORT_FORWARD_PID 2>/dev/null || true
            echo -e "${GREEN}✓ Port-forward stopped${NC}"
        fi
    fi
    exit 0
}

trap cleanup INT TERM

print_header

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}✗ kubectl not found${NC}"
    echo "Please install kubectl and try again"
    exit 1
fi

# Check if service exists
echo -e "${CYAN}[1/4]${NC} Checking Grafana service..."
if ! kubectl get svc -n ${NAMESPACE} ${SERVICE} &> /dev/null; then
    echo -e "${RED}✗ Grafana service '${SERVICE}' not found in namespace '${NAMESPACE}'${NC}"
    echo ""
    echo "Available services in ${NAMESPACE}:"
    kubectl get svc -n ${NAMESPACE} | grep grafana || echo "  No Grafana services found"
    exit 1
fi
echo -e "${GREEN}✓ Grafana service found${NC}"

# Check if port is already in use
echo -e "${CYAN}[2/4]${NC} Checking if port ${LOCAL_PORT} is available..."
if lsof -Pi :${LOCAL_PORT} -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠ Port ${LOCAL_PORT} is already in use${NC}"
    echo ""
    echo "Trying alternative port 8080..."
    LOCAL_PORT=8080
    if lsof -Pi :${LOCAL_PORT} -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo -e "${RED}✗ Port ${LOCAL_PORT} is also in use${NC}"
        echo ""
        echo "Please free up port 3000 or 8080 and try again"
        echo "Or manually specify a port:"
        echo "  kubectl port-forward -n ${NAMESPACE} svc/${SERVICE} <YOUR_PORT>:${SERVICE_PORT}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ Port ${LOCAL_PORT} is available${NC}"

# Start port-forward
echo -e "${CYAN}[3/4]${NC} Starting port-forward..."
kubectl port-forward -n ${NAMESPACE} svc/${SERVICE} ${LOCAL_PORT}:${SERVICE_PORT} > /dev/null 2>&1 &
PORT_FORWARD_PID=$!

# Wait for port-forward to be ready
sleep 2

if ! ps -p $PORT_FORWARD_PID > /dev/null 2>&1; then
    echo -e "${RED}✗ Failed to start port-forward${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Port-forward started (PID: ${PORT_FORWARD_PID})${NC}"

# Test connection
echo -e "${CYAN}[4/4]${NC} Testing Grafana connection..."
sleep 1
if curl -s -o /dev/null -w "%{http_code}" http://localhost:${LOCAL_PORT}/api/health 2>/dev/null | grep -q "200"; then
    echo -e "${GREEN}✓ Grafana is accessible${NC}"
else
    echo -e "${YELLOW}⚠ Grafana connection test inconclusive, but service should be accessible${NC}"
fi

# Display access information
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Grafana is now accessible!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}📊 Access URLs:${NC}"
echo -e "   Grafana Home:       ${GREEN}http://localhost:${LOCAL_PORT}${NC}"
echo -e "   Dual-Path Dashboard: ${GREEN}http://localhost:${LOCAL_PORT}/d/${DASHBOARD_UID}${NC}"
echo ""
echo -e "${CYAN}🔐 Login Credentials:${NC}"
echo -e "   Username: ${YELLOW}${USERNAME}${NC}"
echo -e "   Password: ${YELLOW}${PASSWORD}${NC}"
echo ""
echo -e "${CYAN}📍 Dashboard Location:${NC}"
echo -e "   Menu: ${YELLOW}Dashboards → Browse → O-RAN RIC - Dual-Path Communication${NC}"
echo -e "   Or use direct URL above"
echo ""
echo -e "${CYAN}📈 What to Monitor:${NC}"
echo -e "   • Active communication path (RMR/HTTP)"
echo -e "   • Failover events and rates"
echo -e "   • Message success rates by path"
echo -e "   • Path health status"
echo -e "   • Message latency and throughput"
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}ℹ  Press Ctrl+C to stop port-forward and exit${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""

# Try to open browser automatically (optional)
if [ "$1" != "--no-browser" ]; then
    echo -e "${CYAN}Attempting to open browser...${NC}"
    DASHBOARD_URL="http://localhost:${LOCAL_PORT}/d/${DASHBOARD_UID}"

    if command -v xdg-open > /dev/null 2>&1; then
        xdg-open "${DASHBOARD_URL}" 2>/dev/null &
        echo -e "${GREEN}✓ Browser opened${NC}"
    elif command -v open > /dev/null 2>&1; then
        open "${DASHBOARD_URL}" 2>/dev/null &
        echo -e "${GREEN}✓ Browser opened${NC}"
    elif command -v wslview > /dev/null 2>&1; then
        wslview "${DASHBOARD_URL}" 2>/dev/null &
        echo -e "${GREEN}✓ Browser opened${NC}"
    else
        echo -e "${YELLOW}⚠ Could not auto-open browser${NC}"
        echo -e "${YELLOW}  Please manually open: ${DASHBOARD_URL}${NC}"
    fi
    echo ""
fi

# Keep running until interrupted
wait $PORT_FORWARD_PID
