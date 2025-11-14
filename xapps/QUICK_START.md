# O-RAN xApps Bundle - Quick Start Guide

## 📦 Package Contents

This package contains four O-RAN Release J compliant xApps:

### 1. **KPIMON (KPI Monitoring)**
- **Purpose**: Collects and monitors network KPIs in real-time
- **Features**:
  - E2SM-KPM v3.0 support for performance measurement
  - Real-time anomaly detection
  - InfluxDB integration for time-series storage
  - Prometheus metrics export
  - 20+ KPI types supported

### 2. **QoE Predictor**
- **Purpose**: Predicts user Quality of Experience using ML models
- **Features**:
  - Deep learning models for video/gaming QoE
  - Random Forest for voice quality prediction
  - Real-time inference engine
  - QoE degradation detection and alerts
  - A1 policy integration

### 3. **RAN Control**
- **Purpose**: Executes RAN control actions for optimization
- **Features**:
  - E2SM-RC v2.0 compliant control actions
  - Handover optimization
  - Resource allocation control
  - Load balancing
  - Network slice management
  - Power control optimization

### 4. **Federated Learning**
- **Purpose**: Coordinates distributed ML training across RAN nodes
- **Features**:
  - FedAvg, FedProx, SCAFFOLD aggregation methods
  - Differential privacy support
  - Secure aggregation
  - Model compression
  - Multi-model support (TensorFlow & PyTorch)

## 🚀 Installation Steps

### Prerequisites
- Kubernetes cluster with O-RAN RIC platform deployed
- Docker registry accessible from cluster
- kubectl configured to access the cluster
- Helm 3.x installed

### Step 1: Extract the Package
```bash
tar -xzf oran-xapps-release-j.tar.gz
cd xapps-bundle
```

### Step 2: Build Docker Images
```bash
# Set your Docker registry (default: localhost:5000)
export REGISTRY=your-registry.com:5000
export TAG=1.0.0

# Build all xApp images
./scripts/build-all.sh
```

### Step 3: Onboard xApps to RIC
```bash
# Set RIC AppMgr URL
export APPMGR_URL=http://service-ricplt-appmgr-http.ricplt:8080
export NAMESPACE=ricxapp

# Onboard all xApps
./scripts/onboard-xapps.sh
```

### Step 4: Deploy xApps
```bash
# Deploy all xApps to the RIC platform
./scripts/deploy-all.sh
```

### Step 5: Verify Deployment
```bash
# Check pod status
kubectl get pods -n ricxapp

# Run integration tests
./scripts/test-integration.sh
```

## 📊 Monitoring & Management

### Access xApp APIs
Each xApp exposes a REST API for monitoring and management:

```bash
# Port forward to access APIs locally
kubectl port-forward -n ricxapp deployment/kpimon 8080:8080
kubectl port-forward -n ricxapp deployment/qoe-predictor 8090:8090
kubectl port-forward -n ricxapp deployment/ran-control 8100:8100
kubectl port-forward -n ricxapp deployment/federated-learning 8110:8110
```

### API Endpoints
- **KPIMON**: http://localhost:8080
  - `/metrics` - Prometheus metrics
  - `/health/alive` - Liveness check
  - `/health/ready` - Readiness check

- **QoE Predictor**: http://localhost:8090
  - `/predict/<ue_id>` - Get QoE prediction
  - `/metrics` - Aggregated metrics

- **RAN Control**: http://localhost:8100
  - `/control/trigger` - Trigger control action
  - `/control/status/<action_id>` - Check action status
  - `/network/state` - Get network state

- **Federated Learning**: http://localhost:8110
  - `/fl/status` - FL training status
  - `/fl/clients` - List FL clients
  - `/fl/history` - Training history

### View Logs
```bash
kubectl logs -n ricxapp deployment/kpimon
kubectl logs -n ricxapp deployment/qoe-predictor
kubectl logs -n ricxapp deployment/ran-control
kubectl logs -n ricxapp deployment/federated-learning
```

## 🔧 Configuration

Each xApp can be configured through its ConfigMap:

```bash
# Edit configuration
kubectl edit configmap kpimon-config -n ricxapp
kubectl edit configmap qoe-predictor-config -n ricxapp
kubectl edit configmap ran-control-config -n ricxapp
kubectl edit configmap federated-learning-config -n ricxapp

# Restart to apply changes
kubectl rollout restart deployment/<xapp-name> -n ricxapp
```

## 📈 Performance Tuning

### Resource Allocation
Adjust resource limits in deployment manifests:
```yaml
resources:
  requests:
    cpu: "500m"
    memory: "1Gi"
  limits:
    cpu: "2000m"
    memory: "2Gi"
```

### Scaling
```bash
# Scale xApp replicas
kubectl scale deployment kpimon -n ricxapp --replicas=3
```

## 🐛 Troubleshooting

### Common Issues

1. **Pod CrashLoopBackOff**
   - Check logs: `kubectl logs -n ricxapp <pod-name>`
   - Verify RMR connectivity to E2Term
   - Check Redis/InfluxDB availability

2. **ImagePullBackOff**
   - Verify Docker registry is accessible
   - Check image name and tag

3. **No E2 Subscriptions**
   - Verify E2Term is running
   - Check RMR routing configuration
   - Ensure E2 nodes are connected

4. **Redis Connection Failed**
   - Verify Redis service is running: `kubectl get svc -n ricplt redis-service`
   - Check network policies

## 📝 O-RAN Release J Compliance

This implementation follows O-RAN Alliance Release J specifications:
- E2AP v3.0 - E2 Application Protocol
- E2SM-KPM v3.0 - Key Performance Measurement
- E2SM-RC v2.0 - RAN Control
- E2SM-CCC v1.0 - Cell Configuration and Control
- A1AP v3.0 - A1 Application Protocol

## 🔒 Security Features

- **Secure Communication**: TLS/mTLS support for E2 and A1 interfaces
- **Authentication**: Service account and RBAC integration
- **Differential Privacy**: Privacy-preserving federated learning
- **Secure Aggregation**: Encrypted gradient aggregation
- **Network Policies**: Restricted pod-to-pod communication

## 📚 Additional Resources

- [O-RAN Alliance Specifications](https://www.o-ran.org/specifications)
- [O-RAN Software Community](https://wiki.o-ran-sc.org)
- [Near-RT RIC Documentation](https://docs.o-ran-sc.org/projects/o-ran-sc-ric-plt-ric-dep)

## 💡 Tips

1. **Monitor Resource Usage**:
   ```bash
   kubectl top pods -n ricxapp
   ```

2. **Enable Debug Logging**:
   Edit ConfigMap and set `logging.level: "DEBUG"`

3. **Backup Configurations**:
   ```bash
   kubectl get configmap -n ricxapp -o yaml > configs-backup.yaml
   ```

4. **Health Monitoring**:
   Set up Prometheus/Grafana for comprehensive monitoring

## 🤝 Support

For issues or questions:
- Check logs first: `kubectl logs -n ricxapp <pod-name>`
- Review integration test results: `./scripts/test-integration.sh`
- Verify RIC platform status: `kubectl get pods -n ricplt`

---
**Version**: 1.0.0  
**Release Date**: November 2025  
**O-RAN Compliance**: Release J
