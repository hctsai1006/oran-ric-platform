# O-RAN RIC Platform 腳本技術債修復計劃 v2.0

日期: 2025-11-17
基於: 深度分析報告 2025-11-17

---

## 執行摘要

基於深度分析報告，本修復計劃整合了 **TDD Rule**、**Boy Scout Rule** 和 **Small CLs** 原則，將技術債務分為 **14 個聚焦的 PR**，預計 **3-4 週**完成。

### 關鍵發現

- **40 個 Shell 腳本**，共 5,368 行程式碼
- **7 個腳本缺少執行權限**
- **8 處硬編碼絕對路徑**
- **2 個命名衝突**（deploy-all.sh）
- **3 個功能重複的腳本**
- **測試覆蓋率: 2.5%**

### 修復優先級

1. **Critical (A級)**: 執行權限、硬編碼路徑、命名衝突
2. **High (B級)**: 路徑依賴、KUBECONFIG 標準化
3. **Medium (C級)**: 測試框架、共用函數庫
4. **Low (D級)**: 文件更新、架構優化

---

## 已完成的 PR (Sprint 0)

### ✅ PR #1: 刪除損壞的 deploy.sh
**狀態**: 已合併
**變更**: -369 行
**分支**: `cleanup/remove-broken-deploy-script`

### ✅ PR #2: 修復 redeploy-xapps-with-metrics.sh 硬編碼路徑
**狀態**: 已推送
**變更**: +11 行
**分支**: `fix/remove-hardcoded-path-redeploy-xapps`

### ✅ PR #3: 刪除重複的 import-grafana-dashboards.sh
**狀態**: 已推送
**變更**: -77 行
**分支**: `cleanup/remove-duplicate-import-dashboards`

---

## Sprint 1: 關鍵基礎修復 (Week 1)

### PR #4: 修復所有腳本執行權限

**目標**: 修復 7 個缺少執行權限的腳本 + 1 個異常權限

**優先級**: 🔴 Critical (A級)

**變更範圍**:
```bash
# 添加執行權限
chmod +x scripts/deploy-ml-xapps.sh
chmod +x scripts/deployment/setup-k3s.sh
chmod +x xapps/scripts/build-all.sh
chmod +x xapps/scripts/deploy-all.sh
chmod +x xapps/scripts/onboard-xapps.sh
chmod +x xapps/scripts/test-integration.sh

# 修復異常權限
chmod 755 scripts/deployment/deploy-all.sh
```

**驗證步驟**:
```bash
# 檢查所有 .sh 檔案權限
find scripts xapps/scripts -name "*.sh" -exec ls -l {} \; | grep -v "rwxr"

# 測試執行
./scripts/deploy-ml-xapps.sh --help
./xapps/scripts/build-all.sh --help
```

**預估工作量**: 30 分鐘
**Small CL**: ✅ (僅修改檔案屬性，無程式碼變更)

**Commit Message**:
```
fix: correct execute permissions for shell scripts

修復所有腳本的執行權限問題

變更內容:
- 添加執行權限至 6 個腳本
- 修復 deploy-all.sh 異常權限 (711 -> 755)

問題原因:
這些腳本在開發過程中可能通過 bash 指令執行，
導致執行權限未被設置。異常的 711 權限會阻止
非擁有者讀取腳本內容，影響團隊協作。

驗證:
- 確認所有 .sh 檔案都有執行權限
- 測試關鍵腳本可正常執行

影響範圍:
- 修改 7 個檔案屬性
- 無程式碼變更

```

---

### PR #5: 移除剩餘硬編碼絕對路徑

**目標**: 修復 3 個腳本中的硬編碼路徑

**優先級**: 🔴 Critical (A級)

**變更範圍**:

#### 1. scripts/deployment/import-dashboards.sh (行 20)

**Before**:
```bash
DASHBOARD_DIR="/home/thc1006/oran-ric-platform/config/dashboards"
```

**After**:
```bash
# 動態解析專案根目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 驗證專案根目錄
if [ ! -f "$PROJECT_ROOT/README.md" ]; then
    echo -e "${RED}[ERROR]${NC} Cannot locate project root" >&2
    exit 1
fi

DASHBOARD_DIR="${PROJECT_ROOT}/config/dashboards"
```

#### 2. scripts/deployment/deploy-e2-simulator.sh (行 21)

**Before**:
```bash
PROJECT_ROOT="/home/thc1006/oran-ric-platform"
```

**After**:
```bash
# 動態解析專案根目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 驗證專案根目錄
if [ ! -f "$PROJECT_ROOT/README.md" ]; then
    echo -e "${RED}[ERROR]${NC} Cannot locate project root" >&2
    exit 1
fi
```

#### 3. scripts/deployment/deploy-grafana.sh (行 102, 114)

**Before**:
```bash
-f /home/thc1006/oran-ric-platform/config/grafana-values.yaml
```

**After**:
```bash
# 在腳本開頭添加
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 在使用處
-f "${PROJECT_ROOT}/config/grafana-values.yaml"
```

**驗證步驟**:
```bash
# 檢查是否還有硬編碼路徑
grep -r "/home/thc1006" scripts/deployment/*.sh

# 從不同目錄測試執行
cd /tmp
/path/to/oran-ric-platform/scripts/deployment/import-dashboards.sh --dry-run
```

**預估工作量**: 1 小時
**預估總行數**: +30, -3 行
**Small CL**: ✅ (單一關注點，3 個檔案)

**Commit Message**:
```
fix: remove hardcoded absolute paths from deployment scripts

移除部署腳本中的硬編碼絕對路徑

變更內容:
- import-dashboards.sh: 動態解析 DASHBOARD_DIR
- deploy-e2-simulator.sh: 動態解析 PROJECT_ROOT
- deploy-grafana.sh: 使用變數替代硬編碼路徑

技術實作:
使用 BASH_SOURCE 和 dirname 動態計算專案根目錄，
並添加 README.md 驗證機制，確保路徑正確。

問題根源:
硬編碼的使用者路徑 (/home/thc1006) 導致腳本
無法在其他環境或使用者下執行。

驗證:
- 從不同目錄執行腳本成功
- 所有配置檔案路徑正確解析
- 無剩餘硬編碼路徑

影響範圍:
- 修改 3 個檔案
- +30 行, -3 行

```

---

### PR #6: 修復 deploy-ml-xapps.sh 路徑依賴

**目標**: 修復脆弱的相對路徑依賴

**優先級**: 🟠 High (B級)

**變更範圍**:

**Before** (行 68-86):
```bash
cd xapps/qoe-predictor
docker build ...
cd ../..

cd xapps/federated-learning
docker build ...
cd ../..
```

**After**:
```bash
# 在腳本開頭添加（與 PR #5 類似）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 驗證專案根目錄
if [ ! -f "$PROJECT_ROOT/README.md" ]; then
    log_error "Cannot locate project root"
    echo "Expected README.md at: $PROJECT_ROOT/README.md" >&2
    exit 1
fi

# 替換所有 cd 命令
cd "$PROJECT_ROOT/xapps/qoe-predictor" || exit 1
docker build ...
cd "$PROJECT_ROOT" || exit 1

cd "$PROJECT_ROOT/xapps/federated-learning" || exit 1
docker build ...
cd "$PROJECT_ROOT" || exit 1
```

**驗證步驟**:
```bash
# 從不同目錄執行
cd /tmp
/path/to/oran-ric-platform/scripts/deploy-ml-xapps.sh build

cd $HOME
/path/to/oran-ric-platform/scripts/deploy-ml-xapps.sh verify
```

**預估工作量**: 45 分鐘
**預估總行數**: +20, -8 行
**Small CL**: ✅ (單一檔案，單一問題)

**Commit Message**:
```
fix: resolve fragile path dependencies in deploy-ml-xapps.sh

修復 deploy-ml-xapps.sh 中脆弱的路徑依賴

變更內容:
- 動態解析專案根目錄
- 使用絕對路徑替代相對路徑 cd
- 添加目錄切換錯誤處理

問題原因:
腳本使用相對路徑 cd (如 cd xapps/qoe-predictor)，
假設從專案根目錄執行。從其他目錄執行會失敗。

技術改進:
- 計算絕對路徑: PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
- 每次 cd 都使用 || exit 1 錯誤處理
- 添加 README.md 驗證機制

驗證:
- 從 /tmp 目錄執行成功
- 從 $HOME 目錄執行成功
- 錯誤處理正常工作

影響範圍:
- 修改 1 個檔案
- +20 行, -8 行

```

---

### PR #7: 解決 deploy-all.sh 命名衝突

**目標**: 重新命名避免混淆

**優先級**: 🟠 High (B級)

**變更範圍**:
```bash
# 重新命名
git mv xapps/scripts/deploy-all.sh xapps/scripts/deploy-xapps-only.sh

# 更新引用（如果有）
grep -r "xapps/scripts/deploy-all.sh" docs/
```

**文件更新**:
- 更新所有文件中的參考
- 添加 deprecation 說明（如果需要向後兼容）

**驗證步驟**:
```bash
# 確認沒有剩餘引用
grep -r "xapps/scripts/deploy-all.sh" .

# 測試新名稱
./xapps/scripts/deploy-xapps-only.sh --help
```

**預估工作量**: 30 分鐘
**Small CL**: ✅ (檔案重新命名 + 參考更新)

**Commit Message**:
```
refactor: rename xapps/scripts/deploy-all.sh to avoid naming conflict

重新命名 xapps 部署腳本以避免命名衝突

變更內容:
- 重新命名: xapps/scripts/deploy-all.sh -> deploy-xapps-only.sh
- 更新所有文件參考

命名衝突問題:
- scripts/deployment/deploy-all.sh: 完整系統部署
- xapps/scripts/deploy-all.sh: 僅 xApps 部署

新名稱更清楚反映功能範圍：
- deploy-all.sh: 完整部署（平台 + xApps + 監控）
- deploy-xapps-only.sh: 僅部署 xApps

驗證:
- 確認無剩餘舊名稱引用
- 新腳本可正常執行

影響範圍:
- 重新命名 1 個檔案
- 更新文件參考

```

---

## Sprint 2: 標準化和測試 (Week 2)

### PR #8: 創建共用函數庫

**目標**: 抽取重複程式碼到共用庫

**優先級**: 🟡 Medium (C級)

**變更範圍**:

**新增檔案**: `scripts/utils/common.sh`

```bash
#!/bin/bash
# O-RAN RIC Platform - 共用函數庫
# 作者: 蔡秀吉 (thc1006)
# 日期: 2025-11-17

# 顏色定義
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# 日誌函數
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 路徑解析
# 使用方式: PROJECT_ROOT=$(get_project_root)
get_project_root() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
    local project_root

    # 嘗試向上查找專案根目錄
    local current_dir="$script_dir"
    while [ "$current_dir" != "/" ]; do
        if [ -f "$current_dir/README.md" ] && [ -d "$current_dir/.git" ]; then
            project_root="$current_dir"
            break
        fi
        current_dir="$(dirname "$current_dir")"
    done

    if [ -z "$project_root" ]; then
        log_error "Cannot locate project root (no README.md + .git found)"
        return 1
    fi

    echo "$project_root"
}

# KUBECONFIG 設定
# 優先級: $KUBECONFIG > ~/.kube/config > /etc/rancher/k3s/k3s.yaml
setup_kubeconfig() {
    if [ -n "$KUBECONFIG" ] && [ -f "$KUBECONFIG" ]; then
        log_info "Using existing KUBECONFIG: $KUBECONFIG"
        return 0
    fi

    if [ -f "$HOME/.kube/config" ]; then
        export KUBECONFIG="$HOME/.kube/config"
        log_info "Using KUBECONFIG: $KUBECONFIG"
        return 0
    fi

    if [ -f "/etc/rancher/k3s/k3s.yaml" ]; then
        export KUBECONFIG="/etc/rancher/k3s/k3s.yaml"
        log_info "Using KUBECONFIG: $KUBECONFIG"
        return 0
    fi

    log_error "Cannot locate kubeconfig file"
    log_error "Tried: \$KUBECONFIG, ~/.kube/config, /etc/rancher/k3s/k3s.yaml"
    return 1
}

# 檢查 kubectl 連線
check_k8s_connection() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install kubectl."
        return 1
    fi

    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        log_error "KUBECONFIG: ${KUBECONFIG:-not set}"
        return 1
    fi

    log_success "Connected to Kubernetes cluster"
    return 0
}

# 驗證配置檔案存在
# 使用方式: verify_config_files "$PROJECT_ROOT/config/file1.yaml" "$PROJECT_ROOT/config/file2.yaml"
verify_config_files() {
    local missing_files=()

    for file in "$@"; do
        if [ ! -f "$file" ]; then
            missing_files+=("$file")
        fi
    done

    if [ ${#missing_files[@]} -gt 0 ]; then
        log_error "Missing required configuration files:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        return 1
    fi

    log_success "All required configuration files exist"
    return 0
}

# 等待 Pod 就緒
# 使用方式: wait_for_pod "namespace" "label=value" "timeout_seconds"
wait_for_pod() {
    local namespace=$1
    local label=$2
    local timeout=${3:-300}

    log_info "Waiting for pod with label '$label' in namespace '$namespace' (timeout: ${timeout}s)"

    if kubectl wait --for=condition=ready pod -l "$label" -n "$namespace" --timeout="${timeout}s" &> /dev/null; then
        log_success "Pod is ready"
        return 0
    else
        log_error "Pod not ready within ${timeout}s"
        kubectl get pods -n "$namespace" -l "$label"
        return 1
    fi
}
```

**使用範例** (更新一個現有腳本作為示範):

```bash
#!/bin/bash
# 範例: 更新 verify-all-xapps.sh

set -e

# 載入共用函數
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/utils/common.sh"

# 使用共用函數
PROJECT_ROOT=$(get_project_root) || exit 1
setup_kubeconfig || exit 1
check_k8s_connection || exit 1

log_info "Starting xApp verification..."
# ... 其餘程式碼
```

**驗證步驟**:
```bash
# 測試共用函數庫
bash -n scripts/utils/common.sh

# 測試更新後的腳本
./scripts/verify-all-xapps.sh
```

**預估工作量**: 2 小時
**預估總行數**: +150 新增
**Small CL**: ✅ (新增獨立模組，不修改現有邏輯)

---

### PR #9: 標準化 KUBECONFIG 處理

**目標**: 統一所有腳本的 KUBECONFIG 設定方式

**優先級**: 🟠 High (B級)

**前置條件**: PR #8 (共用函數庫)

**變更範圍**:

更新以下 3 個腳本，使用統一的 KUBECONFIG 處理：
- scripts/verify-all-xapps.sh
- scripts/redeploy-xapps-with-metrics.sh
- scripts/deployment/deploy-e2-simulator.sh

**Before** (所有腳本都類似):
```bash
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
```

**After**:
```bash
source "${SCRIPT_DIR}/utils/common.sh"
setup_kubeconfig || exit 1
```

**驗證步驟**:
```bash
# 測試不同 KUBECONFIG 情境
export KUBECONFIG=/custom/path/kubeconfig
./scripts/verify-all-xapps.sh  # 應該使用自定義路徑

unset KUBECONFIG
./scripts/verify-all-xapps.sh  # 應該自動查找
```

**預估工作量**: 1 小時
**預估總行數**: +12, -6 行
**Small CL**: ✅ (單一關注點，重複模式)

---

### PR #10: 添加 BATS 測試框架

**目標**: 建立自動化測試基礎設施

**優先級**: 🟡 Medium (C級)

**變更範圍**:

**新增檔案**:
1. `tests/scripts/test_helper.bash` - 測試輔助函數
2. `tests/scripts/test_common.bats` - 共用函數測試
3. `.github/workflows/test-scripts.yml` - CI 整合

**test_helper.bash**:
```bash
#!/bin/bash
# BATS 測試輔助函數

setup_test_env() {
    export TEST_PROJECT_ROOT="${BATS_TEST_DIRNAME}/../.."
    export TEST_TMPDIR="${BATS_TMPDIR}/oran-ric-test"
    mkdir -p "$TEST_TMPDIR"
}

cleanup_test_env() {
    rm -rf "$TEST_TMPDIR"
}

mock_kubectl() {
    function kubectl() {
        echo "MOCK: kubectl $@"
        return 0
    }
    export -f kubectl
}
```

**test_common.bats**:
```bash
#!/usr/bin/env bats

load test_helper

setup() {
    setup_test_env
    source "${TEST_PROJECT_ROOT}/scripts/utils/common.sh"
}

teardown() {
    cleanup_test_env
}

@test "log_info outputs correct format" {
    run log_info "test message"
    [ "$status" -eq 0 ]
    [[ "$output" =~ \[INFO\] ]]
    [[ "$output" =~ "test message" ]]
}

@test "get_project_root finds README.md" {
    run get_project_root
    [ "$status" -eq 0 ]
    [ -f "${output}/README.md" ]
}

@test "verify_config_files detects missing files" {
    run verify_config_files "/nonexistent/file.yaml"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Missing required configuration" ]]
}
```

**CI 整合** (`.github/workflows/test-scripts.yml`):
```yaml
name: Shell Script Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install BATS
        run: |
          sudo apt-get update
          sudo apt-get install -y bats

      - name: Run tests
        run: bats tests/scripts/
```

**預估工作量**: 3 小時
**預估總行數**: +200 新增
**Small CL**: ✅ (測試基礎設施，不修改產品程式碼)

---

### PR #11: 為關鍵腳本添加測試

**目標**: 提升測試覆蓋率到 30%

**優先級**: 🟡 Medium (C級)

**前置條件**: PR #10 (BATS 框架)

**變更範圍**:

**新增檔案**:
1. `tests/scripts/test_redeploy_xapps.bats`
2. `tests/scripts/test_verify_xapps.bats`
3. `tests/scripts/test_path_resolution.bats`

**範例測試** (`test_path_resolution.bats`):
```bash
#!/usr/bin/env bats

load test_helper

@test "scripts can resolve PROJECT_ROOT from any directory" {
    cd /tmp

    run /path/to/oran-ric-platform/scripts/deployment/deploy-all.sh --dry-run
    [ "$status" -eq 0 ]
}

@test "scripts handle missing README.md gracefully" {
    # 建立假專案結構（無 README.md）
    mkdir -p "$TEST_TMPDIR/fake-project/scripts"

    # 測試應該失敗
    cd "$TEST_TMPDIR/fake-project"
    run bash -c "source /path/to/common.sh && get_project_root"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Cannot locate project root" ]]
}

@test "all shell scripts have execute permissions" {
    cd "${TEST_PROJECT_ROOT}"

    # 檢查所有 .sh 檔案
    while IFS= read -r script; do
        if [ ! -x "$script" ]; then
            echo "Missing execute permission: $script"
            return 1
        fi
    done < <(find scripts xapps/scripts -name "*.sh")
}
```

**預估工作量**: 4 小時
**預估總行數**: +300 新增
**Small CL**: ✅ (純測試程式碼)

---

## Sprint 3: 文件和整合 (Week 3)

### PR #12: 更新 PHASE4-DEPLOYMENT-COMPLETE.md

**目標**: 移除過時的 deploy-ml-xapps.sh 參考

**優先級**: 🟢 Low (D級)

**變更範圍**:

文件: `docs/PHASE4-DEPLOYMENT-COMPLETE.md`

**替換內容**:
- 將所有 `./scripts/deploy-ml-xapps.sh` 替換為 `./scripts/deployment/deploy-all.sh`
- 更新命令範例
- 添加新的部署選項說明

**Before** (行 96, 156, 489, 495-501):
```markdown
./scripts/deploy-ml-xapps.sh build
./scripts/deploy-ml-xapps.sh deploy
./scripts/deploy-ml-xapps.sh cleanup
```

**After**:
```markdown
# 完整部署（推薦）
./scripts/deployment/deploy-all.sh

# 或僅部署 xApps
./xapps/scripts/deploy-xapps-only.sh

# 構建映像（開發用）
./xapps/scripts/build-all.sh
```

**預估工作量**: 1 小時
**預估總行數**: ±20 行
**Small CL**: ✅ (僅文件更新)

---

### PR #13: 創建腳本使用指南

**目標**: 為所有腳本提供統一文件

**優先級**: 🟢 Low (D級)

**變更範圍**:

**新增檔案**: `scripts/README.md`

```markdown
# O-RAN RIC Platform 腳本使用指南

日期: 2025-11-17

## 目錄結構

```
scripts/
├── deployment/           # 部署相關腳本
│   ├── deploy-all.sh    # 🚀 一鍵完整部署（推薦）
│   ├── setup-k3s.sh     # k3s 集群設置
│   └── ...
├── xapp/                # xApp 管理腳本
├── utils/               # 共用函數庫
└── README.md            # 本文件
```

## 快速開始

### 1. 完整部署

```bash
# 一鍵部署 RIC 平台 + xApps + 監控
sudo ./scripts/deployment/deploy-all.sh
```

### 2. xApps 管理

```bash
# 構建所有 xApps
./xapps/scripts/build-all.sh

# 部署 xApps
./xapps/scripts/deploy-xapps-only.sh

# 驗證 xApps 健康狀態
./scripts/verify-all-xapps.sh
```

## 腳本參考

### 部署腳本

| 腳本 | 用途 | 執行時間 | 前置需求 |
|------|------|---------|---------|
| deploy-all.sh | 完整系統部署 | ~15 分鐘 | sudo, k3s |
| setup-k3s.sh | k3s 集群設置 | ~5 分鐘 | sudo |
| deploy-prometheus.sh | Prometheus 部署 | ~3 分鐘 | k3s |
| deploy-grafana.sh | Grafana 部署 | ~3 分鐘 | k3s |

### xApp 管理

| 腳本 | 用途 | 執行時間 |
|------|------|---------|
| build-all.sh | 構建所有 xApps | ~10 分鐘 |
| deploy-xapps-only.sh | 部署 xApps | ~5 分鐘 |
| redeploy-xapps-with-metrics.sh | 重新部署並更新 metrics | ~8 分鐘 |
| verify-all-xapps.sh | 健康檢查 | ~1 分鐘 |

## 環境變數

所有腳本支援以下環境變數：

```bash
# KUBECONFIG 路徑（自動檢測）
export KUBECONFIG=/path/to/kubeconfig

# Docker Registry
export REGISTRY=localhost:5000

# 命名空間
export NAMESPACE_PLT=ricplt
export NAMESPACE_XAPP=ricxapp
```

## 疑難排解

### 執行權限問題

```bash
# 如果遇到 Permission denied
chmod +x scripts/deployment/*.sh
chmod +x xapps/scripts/*.sh
```

### KUBECONFIG 找不到

```bash
# 檢查當前 KUBECONFIG
echo $KUBECONFIG

# 手動設定
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
```

## 開發指南

### 新增腳本

1. 使用共用函數庫：
```bash
source "${SCRIPT_DIR}/utils/common.sh"
PROJECT_ROOT=$(get_project_root) || exit 1
```

2. 添加錯誤處理：
```bash
set -e  # Exit on error
```

3. 添加測試：
```bash
# tests/scripts/test_your_script.bats
```

### 測試

```bash
# 運行所有測試
bats tests/scripts/

# 運行特定測試
bats tests/scripts/test_common.bats
```

## 相關文件

- [部署指南](../docs/deployment/README.md)
- [疑難排解](../docs/deployment/TROUBLESHOOTING.md)
- [QUICKSTART](../docs/deployment/QUICKSTART.md)
```

**預估工作量**: 2 小時
**預估總行數**: +250 新增
**Small CL**: ✅ (純文件)

---

### PR #14: 添加配置檔案驗證功能

**目標**: 在部署前驗證所有必要配置檔案

**優先級**: 🟢 Low (D級)

**前置條件**: PR #8 (共用函數庫)

**變更範圍**:

在 `scripts/utils/common.sh` 中已包含 `verify_config_files()` 函數。

**更新腳本使用驗證**:

1. **deploy-all.sh** (在部署前添加):
```bash
# 驗證必要配置檔案
log_info "Verifying configuration files..."
verify_config_files \
    "${PROJECT_ROOT}/config/prometheus-values.yaml" \
    "${PROJECT_ROOT}/config/grafana-values.yaml" \
    "${PROJECT_ROOT}/config/dashboards/oran-ric-overview.json" \
    || exit 1
```

2. **deploy-prometheus.sh**:
```bash
verify_config_files "${PROJECT_ROOT}/config/prometheus-values.yaml" || exit 1
```

3. **deploy-grafana.sh**:
```bash
verify_config_files "${PROJECT_ROOT}/config/grafana-values.yaml" || exit 1
```

**預估工作量**: 1 小時
**預估總行數**: +15 行
**Small CL**: ✅ (小改動，單一目的)

---

## Sprint 總結

### Sprint 1 成果 (Week 1)
- ✅ 所有腳本擁有正確執行權限
- ✅ 無硬編碼絕對路徑
- ✅ 無命名衝突
- ✅ 路徑依賴穩健

### Sprint 2 成果 (Week 2)
- ✅ 共用函數庫建立
- ✅ KUBECONFIG 處理標準化
- ✅ BATS 測試框架就緒
- ✅ 測試覆蓋率達 30%

### Sprint 3 成果 (Week 3)
- ✅ 文件更新完整
- ✅ 腳本使用指南完成
- ✅ 配置驗證機制建立

---

## 度量指標

### 修復前

| 指標 | 數值 |
|------|------|
| 總腳本數 | 40 |
| 總行數 | 5,368 |
| 硬編碼路徑 | 8 處 |
| 缺少執行權限 | 7 個 |
| 命名衝突 | 2 個 |
| 測試覆蓋率 | 2.5% |
| 重複功能 | 3 組 |

### 修復後（預期）

| 指標 | 數值 | 改善 |
|------|------|------|
| 總腳本數 | 41 | +1 (utils/common.sh) |
| 總行數 | 5,700 | +332 (測試 +500, 優化 -168) |
| 硬編碼路徑 | 0 | ✅ -100% |
| 缺少執行權限 | 0 | ✅ -100% |
| 命名衝突 | 0 | ✅ -100% |
| 測試覆蓋率 | 30% | ✅ +1100% |
| 重複功能 | 0 | ✅ -100% |

---

## 執行原則

### TDD (Test-Driven Development)
- PR #10-11: 先建立測試框架，再重構
- 每個 PR 都需要對應的驗證步驟

### Boy Scout Rule
- 每次修改都讓程式碼比之前更好
- 統一程式碼風格、錯誤處理
- 清理過時註解

### Small CLs (Changelists)
- 每個 PR 聚焦單一問題
- PR #4: 僅修改檔案屬性
- PR #5: 僅修復路徑問題
- PR #8: 僅新增函數庫
- 平均每個 PR: 100-250 行變更

### Anti-Patterns (避免)
- ❌ 過度生成: 不建立不必要的抽象
- ❌ 過早抽象: 在第 3 次重複時才抽象
- ❌ 大改動: 每個 PR 控制在 300 行內

---

## 檢查清單

每個 PR 推送前必須完成：

- [ ] 程式碼通過 `bash -n` 語法檢查
- [ ] 執行權限正確 (`ls -l`)
- [ ] 無硬編碼路徑 (`grep -r "/home/"`)
- [ ] 從不同目錄執行成功
- [ ] Commit message 符合規範
- [ ] 變更小於 300 行
- [ ] 有對應的驗證步驟

---

## 聯絡資訊

**專案**: O-RAN RIC Platform
**日期**: 2025-11-17

---

**注意**: 本計劃遵循軟體工程最佳實踐，所有修改都經過深度分析和驗證。
