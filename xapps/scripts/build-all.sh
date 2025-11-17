#!/bin/bash
# Build script for all O-RAN xApps
# Version: 1.0.0

set -e

# Configuration
REGISTRY="${REGISTRY:-localhost:5000}"
TAG="${TAG:-1.0.0}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building O-RAN xApps for Release J${NC}"
echo "Registry: $REGISTRY"
echo "Tag: $TAG"
echo ""

# Function to build xApp
build_xapp() {
    local xapp_name=$1
    local xapp_dir=$2
    
    echo -e "${YELLOW}Building $xapp_name...${NC}"
    
    # Check if directory exists
    if [ ! -d "$xapp_dir" ]; then
        echo -e "${RED}Error: Directory $xapp_dir not found${NC}"
        return 1
    fi
    
    # Build Docker image
    docker build -t ${REGISTRY}/xapp-${xapp_name}:${TAG} ${xapp_dir}/
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $xapp_name built successfully${NC}"
        
        # Push to registry if not localhost
        if [ "$REGISTRY" != "localhost:5000" ]; then
            echo "Pushing to registry..."
            docker push ${REGISTRY}/xapp-${xapp_name}:${TAG}
            echo -e "${GREEN}✓ $xapp_name pushed to registry${NC}"
        fi
    else
        echo -e "${RED}✗ Failed to build $xapp_name${NC}"
        return 1
    fi
    
    echo ""
}

# Create placeholder directories for model and policy files
create_placeholders() {
    echo -e "${YELLOW}Creating placeholder directories...${NC}"
    
    # QoE Predictor models
    mkdir -p qoe-predictor/models
    touch qoe-predictor/models/.gitkeep
    
    # RAN Control policies
    mkdir -p ran-control/policies
    echo '{"default_policy": "active"}' > ran-control/policies/default.json
    
    # Federated Learning models and aggregator
    mkdir -p federated-learning/models
    mkdir -p federated-learning/aggregator
    touch federated-learning/models/.gitkeep
    touch federated-learning/aggregator/.gitkeep
    
    echo -e "${GREEN}✓ Placeholders created${NC}\n"
}

# Main build process
main() {
    echo "Starting build process..."
    echo "========================="
    echo ""
    
    # Create placeholders
    create_placeholders
    
    # Build each xApp
    build_xapp "kpimon" "kpimon"
    build_xapp "qoe-predictor" "qoe-predictor"
    build_xapp "ran-control" "ran-control"
    build_xapp "federated-learning" "federated-learning"
    
    echo "========================="
    echo -e "${GREEN}Build process completed!${NC}"
    echo ""
    echo "Built images:"
    docker images | grep xapp- | grep $TAG
    echo ""
    echo "Next steps:"
    echo "1. Run ./onboard-xapps.sh to onboard xApps to RIC"
    echo "2. Run ./deploy-all.sh to deploy xApps"
}

# Run main function
main
