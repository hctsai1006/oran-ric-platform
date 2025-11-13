# O-RAN RIC Platform Deployment Project

## Project Overview
This project deploys O-RAN Software Community's Near-RT RIC J Release with production-ready xApps optimized for Claude Code CLI workflows.

## Architecture Overview
- **Platform**: Near-RT RIC J Release (O-RAN SC v4.0)  
- **Deployment**: Local k3s cluster (3-node configuration recommended)
- **xApps**: Traffic Steering, KPIMON, QoE Predictor, RC, Federated Learning
- **Interfaces**: E2 (southbound to RAN), A1 (northbound to Non-RT RIC), O1 (management)

## Key Commands and Workflows

### Cluster Management
```bash
# Start k3s cluster
sudo k3s server --write-kubeconfig-mode 644 --disable traefik --disable servicelb

# Install Cilium CNI
helm install cilium cilium/cilium --namespace kube-system --set operator.replicas=1
```

### RIC Platform Deployment
```bash
# Add O-RAN SC Helm repository
helm repo add ric https://gerrit.o-ran-sc.org/r/ric-plt/ric-dep

# Install RIC Platform
helm install ric-platform ric/ric-platform \
  -n ricplt --create-namespace \
  -f platform/values/local.yaml
```

### xApp Onboarding
```bash
# Onboard xApp
dms_cli onboard \
  --config_file_path=./xapps/traffic-steering/config.json \
  --schema_file_path=./xapps/traffic-steering/schema.json

# Install xApp
dms_cli install --xapp_chart_name=traffic-steering --namespace=ricxapp
```

## Development Conventions

### RMR Message Types
- 12010: RIC_SUB_REQ (Subscription Request)
- 12011: RIC_SUB_RESP (Subscription Response)
- 12050: RIC_INDICATION (E2 Indication)
- 12040: RIC_CONTROL_REQ (Control Request)

## Security Requirements

### Pod Security Standards
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
```

## Performance Targets
- E2 indication processing: < 10ms
- Control command latency: < 100ms  
- xApp startup time: < 30s
- RMR message throughput: > 10K msg/sec

## MCP Server Configuration
- **kubernetes-mcp-server**: Cluster management
- **docker-mcp-server**: Container operations
- **github-mcp-server**: Repository management
