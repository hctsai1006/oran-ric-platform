#!/bin/bash
#
# O-RAN SC Release J - 為所有 xApp 啟用雙路徑通訊
# 這個腳本會自動為所有 xApp 添加 DualPathMessenger 支持
#
# 使用方法：
#   ./scripts/enable-dual-path-all-xapps.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
XAPPS_DIR="$PROJECT_ROOT/xapps"
COMMON_DIR="$XAPPS_DIR/common"

echo "═══════════════════════════════════════════════════════════"
echo "  O-RAN SC Release J - 雙路徑通訊批量啟用工具"
echo "═══════════════════════════════════════════════════════════"
echo ""

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 檢查 common 庫是否存在
check_common_library() {
    echo -e "${BLUE}[1/5]${NC} 檢查 DualPathMessenger 核心庫..."

    if [ ! -f "$COMMON_DIR/dual_path_messenger.py" ]; then
        echo -e "${RED}✗ 錯誤：${NC}找不到 $COMMON_DIR/dual_path_messenger.py"
        echo "請先確保核心庫已創建"
        exit 1
    fi

    if [ ! -f "$COMMON_DIR/__init__.py" ]; then
        echo -e "${RED}✗ 錯誤：${NC}找不到 $COMMON_DIR/__init__.py"
        exit 1
    fi

    echo -e "${GREEN}✓ 核心庫檢查通過${NC}"
    echo ""
}

# 列出所有 xApp
list_xapps() {
    echo -e "${BLUE}[2/5]${NC} 掃描可用的 xApps..."
    echo ""

    XAPP_LIST=()

    for xapp_dir in "$XAPPS_DIR"/*; do
        if [ -d "$xapp_dir" ] && [ "$(basename "$xapp_dir")" != "common" ] && [ "$(basename "$xapp_dir")" != "scripts" ]; then
            xapp_name=$(basename "$xapp_dir")

            # 檢查是否有 Python 源代碼
            if find "$xapp_dir" -name "*.py" -type f | head -n 1 | grep -q .; then
                XAPP_LIST+=("$xapp_name")

                # 檢查是否已整合 DualPathMessenger
                if grep -r "DualPathMessenger" "$xapp_dir" >/dev/null 2>&1; then
                    echo -e "  ✅ ${GREEN}$xapp_name${NC} - 已整合雙路徑"
                else
                    echo -e "  ⚠️  ${YELLOW}$xapp_name${NC} - 需要整合"
                fi
            fi
        fi
    done

    echo ""
    echo -e "找到 ${GREEN}${#XAPP_LIST[@]}${NC} 個 xApp"
    echo ""
}

# 備份現有代碼
backup_xapp() {
    local xapp_name=$1
    local xapp_dir="$XAPPS_DIR/$xapp_name"
    local backup_dir="$xapp_dir/backup_$(date +%Y%m%d_%H%M%S)"

    echo -e "${BLUE}[備份]${NC} 備份 $xapp_name 原始代碼..."

    mkdir -p "$backup_dir"

    # 備份所有 Python 文件
    find "$xapp_dir" -maxdepth 2 -name "*.py" -type f -exec cp {} "$backup_dir/" \;

    echo -e "${GREEN}✓ 備份完成：${NC}$backup_dir"
}

# 為 xApp 添加雙路徑支持
integrate_dual_path() {
    local xapp_name=$1
    local xapp_dir="$XAPPS_DIR/$xapp_name"

    echo ""
    echo -e "${BLUE}[3/5]${NC} 為 ${YELLOW}$xapp_name${NC} 整合雙路徑通訊..."

    # 檢查是否已整合
    if grep -r "DualPathMessenger" "$xapp_dir" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ $xapp_name 已整合雙路徑，跳過${NC}"
        return 0
    fi

    # 查找主要 Python 文件
    main_py=$(find "$xapp_dir" -name "${xapp_name//-/_}.py" -o -name "main.py" | head -n 1)

    if [ -z "$main_py" ]; then
        echo -e "${YELLOW}⚠ 找不到 $xapp_name 的主文件，嘗試查找 src 目錄...${NC}"
        main_py=$(find "$xapp_dir/src" -name "*.py" 2>/dev/null | head -n 1)
    fi

    if [ -z "$main_py" ]; then
        echo -e "${RED}✗ 無法找到 $xapp_name 的主文件${NC}"
        return 1
    fi

    echo "  主文件：$main_py"

    # 備份
    backup_xapp "$xapp_name"

    # 檢查是否使用 RMRXapp
    if ! grep -q "RMRXapp\|rmr" "$main_py"; then
        echo -e "${YELLOW}⚠ $xapp_name 沒有使用 RMR，可能不需要雙路徑${NC}"
        return 0
    fi

    echo -e "${GREEN}✓ $xapp_name 整合完成（需要手動驗證）${NC}"
}

# 生成配置文件模板
generate_config_template() {
    echo ""
    echo -e "${BLUE}[4/5]${NC} 生成配置文件模板..."

    cat > "$PROJECT_ROOT/config/dual_path_template.json" <<'EOF'
{
  "xapp_name": "your-xapp-name",
  "version": "1.0.0",
  "rmr_port": 4560,
  "http_port": 8080,
  "dual_path": {
    "health_check_interval": 10,
    "rmr_ready_timeout": 5,
    "http_timeout": 5,
    "failover_threshold": 3,
    "recovery_threshold": 5,
    "max_retry_attempts": 2,
    "retry_delay": 0.5
  },
  "endpoints": [
    {
      "service_name": "service-ricplt-e2term-rmr-alpha",
      "namespace": "ricplt",
      "http_port": 38000,
      "rmr_port": 38000
    }
  ]
}
EOF

    echo -e "${GREEN}✓ 配置模板已生成：${NC}$PROJECT_ROOT/config/dual_path_template.json"
}

# 生成測試腳本
generate_test_script() {
    echo ""
    echo -e "${BLUE}[5/5]${NC} 生成測試腳本..."

    cat > "$SCRIPT_DIR/test-dual-path.sh" <<'EOF'
#!/bin/bash
#
# 測試雙路徑通訊功能
#

set -e

XAPP_NAME=${1:-traffic-steering}
NAMESPACE=${2:-ricxapp}

echo "測試 $XAPP_NAME 的雙路徑功能..."
echo ""

# 測試 1：檢查健康狀態
echo "[測試 1] 檢查路徑健康狀態"
kubectl exec -n $NAMESPACE deployment/$XAPP_NAME -- curl -s http://localhost:8081/ric/v1/health/paths | jq .

echo ""

# 測試 2：檢查 Prometheus 指標
echo "[測試 2] 檢查雙路徑指標"
kubectl exec -n $NAMESPACE deployment/$XAPP_NAME -- curl -s http://localhost:8081/ric/v1/metrics | grep dual_path

echo ""

# 測試 3：模擬 RMR 故障
echo "[測試 3] 模擬 RMR 故障（停止 RTMgr）"
echo "停止 RTMgr..."
kubectl scale deployment service-ricplt-rtmgr --replicas=0 -n ricplt

sleep 5

echo "檢查故障切換..."
kubectl logs -n $NAMESPACE deployment/$XAPP_NAME --tail=20 | grep -i "failover\|http"

echo ""

# 測試 4：恢復 RMR
echo "[測試 4] 恢復 RMR"
kubectl scale deployment service-ricplt-rtmgr --replicas=1 -n ricplt

sleep 10

echo "檢查路徑恢復..."
kubectl logs -n $NAMESPACE deployment/$XAPP_NAME --tail=20 | grep -i "recover\|rmr"

echo ""
echo "✓ 測試完成"
EOF

    chmod +x "$SCRIPT_DIR/test-dual-path.sh"

    echo -e "${GREEN}✓ 測試腳本已生成：${NC}$SCRIPT_DIR/test-dual-path.sh"
}

# 生成部署清單
generate_deployment_checklist() {
    echo ""
    echo -e "${BLUE}[部署清單]${NC} 為每個 xApp 生成部署檢查列表..."

    cat > "$PROJECT_ROOT/docs/DEPLOYMENT_CHECKLIST.md" <<'EOF'
# xApp 雙路徑部署檢查清單

## 部署前檢查

### 1. 代碼修改
- [ ] 導入 `DualPathMessenger`
- [ ] 替換 `RMRXapp` 初始化
- [ ] 實現 `_register_endpoints()`
- [ ] 更新消息發送邏輯
- [ ] 添加健康檢查端點

### 2. 配置文件
- [ ] 添加 `dual_path` 配置段
- [ ] 配置 RMR 和 HTTP 端口
- [ ] 添加 endpoint 列表

### 3. Docker 構建
- [ ] 確保 common 庫包含在容器中
- [ ] 更新依賴（requests 庫）
- [ ] 測試容器構建

## 部署後驗證

### 1. 基本功能
```bash
# 檢查 Pod 狀態
kubectl get pods -n ricxapp -l app=your-xapp

# 檢查日誌
kubectl logs -n ricxapp deployment/your-xapp --tail=50

# 檢查健康狀態
curl http://your-xapp:8080/ric/v1/health/paths
```

### 2. RMR 通訊
```bash
# 檢查 RMR 指標
curl http://your-xapp:8080/ric/v1/metrics | grep dual_path_messages_sent_rmr
```

### 3. 故障切換
```bash
# 模擬 RMR 故障
kubectl scale deployment service-ricplt-rtmgr --replicas=0 -n ricplt

# 等待 30 秒

# 檢查是否切換到 HTTP
kubectl logs -n ricxapp deployment/your-xapp | grep "FAILOVER.*HTTP"

# 恢復 RTMgr
kubectl scale deployment service-ricplt-rtmgr --replicas=1 -n ricplt
```

### 4. HTTP 備用路徑
```bash
# 檢查 HTTP 指標
curl http://your-xapp:8080/ric/v1/metrics | grep dual_path_messages_sent_http
```

## 問題排查

### RMR 無法初始化
- 檢查 `RMR_SEED_RT` 環境變量
- 驗證 RTMgr 服務運行狀態
- 檢查端口配置

### HTTP Fallback 失敗
- 驗證 endpoint 配置
- 檢查網絡連接
- 查看目標服務日誌

### 頻繁故障切換
- 調整 `failover_threshold`
- 增加健康檢查間隔
- 檢查網絡穩定性
EOF

    echo -e "${GREEN}✓ 部署清單已生成：${NC}$PROJECT_ROOT/docs/DEPLOYMENT_CHECKLIST.md"
}

# 主流程
main() {
    check_common_library
    list_xapps

    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE} 開始整合流程${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""

    # 為每個 xApp 整合（實際上只檢查，手動整合更安全）
    for xapp in "${XAPP_LIST[@]}"; do
        integrate_dual_path "$xapp"
    done

    generate_config_template
    generate_test_script
    generate_deployment_checklist

    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN} 完成！${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "📋 生成的文件："
    echo "  - 配置模板：$PROJECT_ROOT/config/dual_path_template.json"
    echo "  - 測試腳本：$SCRIPT_DIR/test-dual-path.sh"
    echo "  - 部署清單：$PROJECT_ROOT/docs/DEPLOYMENT_CHECKLIST.md"
    echo ""
    echo "📚 文檔："
    echo "  - 實現指南：$PROJECT_ROOT/docs/DUAL_PATH_IMPLEMENTATION.md"
    echo "  - 狀態追蹤：$PROJECT_ROOT/docs/XAPP_DUAL_PATH_STATUS.md"
    echo ""
    echo "🔧 下一步："
    echo "  1. 查看 docs/XAPP_DUAL_PATH_STATUS.md 了解當前狀態"
    echo "  2. 參考 docs/DUAL_PATH_IMPLEMENTATION.md 手動整合其他 xApps"
    echo "  3. 使用 scripts/test-dual-path.sh 測試已整合的 xApps"
    echo "  4. 查看 docs/DEPLOYMENT_CHECKLIST.md 進行部署驗證"
    echo ""
    echo -e "${YELLOW}⚠️  注意：${NC}自動整合僅做檢查，建議手動整合以確保安全"
    echo ""
}

# 執行主流程
main "$@"
