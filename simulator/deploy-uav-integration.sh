#!/bin/bash
#
# UAV Integration Deployment Script
# Purpose: Build and deploy E2-simulator with UAV support and ns-O-RAN bridge
#

set -e

REGISTRY="${REGISTRY:-localhost:5000}"
E2_SIM_IMAGE="${REGISTRY}/e2-simulator:uav-enabled"
BRIDGE_IMAGE="${REGISTRY}/ns-oran-bridge:1.0.0"
NAMESPACE="${NAMESPACE:-ricxapp}"

echo "=========================================="
echo "E2-Simulator UAV Integration Deployment"
echo "=========================================="
echo "Registry: $REGISTRY"
echo "Namespace: $NAMESPACE"
echo ""

# Step 1: Build E2-Simulator
echo "[1/4] Building E2-Simulator (UAV-enabled)..."
cd "$(dirname "$0")/e2-simulator"
docker build -t "$E2_SIM_IMAGE" .
echo "✓ E2-Simulator built successfully"
echo ""

# Step 2: Build ns-O-RAN Bridge
echo "[2/4] Building ns-O-RAN Bridge..."
cd "$(dirname "$0")/ns-oran-bridge"
docker build -t "$BRIDGE_IMAGE" .
echo "✓ ns-O-RAN Bridge built successfully"
echo ""

# Step 3: Push images
echo "[3/4] Pushing Docker images..."
docker push "$E2_SIM_IMAGE"
echo "✓ E2-Simulator pushed"
docker push "$BRIDGE_IMAGE"
echo "✓ ns-O-RAN Bridge pushed"
echo ""

# Step 4: Deploy to Kubernetes
echo "[4/4] Deploying to Kubernetes (namespace: $NAMESPACE)..."

# Check if namespace exists
if ! kubectl get namespace "$NAMESPACE" &>/dev/null; then
    echo "Creating namespace: $NAMESPACE"
    kubectl create namespace "$NAMESPACE"
fi

# Deploy E2-Simulator
echo "Deploying E2-Simulator..."
kubectl apply -n "$NAMESPACE" -f "$(dirname "$0")/e2-simulator/deploy/deployment.yaml"

# Deploy ns-O-RAN Bridge
echo "Deploying ns-O-RAN Bridge..."
kubectl apply -n "$NAMESPACE" -f "$(dirname "$0")/ns-oran-bridge/deploy/deployment.yaml"

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Verify deployment:"
echo "  kubectl -n $NAMESPACE get pods"
echo ""
echo "View logs:"
echo "  kubectl -n $NAMESPACE logs -f deployment/e2-simulator"
echo "  kubectl -n $NAMESPACE logs -f deployment/ns-oran-bridge"
echo ""
echo "Port forward for testing:"
echo "  kubectl -n $NAMESPACE port-forward svc/e2-simulator 8080:8080 &"
echo "  kubectl -n $NAMESPACE port-forward svc/ns-oran-bridge 5000:5000 &"
echo ""
echo "Run tests:"
echo "  python e2-simulator/test_uav_integration.py --url http://localhost:8080"
echo "  python ns-oran-bridge/test_bridge.py --url http://localhost:5000"
echo ""
