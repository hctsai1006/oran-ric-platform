#!/bin/bash
#
# GPU Support Setup for O-RAN RIC Platform
#
# Purpose: Complete GPU support setup including:
#   - NVIDIA Container Toolkit installation
#   - Containerd runtime configuration
#   - NVIDIA Device Plugin deployment with RuntimeClass
#   - Node labeling for GPU workloads
#
# This script contains ALL the steps that were successfully verified
# on RTX 3060 GPU system with k3s v1.28.5+k3s1
#

set -e

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load validation library
source "${PROJECT_ROOT}/scripts/lib/validation.sh"

# KUBECONFIG setup
if ! setup_kubeconfig; then
    exit 1
fi

echo "=========================================================================="
echo -e "${CYAN}   NVIDIA GPU Support Setup for O-RAN RIC Platform${NC}"
echo "   Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================================================="
echo
echo "This script will install and configure:"
echo "  ✓ NVIDIA Container Toolkit (v1.18.0+)"
echo "  ✓ Containerd runtime configuration for k3s"
echo "  ✓ NVIDIA RuntimeClass"
echo "  ✓ NVIDIA Device Plugin with GPU support"
echo "  ✓ Node labels for GPU scheduling"
echo
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 0
fi
echo

# ============================================================================
# Step 1: Prerequisites Check
# ============================================================================
echo -e "${YELLOW}[Step 1/8]${NC} Checking prerequisites..."

# Check if nvidia-smi is available
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${RED}Error: nvidia-smi not found. Please install NVIDIA drivers first.${NC}"
    echo
    echo "To install NVIDIA drivers:"
    echo "  1. ubuntu-drivers devices"
    echo "  2. sudo ubuntu-drivers autoinstall"
    echo "  3. sudo reboot"
    exit 1
fi

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl not found.${NC}"
    exit 1
fi

# Check if cluster is accessible
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}Error: Cannot connect to Kubernetes cluster.${NC}"
    exit 1
fi

# Check if k3s is running
if ! systemctl is-active --quiet k3s; then
    echo -e "${RED}Error: k3s service is not running.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites check passed${NC}"
echo

# ============================================================================
# Step 2: Display GPU Information
# ============================================================================
echo -e "${YELLOW}[Step 2/8]${NC} Detected GPU information:"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
echo
nvidia-smi -L
echo

# ============================================================================
# Step 3: Install NVIDIA Container Toolkit
# ============================================================================
echo -e "${YELLOW}[Step 3/8]${NC} Installing NVIDIA Container Toolkit..."

# Check if already installed
if command -v nvidia-ctk &> /dev/null; then
    echo -e "${CYAN}NVIDIA Container Toolkit already installed:${NC}"
    nvidia-ctk --version
    echo
    read -p "Reinstall? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping installation..."
    else
        echo "Proceeding with reinstallation..."

        # Add NVIDIA Container Toolkit repository
        echo "Adding NVIDIA Container Toolkit repository..."

        # Download and install GPG key
        curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
            sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

        # Add repository
        curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
            sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
            sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

        # Update package list
        echo "Updating package list..."
        sudo apt-get update

        # Install NVIDIA Container Toolkit
        echo "Installing nvidia-container-toolkit..."
        sudo apt-get install -y nvidia-container-toolkit

        echo -e "${GREEN}✓ NVIDIA Container Toolkit installed${NC}"
        nvidia-ctk --version
    fi
else
    echo "Installing NVIDIA Container Toolkit..."

    # Add NVIDIA Container Toolkit repository
    echo "Adding NVIDIA Container Toolkit repository..."

    # Download and install GPG key
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
        sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

    # Add repository
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

    # Update package list
    echo "Updating package list..."
    sudo apt-get update

    # Install NVIDIA Container Toolkit
    echo "Installing nvidia-container-toolkit..."
    sudo apt-get install -y nvidia-container-toolkit

    echo -e "${GREEN}✓ NVIDIA Container Toolkit installed${NC}"
    nvidia-ctk --version
fi
echo

# ============================================================================
# Step 4: Configure Containerd for k3s
# ============================================================================
echo -e "${YELLOW}[Step 4/8]${NC} Configuring containerd runtime for k3s..."

# Create containerd config directory if it doesn't exist
sudo mkdir -p /etc/containerd/config.d

# Configure NVIDIA runtime
echo "Configuring NVIDIA runtime..."
sudo nvidia-ctk runtime configure --runtime=containerd --set-as-default

# Verify configuration
if [ -f /etc/containerd/config.d/99-nvidia.toml ]; then
    echo -e "${GREEN}✓ Containerd configuration updated${NC}"
    echo "Configuration file: /etc/containerd/config.d/99-nvidia.toml"
else
    echo -e "${RED}Error: Configuration file not created${NC}"
    exit 1
fi
echo

# ============================================================================
# Step 5: Restart k3s Service
# ============================================================================
echo -e "${YELLOW}[Step 5/8]${NC} Restarting k3s service to apply changes..."

echo "Restarting k3s..."
sudo systemctl restart k3s

# Wait for k3s to be ready
echo "Waiting for k3s to be ready..."
sleep 10

# Verify k3s is running
if ! systemctl is-active --quiet k3s; then
    echo -e "${RED}Error: k3s failed to restart${NC}"
    exit 1
fi

# Verify kubectl connection
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}Error: Cannot connect to cluster after restart${NC}"
    exit 1
fi

echo -e "${GREEN}✓ k3s restarted successfully${NC}"
echo

# ============================================================================
# Step 6: Create NVIDIA RuntimeClass
# ============================================================================
echo -e "${YELLOW}[Step 6/8]${NC} Creating NVIDIA RuntimeClass..."

# Create RuntimeClass
cat <<EOF | kubectl apply -f -
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: nvidia
handler: nvidia
EOF

echo -e "${GREEN}✓ NVIDIA RuntimeClass created${NC}"
kubectl get runtimeclass nvidia
echo

# ============================================================================
# Step 7: Deploy NVIDIA Device Plugin with RuntimeClass
# ============================================================================
echo -e "${YELLOW}[Step 7/8]${NC} Deploying NVIDIA Device Plugin..."

# Check if already installed
if kubectl get daemonset -n kube-system nvidia-device-plugin-daemonset &> /dev/null; then
    echo -e "${CYAN}NVIDIA Device Plugin already installed.${NC}"
    read -p "Reinstall with correct RuntimeClass configuration? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl delete daemonset -n kube-system nvidia-device-plugin-daemonset
        echo "Waiting for cleanup..."
        sleep 5
    else
        echo "Skipping installation..."
        echo
        echo -e "${YELLOW}[7/8]${NC} Labeling nodes with GPU..."
        NODES=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')
        for NODE in $NODES; do
            echo "Labeling node: $NODE"
            kubectl label nodes $NODE nvidia.com/gpu=true --overwrite
        done
        echo -e "${GREEN}✓ Nodes labeled${NC}"
        echo
        echo "=========================================================================="
        echo -e "${GREEN}✓ GPU Support Setup Complete!${NC}"
        echo "=========================================================================="
        exit 0
    fi
fi

# Deploy NVIDIA Device Plugin with RuntimeClass
# IMPORTANT: This configuration includes runtimeClassName: nvidia
# which is CRITICAL for the Device Plugin to access GPU hardware
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: nvidia-device-plugin-daemonset
  namespace: kube-system
spec:
  selector:
    matchLabels:
      name: nvidia-device-plugin-ds
  updateStrategy:
    type: RollingUpdate
  template:
    metadata:
      labels:
        name: nvidia-device-plugin-ds
    spec:
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
      priorityClassName: "system-node-critical"
      runtimeClassName: nvidia  # CRITICAL: Allows Device Plugin to see GPU
      containers:
      - image: nvcr.io/nvidia/k8s-device-plugin:v0.14.0
        name: nvidia-device-plugin-ctr
        env:
          - name: FAIL_ON_INIT_ERROR
            value: "false"
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop: ["ALL"]
        volumeMounts:
        - name: device-plugin
          mountPath: /var/lib/kubelet/device-plugins
      volumes:
      - name: device-plugin
        hostPath:
          path: /var/lib/kubelet/device-plugins
EOF

# Wait for daemonset to be ready
echo "Waiting for NVIDIA Device Plugin to be ready..."
kubectl rollout status daemonset/nvidia-device-plugin-daemonset -n kube-system --timeout=120s

echo -e "${GREEN}✓ NVIDIA Device Plugin installed${NC}"
echo

# Check Device Plugin logs
echo "Checking Device Plugin logs..."
sleep 5
DEVICE_PLUGIN_POD=$(kubectl get pods -n kube-system -l name=nvidia-device-plugin-ds -o jsonpath='{.items[0].metadata.name}')
if [ -n "$DEVICE_PLUGIN_POD" ]; then
    echo "Recent logs from $DEVICE_PLUGIN_POD:"
    kubectl logs -n kube-system $DEVICE_PLUGIN_POD --tail=10
    echo
fi

# ============================================================================
# Step 8: Label Nodes with GPU
# ============================================================================
echo -e "${YELLOW}[Step 8/8]${NC} Labeling nodes with GPU..."

# Get all nodes
NODES=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')

for NODE in $NODES; do
    echo "Labeling node: $NODE"
    kubectl label nodes $NODE nvidia.com/gpu=true --overwrite
done

echo -e "${GREEN}✓ Nodes labeled${NC}"
echo

# ============================================================================
# Verification
# ============================================================================
echo "=========================================================================="
echo "   Verification"
echo "=========================================================================="
echo

echo "GPU resources on nodes:"
kubectl get nodes -o=custom-columns=NAME:.metadata.name,GPU:.status.capacity.'nvidia\.com/gpu'
echo

echo "NVIDIA Device Plugin pods:"
kubectl get pods -n kube-system -l name=nvidia-device-plugin-ds
echo

# Check if GPU resources are actually detected
GPU_COUNT=$(kubectl get nodes -o json | jq -r '.items[].status.capacity."nvidia.com/gpu" // "0"' | awk '{sum += $1} END {print sum}')

if [ "$GPU_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ GPU resources detected: $GPU_COUNT GPU(s)${NC}"
else
    echo -e "${RED}⚠ Warning: No GPU resources detected!${NC}"
    echo
    echo "Troubleshooting steps:"
    echo "  1. Check Device Plugin logs:"
    echo "     kubectl logs -n kube-system -l name=nvidia-device-plugin-ds"
    echo
    echo "  2. Verify NVML library is accessible:"
    echo "     kubectl exec -n kube-system -l name=nvidia-device-plugin-ds -- nvidia-smi"
    echo
    echo "  3. Check RuntimeClass:"
    echo "     kubectl get runtimeclass nvidia"
    echo
    exit 1
fi
echo

echo "=========================================================================="
echo -e "${GREEN}✓ GPU Support Setup Complete!${NC}"
echo "=========================================================================="
echo
echo "Summary of installed components:"
echo "  ✓ NVIDIA Container Toolkit ($(nvidia-ctk --version 2>&1 | head -n1))"
echo "  ✓ Containerd runtime configured (/etc/containerd/config.d/99-nvidia.toml)"
echo "  ✓ NVIDIA RuntimeClass created"
echo "  ✓ NVIDIA Device Plugin deployed (v0.14.0)"
echo "  ✓ Nodes labeled with nvidia.com/gpu=true"
echo "  ✓ GPU resources available: $GPU_COUNT GPU(s)"
echo
echo "Next steps:"
echo "  1. Deploy GPU-enabled Federated Learning xApp:"
echo "     kubectl apply -f xapps/federated-learning/deploy/deployment-gpu.yaml -n ricxapp"
echo
echo "  2. Or use wednesday-safe-deploy.sh which will auto-detect GPU:"
echo "     bash scripts/wednesday-safe-deploy.sh"
echo
echo "  3. Verify GPU pod is scheduled:"
echo "     kubectl get pods -n ricxapp -l app=federated-learning"
echo
echo "  4. Check GPU usage inside pod:"
echo "     kubectl exec -n ricxapp <pod-name> -- nvidia-smi"
echo
echo "  5. Monitor GPU utilization:"
echo "     watch -n 1 nvidia-smi"
echo
