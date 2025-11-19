# O-RAN Near-RT RIC Platform with Production xApps

<div align="center">

[![Version](https://img.shields.io/badge/version-v2.0.1-blue)](https://github.com/thc1006/oran-ric-platform/releases/tag/v2.0.1)
[![O-RAN SC](https://img.shields.io/badge/O--RAN%20SC-J%20Release-orange)](https://o-ran-sc.org)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.28+-326ce5?logo=kubernetes)](https://kubernetes.io)
[![License](https://img.shields.io/badge/License-Apache%202.0-green)](LICENSE)

[Quick Start](#quick-start) • [Documentation](docs/deployment/) • [E2 Simulator](https://github.com/thc1006/oran-e2-node)

</div>

---

## TLDR

**What**: Production-ready O-RAN Near-RT RIC Platform (J Release) with 5 functional xApps and complete observability stack.

**Includes**: KPIMON, Traffic Steering, QoE Predictor, RAN Control, Federated Learning xApps + Prometheus metrics + Grafana dashboards + E2 traffic simulator.

**For**: 5G RAN testing without physical equipment, xApp development, performance benchmarking, educational deployments, CI/CD integration.

**Deploy**: Clone → Run deployment script → Access Grafana (15 minutes).

**New in v2.0.1**: KUBECONFIG standardization with automatic multi-cluster support, improved deployment scripts reliability.

**Previous (v2.0.0)**: E2 Node extracted to [separate repo](https://github.com/thc1006/oran-e2-node), complete metrics integration, 7 alert rule groups, automated testing.

---

## Wednesday 一鍵部署（生產就緒版）

> ** 新功能**: 整合 Phase 0 緊急修復的安全部署腳本，包含 Redis 持久化、密碼加密、自動備份機制。

### 快速開始（5 步驟，45 分鐘）

```bash
# 1. 前置檢查（2 分鐘）
kubectl get nodes # 確認 k3s 運行
free -h # 確認至少 16GB RAM
df -h # 確認至少 50GB 磁碟空間

# 2. 確認映像已構建（如果是首次部署，參考下方"建置映像"）
curl -s http://localhost:5000/v2/_catalog | python3 -m json.tool

# 3. 執行一鍵部署（40-60 分鐘）
sudo bash scripts/wednesday-safe-deploy.sh

# 4. 訪問 Grafana（1 分鐘）
# 腳本執行完成後會顯示密碼和訪問方式
# 或手動執行：
kubectl port-forward -n ricplt svc/grafana 3000:80

# 5. 驗證部署（2 分鐘）
kubectl get pods -A | grep -E 'ricplt|ricxapp'
```

### 部署腳本功能亮點

**wednesday-safe-deploy.sh** 自動執行以下操作：

 **安全增強**
- 自動生成安全密碼（Grafana、Redis）
- 建立 Kubernetes Secrets
- 移除所有明文密碼配置

 **資料保護**
- 啟用 Redis AOF 持久化（appendonly: yes）
- 配置 RDB 快照（防止資料遺失）
- 建立每日自動備份 CronJob
- 設定 InfluxDB 7 天保留策略

 **完整部署**
- RIC Platform 核心元件
- Prometheus + Grafana 監控堆疊
- 5 個生產級 xApps（KPIMON, TS, QP, RC, FL）
- E2 Simulator（含 FL 配置修正）

 **智慧驗證**
- 部署前系統檢查
- 部署前自動備份
- 部署後完整驗證（7 大類別）
- 生成詳細部署報告

### 首次部署：建置映像

如果是首次部署，需要先建置並推送 Docker 映像到本地 registry：

```bash
# 啟動本地 Docker Registry
docker run -d --restart=always --name registry -p 5000:5000 \
 -v /var/lib/registry:/var/lib/registry registry:2

# 建置所有映像（一行命令）
cd xapps/kpimon-go-xapp && docker build -t localhost:5000/xapp-kpimon:1.0.1 . && docker push localhost:5000/xapp-kpimon:1.0.1 && cd ../.. && \
cd xapps/traffic-steering && docker build -t localhost:5000/xapp-traffic-steering:1.0.2 . && docker push localhost:5000/xapp-traffic-steering:1.0.2 && cd ../.. && \
cd xapps/rc-xapp && docker build -t localhost:5000/xapp-ran-control:1.0.1 . && docker push localhost:5000/xapp-ran-control:1.0.1 && cd ../.. && \
cd xapps/qoe-predictor && docker build -t localhost:5000/xapp-qoe-predictor:1.0.0 . && docker push localhost:5000/xapp-qoe-predictor:1.0.0 && cd ../.. && \
cd xapps/federated-learning && docker build -t localhost:5000/xapp-federated-learning:1.0.0 . && docker push localhost:5000/xapp-federated-learning:1.0.0 && cd ../.. && \
cd simulator/e2-simulator && docker build -t localhost:5000/e2-simulator:1.0.0 . && docker push localhost:5000/e2-simulator:1.0.0 && cd ../..
```

### 部署後驗證清單

腳本執行完成後，執行以下檢查：

```bash
# 1. 檢查所有 Pods 運行
kubectl get pods -A | grep -v Running | grep -v Completed
# 應該沒有輸出（所有 Pods 都正常）

# 2. 檢查 Redis 持久化已啟用
kubectl exec -n ricplt deployment/ricplt-dbaas-server -- redis-cli CONFIG GET appendonly
# 預期輸出: "yes"

# 3. 檢查每日備份 CronJob
kubectl get cronjob -n ricplt
# 應該看到: ric-daily-backup

# 4. 取得 Grafana 密碼
kubectl get secret grafana-admin-secret -n ricplt -o jsonpath='{.data.admin-password}' | base64 -d; echo

# 5. 訪問 Grafana
kubectl port-forward -n ricplt svc/grafana 3000:80
# 瀏覽器開啟: http://localhost:3000
# 帳號: admin / 密碼: 上一步的輸出
```

### 重要文件位置

部署完成後，以下文件包含重要資訊：

```bash
# 部署日誌
/tmp/wednesday-deploy-YYYYMMDD-HHMMSS.log

# 部署報告
/tmp/wednesday-deploy-YYYYMMDD-HHMMSS-report.txt

# 密碼檔案（請立即備份到安全位置！）
/tmp/wednesday-backup-YYYYMMDD-HHMMSS/PASSWORDS.txt

# 備份所有配置
/tmp/wednesday-backup-YYYYMMDD-HHMMSS/
```

### 常見問題排查

**問題 1: kubectl 連線失敗**
```bash
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
# 或
export KUBECONFIG=$HOME/.kube/config
```

**問題 2: Pod 卡在 Pending**
```bash
kubectl describe pod <pod-name> -n <namespace>
kubectl top nodes # 檢查資源使用
```

**問題 3: 映像拉取失敗**
```bash
# 確認本地 registry 運行
docker ps | grep registry

# 確認映像已推送
curl -s http://localhost:5000/v2/_catalog
```

### 技術分析報告

完整的系統分析與 90 天行動計畫，請參考：

- [主執行摘要](docs/reports/project-summary/MASTER_EXECUTIVE_SUMMARY.md) - 5 分鐘了解系統狀況
- [90 天行動計畫](docs/technical-debt/90_DAY_ACTION_PLAN.md) - 完整執行計畫
- [安全審查報告](docs/security/SECURITY_AUDIT_REPORT.md) - 28 個安全漏洞分析
- [效能分析](docs/technical-debt/PERFORMANCE_ANALYSIS.md) - 效能優化建議
- [所有報告索引](docs/reports/project-summary/ANALYSIS_REPORTS_INDEX.md) - 15 份報告導覽
- [完整文檔索引](docs/INDEX.md) - 所有文檔導覽

---

## Table of Contents

**Wednesday 部署（推薦）**
- [ Wednesday 一鍵部署](#-wednesday-一鍵部署生產就緒版) - **生產就緒的安全部署** 

**Getting Started**
- [部署模式選擇](#部署模式選擇) - 選擇適合的部署方式
- [Quick Start](#quick-start) - Deploy in 15 minutes
- [Installation Guide](#installation-guide) - Detailed setup instructions
- [Architecture](#architecture) - System overview

**Components**
- [xApps](#xapps) - Available applications
- [Monitoring](#monitoring--observability) - Metrics and dashboards
- [Testing](#testing) - Validation and E2E tests

**Operations**
- [Documentation](#documentation) - Guides and references
- [What's New](#whats-new-in-v200) - Version 2.0.0 changes
- [Troubleshooting](docs/deployment/TROUBLESHOOTING.md) - Common issues

---

## 部署模式選擇

本專案提供兩種部署模式，請根據使用場景選擇：

### 模式 1: 輕量級部署（推薦）

**使用腳本**: `bash scripts/deployment/deploy-all.sh`

**部署組件**:
- Prometheus（監控系統）
- Grafana（可視化儀表板）
- 5 個生產級 xApps（KPIMON, Traffic Steering, RAN Control, QoE Predictor, Federated Learning）
- E2 Simulator（測試流量產生器）

**適用場景**:
- 開發與測試環境
- xApp 功能開發
- 監控系統展示
- CI/CD 整合測試
- 教學與演示

**優點**:
- ⚡ 快速部署（~15 分鐘）
- 💻 資源需求低（8 核 / 16GB RAM）
- 🔄 獨立運行，不依賴外部 E2 節點
- 完整監控與可視化
- **這是當前推薦的標準部署方式**

**執行方式**:
```bash
# 一鍵部署所有組件
bash scripts/deployment/deploy-all.sh
```

---

### 🏭 模式 2: 完整 RIC Platform（實驗性）

**使用腳本**: `bash scripts/deployment/deploy-ric-platform.sh`

**額外組件**（在輕量級基礎上增加）:
- AppMgr（xApp 生命週期管理）
- E2Mgr（E2 連接管理）
- E2Term（E2 協議終端）
- SubMgr（訂閱管理）
- A1 Mediator（A1 策略介面）
- Redis（共享資料層 SDL）

**適用場景**:
- 生產環境部署
- 真實 E2 節點連接（實體 RAN / CU / DU）
- A1 Policy 完整測試
- RMR 訊息路由驗證
- O-RAN 架構完整驗證

**資源需求**:
- CPU: 16+ 核心
- RAM: 32GB+
- 磁碟: 100GB+

** 重要提示**:
- 此模式標記為 **EXPERIMENTAL**
- 需要額外配置與調整
- 未包含在標準部署流程中
- 適合進階使用者與生產環境準備

**執行方式**:
```bash
# 完整 RIC Platform 部署（實驗性）
bash scripts/deployment/deploy-ric-platform.sh
```

---

## Quick Start

> **Time to deploy**: ~15 minutes | **Difficulty**: Beginner

### Prerequisites Check

| Component | Requirement | Check Command |
|-----------|-------------|---------------|
| OS | Debian 11+/Ubuntu 20.04+ | `lsb_release -a` |
| CPU | 8+ cores | `nproc` |
| RAM | 16GB+ | `free -h` |
| Disk | 100GB+ free | `df -h` |

> **Tested on**: Debian 13, Ubuntu 22.04/24.04 LTS

### Fast Track Deployment

> ** IMPORTANT**: This assumes Docker images are already built. First-time users should follow the [Installation Guide](#installation-guide) instead.

> ** Critical Setup Requirements** (必读！Read First!)
>
> Before starting deployment, ensure these steps are completed:
>
> 1. **KUBECONFIG Configuration** (必须/Required)
> - All `kubectl` and `helm` commands require proper KUBECONFIG setup
> - After k3s installation, configure kubectl access:
> ```bash
> mkdir -p $HOME/.kube
> sudo cp /etc/rancher/k3s/k3s.yaml $HOME/.kube/config
> sudo chown $USER:$USER $HOME/.kube/config
> export KUBECONFIG=$HOME/.kube/config
> echo "export KUBECONFIG=$HOME/.kube/config" >> ~/.bashrc
> source ~/.bashrc
> ```
> - **Verify**: `kubectl get nodes` should show your node
>
> 2. **E2 Simulator Submodule** (必须/Required)
> - E2 Simulator is a git submodule (separate repository)
> - **Must initialize before building images**:
> ```bash
> cd oran-ric-platform
> git submodule update --init --recursive
> ```
> - **Verify**: `ls simulator/e2-simulator/` should show Dockerfile and src/
>
> 3. **GPU Support** (可选/Optional - for Federated Learning GPU)
> - Required only if you want to use GPU-accelerated Federated Learning
> - See [GPU Support Setup](#gpu-support-optional) below
> - CPU version works without GPU setup

#### Step 1: Install Prerequisites (~5 min)

```bash
# Install Docker + Helm + k3s with one script
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker

curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

git clone https://github.com/thc1006/oran-ric-platform.git
cd oran-ric-platform
sudo bash scripts/deployment/setup-k3s.sh

# Configure kubectl access (OPTIONAL - for immediate effect in current shell)
# NOTE: All deployment scripts now automatically detect KUBECONFIG (see v2.0.1)
# If you open a new shell, .bashrc will load KUBECONFIG automatically
export KUBECONFIG=$HOME/.kube/config
source ~/.bashrc

# Create RIC namespaces
kubectl create namespace ricplt
kubectl create namespace ricxapp
kubectl create namespace ricobs

# Start local Docker registry
docker run -d --restart=always --name registry -p 5000:5000 \
 -v /var/lib/registry:/var/lib/registry registry:2
```

**Verify installation:**
```bash
kubectl get nodes # Should show: Ready
helm version # Should show version without errors
kubectl get namespaces | grep -E 'ricplt|ricxapp|ricobs' # Should show all 3 namespaces
docker ps | grep registry # Should show: localhost:5000 running
```

#### Step 2: Initialize E2 Simulator Submodule (~1 min, first-time only)

```bash
# Initialize E2 Simulator git submodule
cd oran-ric-platform
git submodule update --init --recursive

# Verify submodule is initialized
ls simulator/e2-simulator/ # Should show: Dockerfile, src/, deploy/, etc.
```

#### Step 3: Build Images (~10 min, first-time only)

```bash
# Build and push images to local registry (localhost:5000)
cd xapps/kpimon-go-xapp && docker build -t localhost:5000/xapp-kpimon:1.0.1 . && docker push localhost:5000/xapp-kpimon:1.0.1 && cd ../..
cd xapps/traffic-steering && docker build -t localhost:5000/xapp-traffic-steering:1.0.2 . && docker push localhost:5000/xapp-traffic-steering:1.0.2 && cd ../..
cd xapps/rc-xapp && docker build -t localhost:5000/xapp-ran-control:1.0.1 . && docker push localhost:5000/xapp-ran-control:1.0.1 && cd ../..
cd xapps/qoe-predictor && docker build -t localhost:5000/xapp-qoe-predictor:1.0.0 . && docker push localhost:5000/xapp-qoe-predictor:1.0.0 && cd ../..
cd xapps/federated-learning && docker build -t localhost:5000/xapp-federated-learning:1.0.0 . && docker push localhost:5000/xapp-federated-learning:1.0.0 && cd ../..
cd simulator/e2-simulator && docker build -t localhost:5000/e2-simulator:1.0.0 . && docker push localhost:5000/e2-simulator:1.0.0 && cd ../..
```

#### Step 4: Deploy RIC Platform (~8 min)

```bash
# Deploy Prometheus (single-line for easy copy-paste)
helm install r4-infrastructure-prometheus ./ric-dep/helm/infrastructure/subcharts/prometheus --namespace ricplt --values ./config/prometheus-values.yaml

# Deploy Grafana
helm repo add grafana https://grafana.github.io/helm-charts && helm repo update
helm install oran-grafana grafana/grafana -n ricplt -f ./config/grafana-values.yaml

# Deploy xApps
kubectl apply -f ./xapps/kpimon-go-xapp/deploy/ -n ricxapp
kubectl apply -f ./xapps/traffic-steering/deploy/ -n ricxapp
kubectl apply -f ./xapps/rc-xapp/deploy/ -n ricxapp
kubectl apply -f ./xapps/qoe-predictor/deploy/ -n ricxapp
kubectl apply -f ./xapps/federated-learning/deploy/ -n ricxapp

# Deploy E2 traffic simulator
kubectl apply -f ./simulator/e2-simulator/deploy/deployment.yaml -n ricxapp
```

#### Step 5: Access Dashboard (~2 min)

```bash
# Get Grafana password
kubectl get secret -n ricplt oran-grafana -o jsonpath="{.data.admin-password}" | base64 -d; echo

# Start port forwarding (keep terminal open in background or new terminal)
kubectl port-forward -n ricplt svc/oran-grafana 3000:80
```

**In a new terminal, import dashboards:**
```bash
cd oran-ric-platform
bash ./scripts/deployment/import-dashboards.sh
```

**Open browser:** http://localhost:3000 (username: `admin`, password: from above)

### Verify Deployment

```bash
# Check all components are running
kubectl get pods -n ricxapp -o wide
kubectl get pods -n ricplt | grep -E 'grafana|prometheus'
```

**Expected output:**
```
NAME READY STATUS
kpimon-xxxxx 1/1 Running
traffic-steering-xxxxx 1/1 Running
ran-control-xxxxx 1/1 Running
qoe-predictor-xxxxx 1/1 Running
federated-learning-xxxxx 1/1 Running
e2-simulator-xxxxx 1/1 Running
oran-grafana-xxxxx 1/1 Running
r4-infrastructure-prometheus-xxx 1/1 Running
```

### GPU Support (Optional)

> **Note**: GPU support is only needed for GPU-accelerated Federated Learning. The CPU version (`federated-learning`) works without GPU setup.

If you have NVIDIA GPU and want to enable GPU-accelerated training:

**Prerequisites:**
- NVIDIA GPU (tested with RTX 3060)
- NVIDIA drivers installed (`nvidia-smi` command available)
- CUDA toolkit (optional, for development)

**Setup GPU Support:**

```bash
# Run the GPU setup script
cd oran-ric-platform
sudo bash scripts/setup-gpu-support.sh
```

This script will:
1. Install NVIDIA Device Plugin for Kubernetes
2. Label nodes with `nvidia.com/gpu=true`
3. Verify GPU resources are available

**Verify GPU Pod Scheduling:**

```bash
# Check if GPU pod is now running (not Pending)
kubectl get pods -n ricxapp -l version=v1.0.0-gpu

# Check GPU usage inside pod
GPU_POD=$(kubectl get pod -n ricxapp -l version=v1.0.0-gpu -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n ricxapp $GPU_POD -- nvidia-smi
```

**Troubleshooting:**
- If pod still Pending: `kubectl describe pod -n ricxapp -l version=v1.0.0-gpu`
- Check NVIDIA Device Plugin: `kubectl get pods -n kube-system -l name=nvidia-device-plugin-ds`
- Verify node has GPU: `kubectl get nodes -o=custom-columns=NAME:.metadata.name,GPU:.status.capacity.'nvidia\.com/gpu'`

> **Next Steps:**
> - View metrics in Grafana dashboards
> - Check [WORKING_DEPLOYMENT_GUIDE.md](docs/deployment/WORKING_DEPLOYMENT_GUIDE.md) for detailed walkthrough
> - If issues occur: [TROUBLESHOOTING.md](docs/deployment/TROUBLESHOOTING.md)

---

## Architecture

```
┌─────────────────┐
│ E2 Simulator │ ← Generates realistic E2 traffic
└────────┬────────┘
 │ HTTP POST /e2/indication
 ├──────────────────┬──────────────┬─────────────┬─────────────┐
 ↓ ↓ ↓ ↓ ↓
 KPIMON Traffic Steering QoE Predictor RAN Control Fed Learning
 :8081/:8080 :8081/:8080 :8090/:8080 :8100/:8080 :8110/:8080
 │ │ │ │ │
 └──────────────────┴────────────────┴─────────────┴─────────────┘
 │
 Prometheus :9090 ← Scrapes metrics every 30s
 │
 Grafana :3000 ← Visualizes metrics
```

**Port Convention:**
- `8081/8090/8100/8110`: xApp business logic (E2 indications)
- `8080`: Prometheus metrics endpoint (all xApps)

---

## Installation Guide

> For users who need detailed control over the installation process or want to understand each component.

### System Preparation

#### 1. Install Docker

**Quick method:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

**Manual method (Debian/Ubuntu):**
```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings

# Download Docker GPG key (works for both Debian and Ubuntu)
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add Docker repository (auto-detects Debian/Ubuntu)
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io
```

> **Note**: This method works for both Debian and Ubuntu. Docker repository auto-detects your distribution.

#### 2. Install Helm

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version # Verify installation
```

#### 3. Install and Configure k3s

**Automated (recommended):**
```bash
git clone https://github.com/thc1006/oran-ric-platform.git
cd oran-ric-platform
sudo bash scripts/deployment/setup-k3s.sh

# Configure kubectl access (OPTIONAL - for immediate effect in current shell)
# NOTE: setup-k3s.sh already configures this and writes to .bashrc
# All deployment scripts (v2.0.1+) automatically detect KUBECONFIG
# If you open a new shell, .bashrc will load KUBECONFIG automatically
mkdir -p $HOME/.kube
sudo cp /etc/rancher/k3s/k3s.yaml $HOME/.kube/config
sudo chown $USER:$USER $HOME/.kube/config
export KUBECONFIG=$HOME/.kube/config
echo "export KUBECONFIG=$HOME/.kube/config" >> ~/.bashrc
source ~/.bashrc

# Create RIC namespaces
kubectl create namespace ricplt
kubectl create namespace ricxapp
kubectl create namespace ricobs

# Verify
kubectl get namespaces | grep -E 'ricplt|ricxapp|ricobs'
```

**Manual:**
```bash
# Install k3s
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=v1.28.5+k3s1 sh -s - server \
 --write-kubeconfig-mode 644 \
 --disable traefik \
 --disable servicelb

# Configure kubectl access (OPTIONAL - for immediate effect in current shell)
# NOTE: All deployment scripts (v2.0.1+) automatically detect KUBECONFIG
# If you open a new shell, .bashrc will load KUBECONFIG automatically
mkdir -p $HOME/.kube
sudo cp /etc/rancher/k3s/k3s.yaml $HOME/.kube/config
sudo chown $USER:$USER $HOME/.kube/config
export KUBECONFIG=$HOME/.kube/config
echo "export KUBECONFIG=$HOME/.kube/config" >> ~/.bashrc
source ~/.bashrc

# Verify cluster access
kubectl cluster-info
helm version # Both should work without errors

# Create RIC namespaces
kubectl create namespace ricplt
kubectl create namespace ricxapp
kubectl create namespace ricobs
```

### KUBECONFIG Configuration

> **New in v2.0.1**: All deployment scripts now use standardized KUBECONFIG handling with automatic detection and multi-cluster support.

#### Automatic KUBECONFIG Setup

All deployment scripts (`scripts/deployment/*.sh`, `scripts/*.sh`) automatically configure KUBECONFIG using a **three-level priority mechanism**:

```bash
Priority 1: Existing environment variable (if set and file exists)
Priority 2: Standard location (~/.kube/config)
Priority 3: k3s default location (/etc/rancher/k3s/k3s.yaml)
```

**What this means:**
- **Multi-cluster support**: If you already have `KUBECONFIG` set, all scripts will respect it
- **Standard compliance**: Scripts prefer `~/.kube/config` (Kubernetes standard)
- **k3s fallback**: Automatic detection of k3s installations
- **No manual configuration needed**: Scripts handle everything automatically

#### Usage Examples

**Scenario 1: Single cluster (default)**
```bash
# After setup-k3s.sh, KUBECONFIG is automatically configured
# All deployment scripts will work without any additional configuration
bash scripts/deployment/deploy-prometheus.sh
bash scripts/deployment/deploy-grafana.sh
```

**Scenario 2: Multi-cluster environment**
```bash
# Set KUBECONFIG to your preferred cluster
export KUBECONFIG=/path/to/cluster-a/kubeconfig

# All scripts will use cluster-a
bash scripts/deployment/deploy-prometheus.sh # Deploys to cluster-a

# Switch to another cluster
export KUBECONFIG=/path/to/cluster-b/kubeconfig
bash scripts/deployment/deploy-grafana.sh # Deploys to cluster-b
```

**Scenario 3: Manual configuration (if needed)**
```bash
# If automatic detection fails, manually set KUBECONFIG
export KUBECONFIG=$HOME/.kube/config

# Make it permanent
echo "export KUBECONFIG=$HOME/.kube/config" >> ~/.bashrc
source ~/.bashrc
```

#### Verification

Check which cluster your scripts will use:
```bash
# Show current KUBECONFIG
echo $KUBECONFIG

# Verify cluster access
kubectl cluster-info

# List available contexts (multi-cluster)
kubectl config get-contexts
```

#### Troubleshooting

If deployment scripts fail with KUBECONFIG errors:

```bash
# Check if KUBECONFIG file exists
ls -l $KUBECONFIG

# Verify file permissions (must be readable)
chmod 600 $KUBECONFIG

# Test kubectl connectivity
kubectl get nodes

# If k3s is installed but KUBECONFIG not found:
mkdir -p $HOME/.kube
sudo cp /etc/rancher/k3s/k3s.yaml $HOME/.kube/config
sudo chown $USER:$USER $HOME/.kube/config
export KUBECONFIG=$HOME/.kube/config
```

**Reference:** [PR #9 KUBECONFIG Standardization Report](docs/testing/PR9-FINAL-REPORT.md)

### Build Container Images

> **IMPORTANT**: Before deploying xApps, you must build and push images to the local registry.

#### Setup Local Docker Registry

```bash
# Start local registry (if not already running)
docker run -d --restart=always --name registry -p 5000:5000 \
 -v /var/lib/registry:/var/lib/registry \
 registry:2

# Verify registry is running
curl -s http://localhost:5000/v2/_catalog
```

#### Build xApp Images

```bash
cd /home/thc1006/oran-ric-platform

# Build KPIMON
cd xapps/kpimon-go-xapp
docker build -t localhost:5000/xapp-kpimon:1.0.1 .
docker push localhost:5000/xapp-kpimon:1.0.1

# Build Traffic Steering
cd ../traffic-steering
docker build -t localhost:5000/xapp-traffic-steering:1.0.2 .
docker push localhost:5000/xapp-traffic-steering:1.0.2

# Build RAN Control
cd ../rc-xapp
docker build -t localhost:5000/xapp-ran-control:1.0.1 .
docker push localhost:5000/xapp-ran-control:1.0.1

# Build QoE Predictor
cd ../qoe-predictor
docker build -t localhost:5000/xapp-qoe-predictor:1.0.0 .
docker push localhost:5000/xapp-qoe-predictor:1.0.0

# Build Federated Learning
cd ../federated-learning
docker build -t localhost:5000/xapp-federated-learning:1.0.0 .
docker push localhost:5000/xapp-federated-learning:1.0.0

cd ../..
```

#### Build E2 Simulator Image

```bash
cd simulator/e2-simulator
docker build -t localhost:5000/e2-simulator:1.0.0 .
docker push localhost:5000/e2-simulator:1.0.0
cd ../..
```

**Verify images:**
```bash
curl -s http://localhost:5000/v2/_catalog | python3 -m json.tool
```

### Component Deployment

#### Deploy Prometheus

```bash
cd oran-ric-platform
helm install r4-infrastructure-prometheus ./ric-dep/helm/infrastructure/subcharts/prometheus --namespace ricplt --values ./config/prometheus-values.yaml
```

**Verify:**
```bash
kubectl get pods -n ricplt -l app=prometheus
# Wait for all pods to be Running
```

#### Deploy Grafana

```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
helm install oran-grafana grafana/grafana -n ricplt -f ./config/grafana-values.yaml
```

**Get admin password:**
```bash
kubectl get secret -n ricplt oran-grafana -o jsonpath="{.data.admin-password}" | base64 -d && echo
```

**Import Grafana dashboards:**
```bash
# Start port forwarding in background or separate terminal
kubectl port-forward -n ricplt svc/oran-grafana 3000:80 &

# Import all dashboards
bash ./scripts/deployment/import-dashboards.sh
```

#### Deploy xApps

Deploy each xApp individually for better control:

```bash
# KPIMON - KPI Monitoring
kubectl apply -f ./xapps/kpimon-go-xapp/deploy/ -n ricxapp

# Traffic Steering
kubectl apply -f ./xapps/traffic-steering/deploy/ -n ricxapp

# RAN Control
kubectl apply -f ./xapps/rc-xapp/deploy/ -n ricxapp

# QoE Predictor (optional)
kubectl apply -f ./xapps/qoe-predictor/deploy/ -n ricxapp

# Federated Learning (optional)
kubectl apply -f ./xapps/federated-learning/deploy/ -n ricxapp
```

#### Deploy E2 Simulator

```bash
kubectl apply -f ./simulator/e2-simulator/deploy/deployment.yaml -n ricxapp
```

**Verify deployment:**
```bash
kubectl wait --for=condition=ready pod -l app=e2-simulator -n ricxapp --timeout=60s
kubectl logs -n ricxapp -l app=e2-simulator --tail=10
```

### Verification Checklist

- [ ] Docker installed and accessible without sudo
- [ ] Helm v3+ available
- [ ] kubectl can access k3s cluster
- [ ] All RIC namespaces created
- [ ] Prometheus pods running
- [ ] Grafana accessible
- [ ] xApps in Running state
- [ ] E2 Simulator generating traffic

```bash
# Run full verification
kubectl get pods -A | grep -E 'ricplt|ricxapp'
```

---

## xApps

| xApp | Version | Purpose | Key Features |
|------|---------|---------|--------------|
| **KPIMON** | v1.0.1 | KPI monitoring | E2SM-KPM v3.0, 20+ KPI types, real-time streaming |
| **Traffic Steering** | v1.0.2 | Handover decisions | E2SM-KPM+RC, A1 policy, SDL integration |
| **QoE Predictor** | v1.0.1 | QoE prediction | ML-based, TensorFlow 2.15, real-time API |
| **RAN Control** | v1.0.1 | RAN optimization | E2SM-RC v2.0, 5 optimization algorithms |
| **Federated Learning** | v1.0.0 | Distributed ML | TensorFlow+PyTorch, privacy-preserving |

**Common Endpoints** (all xApps on port 8080):
- `GET /ric/v1/health/alive` - Liveness probe
- `GET /ric/v1/health/ready` - Readiness probe
- `GET /ric/v1/metrics` - Prometheus metrics

**Documentation:** Each xApp has detailed README in `xapps/<name>/`

### Federated Learning xApp - Architecture Note

The Federated Learning xApp has two deployment variants:

1. **CPU Version** (`federated-learning`) - Default, always deployed
 - Works on any Kubernetes cluster
 - Suitable for development and testing
 - Uses TensorFlow CPU backend

2. **GPU Version** (`federated-learning-gpu`) - Optional, requires GPU setup
 - Requires NVIDIA GPU and Device Plugin
 - Significantly faster training (5-10x speedup)
 - Recommended for production with large models
 - See [GPU Support](#gpu-support-optional) for setup

**Future Consideration**: Due to its unique GPU dependencies and specialized ML infrastructure requirements, the Federated Learning xApp is a candidate for extraction into a separate repository (similar to E2 Simulator). This would enable:
- Independent development cycle for ML features
- Specialized CI/CD for GPU testing
- Cleaner dependency management (CUDA, cuDNN, TensorRT)
- Optional installation for users not needing FL capabilities

For now, both versions coexist in this repository for easier integration and testing.

---

## Monitoring & Observability

### Quick Access

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3000 | admin / `kubectl get secret -n ricplt oran-grafana -o jsonpath="{.data.admin-password}" \| base64 -d` |
| **Prometheus** | http://localhost:9090 | None required |

**Port forwarding commands:**
```bash
# Grafana
kubectl port-forward -n ricplt svc/oran-grafana 3000:80

# Prometheus
kubectl port-forward -n ricplt svc/r4-infrastructure-prometheus-server 9090:80
```

### Prometheus Metrics

All xApps expose metrics on port **8080** with automatic Prometheus discovery:

**Auto-discovery configuration:**
```yaml
prometheus.io/scrape: "true"
prometheus.io/port: "8080"
prometheus.io/path: "/ric/v1/metrics"
```

**Key Metrics by Category:**

| Category | Metric | Description |
|----------|--------|-------------|
| **Messages** | `kpimon_messages_received_total` | Total E2 indications received |
| | `kpimon_messages_processed_total` | Successfully processed messages |
| **Performance** | `kpimon_processing_time_seconds` | Message processing latency (histogram) |
| **Subscriptions** | `kpimon_active_subscriptions` | Active E2 subscriptions count |
| **KPIs** | `kpimon_kpi_value{type="prb_usage_dl"}` | PRB utilization percentage |

**Example Queries:**
```promql
# Message processing rate
rate(kpimon_messages_received_total[5m])

# Average processing time
histogram_quantile(0.95, rate(kpimon_processing_time_seconds_bucket[5m]))

# xApp resource usage
container_cpu_usage_seconds_total{namespace="ricxapp"}
```

### Alert Rules

**7 Alert Groups** covering availability, performance, and data quality:

| Alert Group | Focus | Coverage |
|-------------|-------|----------|
| **xapp_availability** | Pod health & readiness | All xApps pod status monitoring |
| **kpimon_alerts** | KPIMON specific | Message processing, rates, errors |
| **traffic_steering_alerts** | Traffic Steering specific | Handover decisions, SDL operations |
| **qoe_predictor_alerts** | QoE Predictor specific | Predictions, model performance |
| **ran_control_alerts** | RAN Control specific | Control actions, success rates |
| **xapp_resource_usage** | Resource monitoring | CPU, memory usage across xApps |
| **e2_interface_alerts** | E2 connectivity | Connection status, indication processing |

**Configuration file:** [monitoring/prometheus/alerts/xapp-alerts.yml](monitoring/prometheus/alerts/xapp-alerts.yml)

### Grafana Dashboards

**Available Dashboards** (auto-created during deployment):

| Dashboard | Key Metrics | Purpose |
|-----------|-------------|---------|
| **O-RAN RIC Platform Overview** | Total xApps, RMR messages, E2 connections | System-wide health |
| **KPIMON xApp** | Messages received, processing time, subscriptions | KPI monitoring |
| **Traffic Steering xApp** | Handover decisions, active UEs, decision latency | Traffic management |
| **QoE Predictor xApp** | Active UEs, prediction latency, predictions total | QoE tracking |
| **RAN Control xApp** | Control actions, handovers, success rate | RAN optimization |
| **Federated Learning xApp** | Training rounds, clients, accuracy, duration | ML training |

**Import dashboards:**
```bash
bash ./scripts/deployment/import-dashboards.sh
```

> **Testing**: 6 Playwright E2E tests (one per dashboard) validate metrics presence (see [Testing](#testing))

---

## Testing

### Automated Testing (Playwright)

**Test Suite Coverage:**

| Test Type | Coverage | Command |
|-----------|----------|---------|
| **Grafana Dashboards** | 6 dashboards, metrics validation | `npm run test:grafana` |
| **Dashboard Accessibility** | Login, navigation, panel loading | Included in above |
| **Metrics Presence** | All expected metrics exist | Included in above |

**Run tests:**
```bash
# First time setup
npm install

# Run all Grafana dashboard tests
npm run test:grafana

# Run with visible browser (debugging)
npm run test:grafana:headed

# View test report
npm run test:report
```

**Test results location:**
- Screenshots: `test-results/screenshots/`
- Reports: `test-results/reports/`

### E2 Simulator Testing

**Monitor continuous traffic:**
```bash
kubectl logs -n ricxapp -l app=e2-simulator -f
```

**Expected output:**
```
=== Simulation Iteration 120 ===
Successfully sent to kpimon (200)
Successfully sent to traffic-steering (200)
Successfully sent to qoe-predictor (200)
Successfully sent to ran-control (200)
```

**Manual E2 indication test:**
```bash
# Get simulator pod name
POD=$(kubectl get pod -n ricxapp -l app=e2-simulator -o jsonpath='{.items[0].metadata.name}')

# Send test indication to KPIMON
kubectl exec -n ricxapp $POD -- curl -X POST \
 http://kpimon.ricxapp.svc.cluster.local:8081/e2/indication \
 -H "Content-Type: application/json" \
 -d '{"cell_id": 1234567, "prb_usage_dl": 45.5, "prb_usage_ul": 32.1}'
```

### Performance Benchmarks

| Metric | Target | Measurement |
|--------|--------|-------------|
| **E2 indication processing** | < 10ms | `kpimon_processing_time_seconds` P95 |
| **Control command latency** | < 100ms | `rc_control_latency_seconds` P95 |
| **xApp startup time** | < 30s | Pod `Ready` condition timestamp |
| **Message throughput** | > 1000 msg/sec | `rate(kpimon_messages_received_total[1m])` |

---

## Documentation

| Document | Description | Audience |
|----------|-------------|----------|
| [QUICKSTART.md](docs/deployment/QUICKSTART.md) | 10-minute deployment | Experienced users |
| [xapp-prometheus-metrics-integration.md](docs/deployment/xapp-prometheus-metrics-integration.md) | Complete walkthrough (15k words) | First-time deployers |
| [TROUBLESHOOTING.md](docs/deployment/TROUBLESHOOTING.md) | Common issues & solutions | All users |
| xApps README files | Implementation details | Developers |

**RIC Platform Configuration:** [RIC-DEP-CUSTOMIZATION.md](docs/RIC-DEP-CUSTOMIZATION.md)

---

## What's New

### v2.0.1 (Latest)

**KUBECONFIG Standardization**
- Automatic KUBECONFIG detection with three-level priority mechanism
- Multi-cluster environment support (respects existing environment variables)
- All deployment scripts standardized to use centralized validation library
- Improved reliability and error messages
- Comprehensive testing (56 tests, 100% pass rate)

**Scripts Updated:**
- `scripts/lib/validation.sh` - Added `setup_kubeconfig()` function
- `scripts/deployment/deploy-prometheus.sh`
- `scripts/deployment/deploy-grafana.sh`
- `scripts/deployment/deploy-e2-simulator.sh`
- `scripts/verify-all-xapps.sh`
- `scripts/redeploy-xapps-with-metrics.sh`
- `scripts/deployment/deploy-all.sh` - Smart dual-check mechanism

**Documentation:**
- [PR #9 KUBECONFIG Standardization Report](docs/testing/PR9-FINAL-REPORT.md)
- Updated README.md with KUBECONFIG configuration guide

### v2.0.0

### Major Changes

**E2 Node Extraction (BREAKING)**
- E2 Simulator moved to [oran-e2-node](https://github.com/thc1006/oran-e2-node) repository
- Now a git submodule: `git submodule update --init --recursive`
- Benefits: Independent development, cleaner structure, community contributions

**Complete Metrics Integration**
- All 5 xApps now expose Prometheus metrics on port 8080
- 8 comprehensive alert rule categories
- Grafana dashboards with automated E2E testing

**Repository Cleanup**
- Removed 10,000+ lines of archived documentation
- Updated `.gitignore` for development artifacts
- Significantly reduced repository size

### Bug Fixes

1. Traffic Steering SDL error handling
2. Unified port configuration (Service/Deployment/Prometheus)
3. E2 Simulator port fixes (QoE: 8090, RC: 8100)
4. KPIMON metrics increment logic
5. Playwright headless mode update

**Full changelog:** [Releases](https://github.com/thc1006/oran-ric-platform/releases)

---

## Project Structure

```
oran-ric-platform/
├── xapps/ # 5 production xApps
│ ├── kpimon-go-xapp/ # v1.0.1
│ ├── traffic-steering/ # v1.0.2
│ ├── qoe-predictor/ # v1.0.1
│ ├── ran-control/ # v1.0.1
│ └── federated-learning/ # v1.0.0
├── monitoring/ # Prometheus + Grafana configs
│ ├── prometheus/
│ │ ├── alerts/xapp-alerts.yml
│ │ └── prometheus.yml
│ └── grafana/dashboards/
├── simulator/e2-simulator/ # Git submodule → oran-e2-node
├── scripts/
│ ├── redeploy-xapps-with-metrics.sh
│ └── deployment/deploy-e2-simulator.sh
├── tests/grafana/ # Playwright E2E tests
├── docs/deployment/ # Comprehensive guides
└── ric-dep/ # RIC Platform Helm charts
```

---

## Technical Stack

**Core:** O-RAN SC J Release, Kubernetes 1.28+ (k3s), Helm 3.x, Docker

**Languages:** Python 3.11+ (xApps), Go 1.19+ (RMR), JavaScript ES6+ (testing)

**Key Libraries:**
- ricxappframe 3.2.2 (Python xApp framework)
- RMR 4.9.4 (RIC Message Router)
- ricsdl 3.0.2 (Shared Data Layer)
- Prometheus Client, Playwright

**Infrastructure:** localhost:5000 registry, Redis (SDL), Prometheus, Grafana

---

## Contributing

1. Fork repository
2. Create feature branch: `git checkout -b feature/name`
3. Commit: `git commit -m 'Add feature'`
4. Push: `git push origin feature/name`
5. Open Pull Request

**Standards:** Python PEP 8, comprehensive docstrings, tests for new features, documentation updates.

---

## Credits

**Author:** 蔡秀吉 (thc1006)

**Related Projects:**
- [oran-e2-node](https://github.com/thc1006/oran-e2-node) - E2 Node Simulator

**Built With:**
- [O-RAN Software Community](https://o-ran-sc.org/) - J Release
- [Kubernetes](https://kubernetes.io/), [Prometheus](https://prometheus.io/), [Grafana](https://grafana.com/), [Playwright](https://playwright.dev/)

---

## License

Apache License 2.0 - See [LICENSE](LICENSE)

---

## Links

- **Repository:** https://github.com/thc1006/oran-ric-platform
- **E2 Simulator:** https://github.com/thc1006/oran-e2-node
- **Issues:** https://github.com/thc1006/oran-ric-platform/issues
- **Releases:** https://github.com/thc1006/oran-ric-platform/releases
- **O-RAN SC:** https://wiki.o-ran-sc.org/

---

<div align="center">

**Made by 蔡秀吉 (thc1006)**

*Production-ready O-RAN deployment with comprehensive observability*

[Back to Top](#o-ran-near-rt-ric-platform-with-production-xapps)

</div>
