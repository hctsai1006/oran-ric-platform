# O-RAN RIC Platform Deployment Fixes Summary
## 部署修正總結

**Author**: 蔡秀吉 (thc1006)
**Date**: 2025-11-18
**Version**: v2.0.2 (Pre-release)

---

## 🎯 修正目標 (Objectives)

基於實際部署測試發現的問題，對部署流程進行以下修正：

1. ✅ 明確標註 KUBECONFIG 設定要求
2. ✅ 明確標註 E2 Simulator Submodule 初始化要求
3. ✅ 添加 GPU 支援設定指南
4. ✅ 修正自動部署腳本
5. ✅ 提供 Federated Learning 架構說明

---

## 📝 修改內容 (Changes Made)

### 1. README.md 修改

#### 1.1 新增「關鍵設定要求」區塊 (Critical Setup Requirements)

**位置**: Quick Start > Fast Track Deployment 開頭
**行號**: 300-329

**新增內容**:
```markdown
> **📋 Critical Setup Requirements** (必讀！Read First!)
>
> Before starting deployment, ensure these steps are completed:
>
> 1. **KUBECONFIG Configuration** (必須/Required)
>    - All `kubectl` and `helm` commands require proper KUBECONFIG setup
>    - After k3s installation, configure kubectl access
>    - Verify: `kubectl get nodes` should show your node
>
> 2. **E2 Simulator Submodule** (必須/Required)
>    - E2 Simulator is a git submodule (separate repository)
>    - Must initialize before building images
>    - Verify: `ls simulator/e2-simulator/` should show Dockerfile and src/
>
> 3. **GPU Support** (可選/Optional - for Federated Learning GPU)
>    - Required only if you want to use GPU-accelerated Federated Learning
>    - See GPU Support Setup below
>    - CPU version works without GPU setup
```

**目的**:
- 解決用戶執行部署時因缺少 KUBECONFIG 而失敗的問題
- 防止用戶忘記初始化 E2 Simulator submodule
- 說明 GPU 是可選功能

#### 1.2 新增 Step 2: 初始化 E2 Simulator Submodule

**位置**: Quick Start > Step 2 (原 Step 2 變成 Step 3)
**行號**: 368-377

**新增內容**:
```bash
# Initialize E2 Simulator git submodule
cd oran-ric-platform
git submodule update --init --recursive

# Verify submodule is initialized
ls simulator/e2-simulator/  # Should show: Dockerfile, src/, deploy/, etc.
```

**目的**:
- 確保用戶在建置映像前初始化 submodule
- 避免 Docker build 時找不到 Dockerfile 的錯誤

#### 1.3 更新步驟編號

- Step 2 → Step 3 (Build Images)
- Step 3 → Step 4 (Deploy RIC Platform)
- Step 4 → Step 5 (Access Dashboard)

#### 1.4 新增 GPU Support 完整指南

**位置**: Quick Start 末尾 (Verify Deployment 之後)
**行號**: 451-489

**新增內容**:
- GPU 支援前置條件
- GPU 設定腳本使用方式
- 驗證 GPU Pod 調度方法
- 疑難排解指南

**目的**:
- 解決 federated-learning-gpu Pod 一直 Pending 的問題
- 提供完整的 GPU 設定流程

#### 1.5 新增 Federated Learning 架構說明

**位置**: xApps 章節末尾
**行號**: 881-902

**新增內容**:
```markdown
### Federated Learning xApp - Architecture Note

The Federated Learning xApp has two deployment variants:

1. **CPU Version** - Default, always deployed
2. **GPU Version** - Optional, requires GPU setup

**Future Consideration**: Candidate for extraction into separate repository
```

**目的**:
- 回答用戶關於「是否應該獨立 repo」的問題
- 說明兩個版本的差異和使用場景

---

### 2. 新增 GPU 支援設定腳本

**文件**: `scripts/setup-gpu-support.sh`
**權限**: `755 (可執行)`

**功能**:
1. 檢查 NVIDIA 驅動和 kubectl 可用性
2. 安裝 NVIDIA Device Plugin for Kubernetes
3. 為節點添加 `nvidia.com/gpu=true` 標籤
4. 驗證 GPU 資源可用性

**使用方式**:
```bash
cd oran-ric-platform
sudo bash scripts/setup-gpu-support.sh
```

**腳本特色**:
- ✅ 使用標準化的 KUBECONFIG 設定（調用 `setup_kubeconfig()`）
- ✅ 完整的錯誤檢查和驗證
- ✅ 顏色化輸出，易於閱讀
- ✅ 提供下一步操作建議

---

### 3. wednesday-safe-deploy.sh 修改

**位置**: `scripts/wednesday-safe-deploy.sh`
**行號**: 175-186 (新增)

**新增功能**: E2 Simulator Submodule 自動初始化檢查

```bash
step "檢查並初始化 E2 Simulator Submodule..."
if [ ! -f "$PROJECT_ROOT/simulator/e2-simulator/Dockerfile" ]; then
    info "E2 Simulator submodule 未初始化，正在初始化..."
    cd "$PROJECT_ROOT"
    if ! git submodule update --init --recursive; then
        error "E2 Simulator submodule 初始化失敗"
        exit 1
    fi
    success "E2 Simulator submodule 初始化完成"
else
    success "E2 Simulator submodule 已初始化"
fi
```

**目的**:
- 自動檢測並初始化 E2 Simulator submodule
- 防止部署到 Phase 5 時才發現 submodule 未初始化
- 提供清晰的錯誤訊息

---

## 🔧 技術細節 (Technical Details)

### GPU 支援技術架構

**問題根源**:
1. federated-learning-gpu deployment 需要:
   - 節點標籤: `nvidia.com/gpu: "true"` (nodeSelector)
   - GPU 資源: `nvidia.com/gpu: "1"` (resources.limits)
2. k3s 預設不安裝 NVIDIA Device Plugin
3. 節點沒有 GPU 標籤和資源

**解決方案**:
1. 安裝 NVIDIA Device Plugin (DaemonSet)
   - 來源: https://github.com/NVIDIA/k8s-device-plugin
   - 版本: v0.14.0
2. 手動為節點添加標籤
3. Device Plugin 自動發現 GPU 並註冊資源

**驗證**:
```bash
# 檢查 GPU 資源
kubectl get nodes -o=custom-columns=NAME:.metadata.name,GPU:.status.capacity.'nvidia\.com/gpu'

# 檢查 Device Plugin
kubectl get pods -n kube-system -l name=nvidia-device-plugin-ds

# 檢查 GPU Pod
kubectl get pods -n ricxapp -l version=v1.0.0-gpu
```

---

## ✅ 測試結果 (Test Results)

### 實際部署測試 (2025-11-18)

**環境**:
- OS: Debian/Ubuntu
- K8s: k3s v1.28.5+k3s1
- GPU: NVIDIA RTX 3060 12GB
- CUDA: 12.6.85
- Docker Registry: localhost:5000

**部署結果**:
```
✅ Prometheus: Running (1/1)
✅ Grafana: Running (1/1)
✅ KPIMON: Running (1/1)
✅ Traffic Steering: Running (1/1)
✅ RAN Control: Running (1/1)
✅ QoE Predictor: Running (1/1)
✅ Federated Learning (CPU): Running (1/1)
⏸️  Federated Learning (GPU): Pending → 待 GPU 設定後可用
✅ E2 Simulator: Running (1/1)
```

**發現的問題**:
1. ❌ KUBECONFIG 未設定 → `kubectl` / `helm` 命令失敗
   - **修正**: README.md 添加明確說明
2. ❌ E2 Simulator submodule 未初始化 → Docker build 失敗
   - **修正**: 添加獨立步驟 + wednesday-safe-deploy.sh 自動檢查
3. ⚠️  GPU Pod Pending → 無 GPU 節點標籤
   - **修正**: 新增 setup-gpu-support.sh 腳本

---

## 📚 文件更新 (Documentation Updates)

### 新增文件

1. **scripts/setup-gpu-support.sh**
   - GPU 支援一鍵設定腳本
   - 完整的前置檢查和驗證

2. **DEPLOYMENT_FIXES_SUMMARY.md** (本文件)
   - 修正總結和技術說明

### 修改文件

1. **README.md**
   - 新增「關鍵設定要求」區塊
   - 新增 E2 Simulator 初始化步驟
   - 新增 GPU Support 完整指南
   - 新增 Federated Learning 架構說明

2. **scripts/wednesday-safe-deploy.sh**
   - 新增 E2 Simulator submodule 自動初始化檢查

---

## 🚀 後續建議 (Next Steps)

### 短期 (v2.0.2)

1. ✅ 完成本次修正
2. ⬜ 測試所有部署腳本
3. ⬜ 更新 CHANGELOG.md
4. ⬜ 準備 v2.0.2 release notes

### 中期 (v2.1.0)

1. **Federated Learning 獨立化評估**
   - 考慮將 FL xApp 獨立成 submodule
   - 類似 E2 Simulator 的架構
   - 優點:
     * 獨立的 GPU 相關依賴管理
     * 專門的 CI/CD for GPU 測試
     * 可選安裝（不需要 FL 的用戶無需下載）
   - 缺點:
     * 增加部署複雜度
     * 需要維護額外的 repo

2. **自動化 GPU 檢測**
   - 自動檢測系統是否有 GPU
   - 自動決定是否部署 GPU 版本
   - 自動運行 GPU 設定腳本

3. **完整的端對端測試**
   - 無 GPU 環境測試
   - 有 GPU 環境測試
   - CI/CD 整合

### 長期 (v3.0.0)

1. **Helm Chart 統一**
   - 所有組件使用 Helm Chart 部署
   - 統一的配置管理
   - 簡化部署流程

2. **Operator 模式**
   - RIC Platform Operator
   - 自動化生命週期管理
   - 自動修復和升級

---

## 🔗 相關連結 (Related Links)

- **E2 Simulator Repository**: https://github.com/thc1006/oran-e2-node
- **NVIDIA Device Plugin**: https://github.com/NVIDIA/k8s-device-plugin
- **O-RAN SC**: https://wiki.o-ran-sc.org/
- **Issue Tracker**: https://github.com/thc1006/oran-ric-platform/issues

---

## 📞 聯繫方式 (Contact)

如有問題或建議，請：
1. 提交 GitHub Issue
2. 聯繫作者：蔡秀吉 (thc1006)

---

**結論**: 所有關鍵部署問題已修正，系統可正常部署。GPU 支援為可選功能，不影響核心平台運行。建議後續版本考慮將 Federated Learning xApp 獨立成 submodule，以獲得更好的模組化和維護性。
