#!/bin/bash
# Onboard script for O-RAN xApps to RIC Platform
# Version: 1.0.0

set -e

# Configuration
APPMGR_URL="${APPMGR_URL:-http://service-ricplt-appmgr-http.ricplt:8080}"
CHART_REPO="${CHART_REPO:-http://aux-entry/helm}"
NAMESPACE="${NAMESPACE:-ricxapp}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}O-RAN xApp Onboarding Script${NC}"
echo "AppMgr URL: $APPMGR_URL"
echo "Namespace: $NAMESPACE"
echo ""

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}kubectl is not installed${NC}"
        exit 1
    fi
    
    # Check if curl is installed
    if ! command -v curl &> /dev/null; then
        echo -e "${RED}curl is not installed${NC}"
        exit 1
    fi
    
    # Check if RIC platform is running
    kubectl get pods -n ricplt > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo -e "${RED}Cannot access RIC platform. Is it running?${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Prerequisites check passed${NC}\n"
}

# Function to create xApp descriptor
create_descriptor() {
    local xapp_name=$1
    local config_file=$2
    local output_file=$3
    
    echo -e "${BLUE}Creating descriptor for $xapp_name...${NC}"
    
    # Create xApp descriptor JSON
    cat > $output_file <<EOF
{
    "xapp_name": "$xapp_name",
    "version": "1.0.0",
    "description": "$xapp_name xApp for O-RAN Release J",
    "config-file": "$config_file",
    "controls": {
        "active": true,
        "requestorId": 100,
        "ranFunctionId": 1
    }
}
EOF
    
    echo -e "${GREEN}✓ Descriptor created: $output_file${NC}"
}

# Function to onboard xApp
onboard_xapp() {
    local xapp_name=$1
    local config_path=$2
    
    echo -e "${YELLOW}Onboarding $xapp_name...${NC}"
    
    # Create temporary descriptor
    local descriptor="/tmp/${xapp_name}-descriptor.json"
    create_descriptor "$xapp_name" "$config_path/config.json" "$descriptor"
    
    # Check if xApp already exists
    existing=$(curl -s ${APPMGR_URL}/ric/v1/xapps | grep -c "\"$xapp_name\"" || true)
    
    if [ "$existing" -gt 0 ]; then
        echo -e "${YELLOW}xApp $xapp_name already exists, updating...${NC}"
        # Update existing xApp
        curl -X PUT \
            ${APPMGR_URL}/ric/v1/xapps/${xapp_name} \
            -H "Content-Type: application/json" \
            -d @${config_path}/config.json
    else
        # Onboard new xApp
        curl -X POST \
            ${APPMGR_URL}/ric/v1/xapps \
            -H "Content-Type: application/json" \
            -d @${config_path}/config.json
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $xapp_name onboarded successfully${NC}"
    else
        echo -e "${RED}✗ Failed to onboard $xapp_name${NC}"
        return 1
    fi
    
    # Clean up
    rm -f $descriptor
    echo ""
}

# Function to verify onboarding
verify_onboarding() {
    echo -e "${YELLOW}Verifying onboarded xApps...${NC}"
    
    # Get list of onboarded xApps
    response=$(curl -s ${APPMGR_URL}/ric/v1/xapps)
    
    echo "Onboarded xApps:"
    echo "$response" | python3 -m json.tool | grep "xapp_name" || true
    echo ""
    
    # Check each xApp
    for xapp in kpimon qoe-predictor ran-control federated-learning; do
        if echo "$response" | grep -q "\"$xapp\""; then
            echo -e "${GREEN}✓ $xapp is onboarded${NC}"
        else
            echo -e "${RED}✗ $xapp is not onboarded${NC}"
        fi
    done
}

# Function to create ConfigMaps
create_configmaps() {
    echo -e "${YELLOW}Creating ConfigMaps...${NC}"
    
    for xapp in kpimon qoe-predictor ran-control federated-learning; do
        kubectl create configmap ${xapp}-config \
            --from-file=config.json=${xapp}/config/config.json \
            -n ${NAMESPACE} \
            --dry-run=client -o yaml | kubectl apply -f -
        
        echo -e "${GREEN}✓ ConfigMap created for $xapp${NC}"
    done
    echo ""
}

# Function to create RBAC resources
create_rbac() {
    echo -e "${YELLOW}Creating RBAC resources...${NC}"
    
    # Create ServiceAccount
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: xapp-serviceaccount
  namespace: ${NAMESPACE}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: xapp-role
  namespace: ${NAMESPACE}
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: xapp-rolebinding
  namespace: ${NAMESPACE}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: xapp-role
subjects:
- kind: ServiceAccount
  name: xapp-serviceaccount
  namespace: ${NAMESPACE}
EOF
    
    echo -e "${GREEN}✓ RBAC resources created${NC}\n"
}

# Main function
main() {
    echo "Starting xApp onboarding process..."
    echo "===================================="
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Create namespace if it doesn't exist
    kubectl create namespace ${NAMESPACE} 2>/dev/null || true
    
    # Create RBAC resources
    create_rbac
    
    # Create ConfigMaps
    create_configmaps
    
    # Onboard each xApp
    onboard_xapp "kpimon" "kpimon/config"
    onboard_xapp "qoe-predictor" "qoe-predictor/config"
    onboard_xapp "ran-control" "ran-control/config"
    onboard_xapp "federated-learning" "federated-learning/config"
    
    # Verify onboarding
    verify_onboarding
    
    echo ""
    echo "===================================="
    echo -e "${GREEN}Onboarding process completed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Run ./deploy-all.sh to deploy the xApps"
    echo "2. Check xApp status: kubectl get pods -n ${NAMESPACE}"
    echo "3. View logs: kubectl logs -n ${NAMESPACE} <pod-name>"
}

# Run main function
main
