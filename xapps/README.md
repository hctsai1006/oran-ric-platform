# O-RAN xApp Bundle for RIC Platform

## Overview
This bundle contains four O-RAN Release J compliant xApps designed for deployment on the Near-RT RIC platform:

1. **KPIMON** - KPI Monitoring xApp
2. **QoE Predictor** - Quality of Experience Prediction xApp  
3. **RAN Control** - RAN Control and Optimization xApp
4. **Federated Learning** - Distributed ML Training xApp

## xApp Specifications

All xApps are built according to:
- O-RAN Release J specifications (November 2025)
- E2AP v3.0 protocol
- E2SM-KPM v3.0 for performance monitoring
- E2SM-RC v2.0 for RAN control
- E2SM-CCC v1.0 for cell configuration
- Python xApp framework (xapp-frame-py) 

## Architecture

Each xApp follows the standard O-RAN architecture:
- Subscribes to E2 nodes via E2AP
- Processes RIC indications in near-real-time
- Sends control messages via E2SM-RC
- Exposes REST APIs for configuration
- Integrates with A1 policy management

## Directory Structure

```
xapps-bundle/
├── kpimon/                 # KPI Monitoring xApp
│   ├── src/               # Source code
│   ├── config/            # Configuration files
│   ├── tests/             # Unit tests
│   ├── Dockerfile         # Container image
│   └── helm/              # Helm charts
├── qoe-predictor/         # QoE Prediction xApp
│   ├── src/              
│   ├── config/           
│   ├── models/            # ML models
│   ├── tests/            
│   ├── Dockerfile        
│   └── helm/             
├── ran-control/           # RAN Control xApp
│   ├── src/              
│   ├── config/           
│   ├── policies/          # A1 policy definitions
│   ├── tests/            
│   ├── Dockerfile        
│   └── helm/             
├── federated-learning/    # Federated Learning xApp
│   ├── src/              
│   ├── config/           
│   ├── models/            # FL models
│   ├── aggregator/        # FL aggregation logic
│   ├── tests/            
│   ├── Dockerfile        
│   └── helm/             
└── scripts/               # Deployment scripts
    ├── deploy-all.sh
    ├── onboard-xapps.sh
    └── test-integration.sh
```

## Quick Start

1. **Prerequisites**
   - Kubernetes cluster with O-RAN RIC platform deployed
   - Docker registry accessible from cluster
   - Helm 3.x installed

2. **Build xApps**
   ```bash
   ./scripts/build-all.sh
   ```

3. **Onboard to RIC Platform**
   ```bash
   ./scripts/onboard-xapps.sh
   ```

4. **Deploy xApps**
   ```bash
   ./scripts/deploy-all.sh
   ```

## Testing

Run integration tests:
```bash
./scripts/test-integration.sh
```

## Release Notes

- Version: 1.0.0
- Release Date: November 2025
- O-RAN Compliance: Release J
- Platform Compatibility: OSC RIC L-Release

## License

Apache License 2.0
