# GPU Compatibility Research for Kubernetes (November 2025)

## Research Question

**問題**: 不同的 GPU 會有不同的獲取資源的方式嗎？導致要好多個不同版本的？

**Answer**: **NO** - 不同 GPU 型號使用統一的資源獲取方式，不需要多個不同版本。

## Key Findings

### 1. Unified Resource Management (統一資源管理)

All NVIDIA GPUs are exposed through **the same unified resource interface**:
- **Resource name**: `nvidia.com/gpu`
- **Works for all models**: RTX 3060, Tesla T4, V100, P100, A100, H100, etc.
- **Same deployment YAML** works across different GPU models
- **No need for GPU-specific application versions**

**Key Insight**: The NVIDIA Device Plugin discovers GPUs via NVML library and exposes them as `nvidia.com/gpu` resources, providing a **consistent interface across different GPU types**.

### 2. How Kubernetes Handles Different GPUs

```
┌─────────────────────────────────────────────────────────────┐
│  Application Pod                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │  requests:                                          │    │
│  │    nvidia.com/gpu: "1"                             │    │
│  │                                                     │    │
│  │  (No need to specify GPU model)                    │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  NVIDIA Device Plugin                                        │
│  - Detects: RTX 3060, Tesla T4, A100, H100, etc.           │
│  - Exposes all as: nvidia.com/gpu                          │
│  - Treats all GPUs equally                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Kubernetes Scheduler                                        │
│  - Assigns pod to any node with available nvidia.com/gpu   │
│  - Application automatically uses whatever GPU is assigned  │
└─────────────────────────────────────────────────────────────┘
```

### 3. When You Have Mixed GPU Hardware

**Scenario**: Cluster with different GPU models (e.g., some nodes have RTX 3060, others have A100)

**Solution**: Use node labels and selectors, NOT different application versions

```yaml
# Label nodes by GPU type
kubectl label nodes node-1 gpu-type=rtx3060
kubectl label nodes node-2 gpu-type=a100

# Select specific GPU type in deployment (if needed)
spec:
  nodeSelector:
    gpu-type: rtx3060  # or a100
  containers:
  - resources:
      requests:
        nvidia.com/gpu: "1"  # Same resource name!
```

**Important**: The application code doesn't need to change - CUDA/TensorFlow/PyTorch automatically detect and use whatever GPU is assigned.

### 4. GPU Feature Compatibility (2025)

Different GPU families support different advanced features:

| Feature | Compatible GPUs | Description |
|---------|----------------|-------------|
| **Basic GPU Access** | All NVIDIA GPUs | Standard `nvidia.com/gpu` resource |
| **Time-Slicing** | All CUDA architectures | Share GPU among multiple workloads |
| **MIG (Multi-Instance GPU)** | GB200, B200, H200, H100, A100, RTX PRO 6000 | Hardware-level GPU partitioning |
| **vGPU** | Data center GPUs | Virtual GPU instances |

**Key Point**: Basic GPU access (what we're using) works universally across all NVIDIA GPUs.

### 5. 2025 Best Practices

**Recommended Approach** (from November 2025 research):

1. **Use NVIDIA GPU Operator** (for production environments)
   - Automates driver, runtime, and device plugin deployment
   - Handles updates and configuration management
   - Supports mixed GPU environments

2. **Or use Device Plugin directly** (simpler, our current approach)
   - Install NVIDIA Container Toolkit
   - Deploy Device Plugin DaemonSet
   - Works consistently across all GPU models

3. **Universal deployment pattern**:
   ```yaml
   runtimeClassName: nvidia
   resources:
     requests:
       nvidia.com/gpu: "1"
   ```

4. **For heterogeneous clusters**: Use node labels/selectors, not different app versions

### 6. Driver and Compatibility Requirements

**What you DO need to ensure**:
- ✅ NVIDIA driver version compatible with GPU hardware
- ✅ CUDA toolkit version compatible with application requirements
- ✅ NVIDIA Container Toolkit installed
- ✅ RuntimeClass configured

**What you DON'T need**:
- ❌ Different application Docker images for different GPUs
- ❌ Different Kubernetes manifests for different GPUs
- ❌ GPU-specific resource names

### 7. Practical Example: Our O-RAN Setup

**Our Hardware**: RTX 3060

**What works**:
```yaml
# This deployment works on RTX 3060, Tesla T4, A100, H100, etc.
spec:
  nodeSelector:
    nvidia.com/gpu: "true"  # Generic: "has GPU"
  tolerations:
  - key: nvidia.com/gpu
    operator: Exists
  runtimeClassName: nvidia
  containers:
  - image: tensorflow/tensorflow:latest-gpu
    resources:
      requests:
        nvidia.com/gpu: "1"
```

**TensorFlow/PyTorch behavior**:
- Automatically detects RTX 3060 (or any NVIDIA GPU)
- Uses CUDA cores available on that GPU
- No code changes needed for different GPU models

### 8. Latest Innovation (November 2025)

**ComputeDomains**: NVIDIA's new feature for NVLink-connected GPUs
- Built into Dynamic Resource Allocation (DRA) driver
- Gives Kubernetes awareness of NVLink topology
- For advanced multi-GPU setups (future consideration)

## Conclusion for O-RAN RIC Platform

### Answer to Original Question

**不需要多個版本！** (No need for multiple versions!)

Our current implementation is **already GPU-agnostic**:
- Same Docker image works on any NVIDIA GPU
- Same deployment YAML works on any NVIDIA GPU
- Smart detection only needs to check: "Is there any GPU?" (yes/no)

### Implementation Recommendation

**Smart GPU Detection Logic** should:
1. Check if node has `nvidia.com/gpu` resource (yes/no)
2. If yes: Deploy GPU version (deployment-gpu.yaml)
3. If no: Deploy CPU version (deployment.yaml)

**No need to**:
- Detect specific GPU model
- Maintain multiple GPU-specific versions
- Check GPU architecture

### Testing Verified

Our setup with RTX 3060 works with:
- Standard TensorFlow GPU image
- Generic `nvidia.com/gpu: "1"` resource request
- Standard nvidia RuntimeClass

This same configuration will work on Tesla T4, V100, A100, H100, etc. without modification.

## References

1. NVIDIA k8s-device-plugin: https://github.com/NVIDIA/k8s-device-plugin
2. NVIDIA GPU Operator (2025): https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/
3. Kubernetes GPU Resource Management Best Practices (2025): Collabnix
4. Time-Slicing GPUs in Kubernetes: NVIDIA Documentation
5. Multi-Instance GPU Support: NVIDIA Technical Blog

**Research Date**: November 2025
**Platform Tested**: O-RAN RIC Platform with RTX 3060
**Conclusion**: Unified approach works across all NVIDIA GPU models
