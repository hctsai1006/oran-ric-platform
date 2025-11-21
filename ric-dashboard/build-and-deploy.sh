#!/bin/bash

# Build and Deploy RIC Dashboard
# MBWCL - 行動寬頻無線通訊實驗室

set -e

echo "========================================="
echo "RIC Dashboard Build and Deploy Script"
echo "MBWCL - 行動寬頻無線通訊實驗室"
echo "========================================="

# Configuration
IMAGE_NAME="ric-dashboard"
IMAGE_TAG="latest"
REGISTRY="localhost:5000"
FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
NAMESPACE="ricplt"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Build Docker image
echo -e "${YELLOW}[Step 1/5]${NC} Building Docker image..."
docker build -t ${FULL_IMAGE} .
echo -e "${GREEN}✓${NC} Docker image built successfully"

# Step 2: Push to local registry
echo -e "${YELLOW}[Step 2/5]${NC} Pushing image to local registry..."
docker push ${FULL_IMAGE}
echo -e "${GREEN}✓${NC} Image pushed to registry"

# Step 3: Create namespace if not exists
echo -e "${YELLOW}[Step 3/5]${NC} Ensuring namespace exists..."
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
echo -e "${GREEN}✓${NC} Namespace ready"

# Step 4: Apply Kubernetes manifests
echo -e "${YELLOW}[Step 4/5]${NC} Deploying to Kubernetes..."
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/ingress.yaml
echo -e "${GREEN}✓${NC} Kubernetes resources created"

# Step 5: Wait for deployment
echo -e "${YELLOW}[Step 5/5]${NC} Waiting for pods to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/ric-dashboard -n ${NAMESPACE}
echo -e "${GREEN}✓${NC} Deployment ready"

# Display access information
echo ""
echo "========================================="
echo -e "${GREEN}Deployment Completed Successfully!${NC}"
echo "========================================="
echo ""
echo "Access the dashboard using one of the following methods:"
echo ""
echo "1. Port Forward (Recommended for development):"
echo "   kubectl port-forward -n ${NAMESPACE} svc/ric-dashboard 8080:80"
echo "   Then open: http://localhost:8080"
echo ""
echo "2. NodePort (Direct node access):"
echo "   http://<node-ip>:30080"
echo ""
echo "3. Ingress (if configured):"
echo "   http://ric-dashboard.local"
echo "   (Add '127.0.0.1 ric-dashboard.local' to /etc/hosts)"
echo ""
echo "Check status:"
echo "   kubectl get pods -n ${NAMESPACE} -l app=ric-dashboard"
echo "   kubectl logs -n ${NAMESPACE} -l app=ric-dashboard"
echo ""
echo "API Gateway health:"
echo "   curl http://localhost:8080/health"
echo ""
echo "========================================="
