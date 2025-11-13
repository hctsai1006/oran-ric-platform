# O-RAN RIC Platform - Claude Code Optimized Deployment

[![O-RAN SC J Release](https://img.shields.io/badge/O--RAN%20SC-J%20Release-blue)](https://o-ran-sc.org)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Optimized-purple)](https://claude.ai)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.28+-326ce5)](https://kubernetes.io)
[![License](https://img.shields.io/badge/License-Apache%202.0-green)](LICENSE)

## 🚀 Quick Start

This project provides a production-ready O-RAN Near-RT RIC Platform (J Release) optimized for local development with Claude Code CLI.

### Prerequisites

- **System**: Ubuntu 22.04+ or macOS 13+
- **Resources**: 8 vCPU, 16GB RAM, 50GB storage
- **Tools**: Claude Code CLI, Docker, kubectl, helm

### One-Command Deployment

```bash
# Clone and setup
git clone https://github.com/your-org/oran-ric-platform
cd oran-ric-platform

# Deploy everything
./scripts/deploy.sh --env local --cluster k3s
```

### Verify Installation

```bash
# Check RIC platform
kubectl get pods -n ricplt

# Check xApps
kubectl get pods -n ricxapp

# Access dashboard
open http://localhost:3000  # Grafana
```

## 📚 Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Installation Guide](docs/INSTALLATION.md)
- [xApp Development](docs/XAPP_DEVELOPMENT.md)
- [Claude Code Integration](docs/CLAUDE_INTEGRATION.md)
- [Security Guide](docs/SECURITY.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## 🏗️ Project Structure

```
.
├── .claude/           # Claude Code configuration
├── infrastructure/    # Kubernetes and cloud configs
├── platform/         # RIC platform components
├── xapps/           # xApp implementations
├── observability/   # Monitoring stack
├── scripts/         # Automation scripts
└── tests/          # Test suites
```

## 🤖 Claude Code Features

This project is optimized for Claude Code CLI with:

- **CLAUDE.md**: Comprehensive project memory
- **MCP Servers**: Kubernetes, Docker, GitHub integrations
- **Custom Commands**: Slash commands for common operations
- **Skills**: Pre-configured deployment and troubleshooting skills

## 🛠️ Supported xApps

- **Traffic Steering**: Dynamic load balancing
- **KPIMON**: KPI monitoring and collection
- **QoE Predictor**: ML-based QoE prediction
- **RAN Control**: E2SM-RC abstraction layer
- **Federated Learning**: Distributed AI/ML training

## 📊 Monitoring

Access dashboards after deployment:

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686

## 🔒 Security

- mTLS via Linkerd service mesh
- RBAC with least privilege
- Network segmentation with Cilium
- Automated certificate management

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## 📝 License

Apache License 2.0 - See [LICENSE](LICENSE)

## 🆘 Support

- [Documentation](https://docs.o-ran-sc.org)
- [Community Slack](https://o-ran-sc.slack.com)
- [Issue Tracker](https://github.com/your-org/oran-ric-platform/issues)

## Maintainers

- Your Team (@yourteam)
- Contact: oran-support@yourcompany.com

---
*Built with ❤️ for the O-RAN community*
