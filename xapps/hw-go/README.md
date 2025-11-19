# HelloWorld (hw-go) xApp for O-RAN SC

## Overview
HelloWorld is a basic example xApp from O-RAN Software Community that demonstrates the fundamental capabilities of the Near-RT RIC platform:
- A1 interface integration
- E2 interface operations
- Database (SDL/Redis) operations
- RMR messaging
- Health monitoring

This xApp serves as a platform validation tool and reference implementation for O-RAN SC J-Release.

## Quick Start

### Deploy
```bash
# Deploy all components
kubectl apply -f deploy/

# Or deploy individually
kubectl apply -f deploy/configmap.yaml
kubectl apply -f deploy/service.yaml
kubectl apply -f deploy/deployment.yaml
```

### Verify
```bash
# Check pod status
kubectl get pods -n ricxapp -l app=hw-go

# View logs
kubectl logs -n ricxapp -l app=hw-go -f

# Check health
kubectl exec -n ricxapp deployment/hw-go -- wget -qO- http://localhost:8080/ric/v1/health/alive
```

### Access Metrics
```bash
# Port forward
kubectl port-forward -n ricxapp deployment/hw-go 8080:8080

# View metrics
curl http://localhost:8080/ric/v1/metrics
```

## Configuration

### Docker Image
- **Registry:** nexus3.o-ran-sc.org:10002
- **Image:** o-ran-sc/ric-app-hw-go:1.1.2
- **Source:** https://gerrit.o-ran-sc.org/r/ric-app/hw-go

### Ports
- **8080/TCP:** HTTP API and metrics
- **4560/TCP:** RMR data port
- **4561/TCP:** RMR route port

### Environment Variables
| Variable | Value | Description |
|----------|-------|-------------|
| RMR_SEED_RT | /app/config/rmr-routes.txt | RMR routing table |
| RMR_SRC_ID | hw-go | RMR source identifier |
| RMR_RTG_SVC | service-ricplt-rtmgr-rmr.ricplt:4561 | Routing Manager |
| DBAAS_SERVICE_HOST | service-ricplt-dbaas-tcp.ricplt | Redis host |
| DBAAS_SERVICE_PORT | 6379 | Redis port |
| LOG_LEVEL | INFO | Logging level |

## Architecture

### RMR Message Types

#### Transmit (TX)
- **12010:** RIC_SUB_REQ - Subscription Request
- **12012:** RIC_SUB_DEL_REQ - Subscription Delete Request

#### Receive (RX)
- **12011:** RIC_SUB_RESP - Subscription Response
- **12013:** RIC_SUB_DEL_RESP - Subscription Delete Response
- **12050:** RIC_INDICATION - RIC Indication Messages

### Platform Integration
```
HelloWorld xApp
    |
    +-- RMR --> E2 Termination (service-ricplt-e2term-rmr:4560)
    +-- RMR --> Routing Manager (service-ricplt-rtmgr-rmr:4561)
    +-- SDL --> Redis (service-ricplt-dbaas-tcp:6379)
```

## Health Endpoints

### Liveness
```
GET /ric/v1/health/alive
```
Returns 200 OK if xApp is running

### Readiness
```
GET /ric/v1/health/ready
```
Returns 200 OK if xApp is ready to serve

### Metrics
```
GET /ric/v1/metrics
```
Returns Prometheus format metrics

## Metrics Exposed

### RMR Metrics
- `ricxapp_RMR_Transmitted` - Total RMR messages sent
- `ricxapp_RMR_Received` - Total RMR messages received
- `ricxapp_RMR_TransmitError` - RMR transmission errors
- `ricxapp_RMR_ReceiveError` - RMR receive errors

### SDL Metrics
- `ricxapp_SDL_Stored` - SDL store operations
- `ricxapp_SDL_StoreError` - SDL store errors

### xApp Metrics
- `ricxapp_hw_go_RICIndicationRx` - RIC Indication messages received

### Go Runtime Metrics
- Standard Go runtime metrics (goroutines, memory, GC, etc.)

## Resource Requirements

### Default Allocation
```yaml
Resources:
  Requests:
    CPU: 100m
    Memory: 128Mi
  Limits:
    CPU: 500m
    Memory: 512Mi
```

### Typical Usage
- **CPU:** ~50m (idle), up to 200m (active)
- **Memory:** ~100Mi (stable)
- **Goroutines:** ~17

## Troubleshooting

### Pod Not Starting
```bash
# Check pod events
kubectl describe pod -n ricxapp -l app=hw-go

# Check image pull
kubectl get events -n ricxapp --field-selector involvedObject.kind=Pod
```

### Connection Issues
```bash
# Verify platform services
kubectl get svc -n ricplt

# Check RMR connectivity
kubectl logs -n ricxapp -l app=hw-go | grep RMR

# Check Redis connectivity
kubectl logs -n ricxapp -l app=hw-go | grep -i redis
```

### Health Check Failures
```bash
# Test endpoints directly
kubectl exec -n ricxapp deployment/hw-go -- wget -qO- http://localhost:8080/ric/v1/health/alive
kubectl exec -n ricxapp deployment/hw-go -- wget -qO- http://localhost:8080/ric/v1/health/ready
```

## Common Tasks

### Scale Replicas
```bash
kubectl scale deployment hw-go -n ricxapp --replicas=2
```

### Update Configuration
```bash
# Edit ConfigMap
kubectl edit configmap hw-go-config -n ricxapp

# Restart to apply
kubectl rollout restart deployment/hw-go -n ricxapp
```

### View Detailed Logs
```bash
# All logs
kubectl logs -n ricxapp deployment/hw-go --tail=100

# Follow logs
kubectl logs -n ricxapp deployment/hw-go -f

# Filter by level
kubectl logs -n ricxapp deployment/hw-go | grep ERROR
```

### Cleanup
```bash
# Delete all resources
kubectl delete -f deploy/

# Or delete individually
kubectl delete deployment hw-go -n ricxapp
kubectl delete service hw-go-http hw-go-rmr -n ricxapp
kubectl delete configmap hw-go-config -n ricxapp
```

## Files

### Directory Structure
```
hw-go/
├── README.md           # This file
├── config/
│   └── config.json    # xApp descriptor
└── deploy/
    ├── configmap.yaml # Configuration and routing
    ├── service.yaml   # Kubernetes services
    └── deployment.yaml # Deployment manifest
```

## References

- [O-RAN SC hw-go Documentation](https://docs.o-ran-sc.org/projects/o-ran-sc-ric-app-hw-go/en/latest/)
- [O-RAN SC Gerrit Repository](https://gerrit.o-ran-sc.org/r/ric-app/hw-go)
- [O-RAN SC Wiki - HelloWorld xApps](https://wiki.o-ran-sc.org/display/RICA/HelloWorld+demo+xApps)
- [O-RAN Alliance Specifications](https://www.o-ran.org/specifications)

## Version Information

- **xApp Version:** 1.1.2
- **O-RAN Release:** J-Release
- **RMR Version:** 4.7.0
- **Go Version:** go1.16.4
- **Deployment Date:** 2025-11-19

## License

Apache License 2.0 - See [O-RAN SC License](https://www.o-ran-sc.org/legal)
