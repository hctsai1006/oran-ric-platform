#!/bin/bash
###############################################################################
# Web UI Proxy Server 健康檢查腳本
#
# 功能：
# - 檢查進程是否存在
# - 檢查 port 是否監聽
# - 檢查 HTTP 是否回應
# - 自動重啟（如果配置）
#
# 使用方式：
#   手動檢查：./health-check-web-ui.sh
#   自動重啟：./health-check-web-ui.sh --auto-restart
#   Cron：     */5 * * * * /path/to/health-check-web-ui.sh --auto-restart >> /tmp/health-check.log 2>&1
#
# Author: 蔡秀吉 (thc1006)
# Date: 2025-11-19
###############################################################################

set -e

# Configuration
PORT=8888
API_URL="http://localhost:$PORT/"
TIMEOUT=3
AUTO_RESTART=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/tmp/beam-ui-health-check.log"

# Parse arguments
if [ "$1" = "--auto-restart" ]; then
    AUTO_RESTART=true
fi

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Colors (only for interactive)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

# Health check functions
check_process() {
    # Check for waitress-serve process first
    if pgrep -f "waitress-serve.*wsgi_app" > /dev/null; then
        return 0
    # Fallback to old Python-based proxy
    elif pgrep -f "python3.*proxy-server.*\.py" > /dev/null; then
        return 0
    else
        return 1
    fi
}

check_port() {
    if lsof -i :$PORT > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

check_http() {
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -m $TIMEOUT "$API_URL" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        return 0
    else
        return 1
    fi
}

# Restart function
restart_server() {
    log "${YELLOW}🔄 嘗試重啟 Web UI Proxy Server...${NC}"

    if [ -f "$SCRIPT_DIR/start-web-ui.sh" ]; then
        bash "$SCRIPT_DIR/start-web-ui.sh" >> "$LOG_FILE" 2>&1
        log "${GREEN}✅ 重啟完成${NC}"
        return 0
    else
        log "${RED}❌ 找不到啟動腳本: $SCRIPT_DIR/start-web-ui.sh${NC}"
        return 1
    fi
}

# Main health check
log "======================================================================"
log "🏥 Web UI Proxy Server 健康檢查開始"
log "======================================================================"

HEALTHY=true

# Check 1: Process
log "📍 檢查進程..."
if check_process; then
    PID=$(pgrep -f "waitress-serve.*wsgi_app" | head -1)
    if [ -z "$PID" ]; then
        PID=$(pgrep -f "python3.*proxy-server.*\.py" | head -1)
    fi
    log "${GREEN}✅ 進程運行中 (PID: $PID)${NC}"
else
    log "${RED}❌ 進程不存在${NC}"
    HEALTHY=false
fi

# Check 2: Port
log "📍 檢查 Port $PORT..."
if check_port; then
    log "${GREEN}✅ Port 監聽中${NC}"
else
    log "${RED}❌ Port 未監聽${NC}"
    HEALTHY=false
fi

# Check 3: HTTP
log "📍 檢查 HTTP 回應..."
if check_http; then
    log "${GREEN}✅ HTTP 回應正常 (200 OK)${NC}"
else
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -m $TIMEOUT "$API_URL" 2>/dev/null || echo "000")
    log "${RED}❌ HTTP 回應異常 (Code: $HTTP_CODE)${NC}"
    HEALTHY=false
fi

# Summary
log "----------------------------------------------------------------------"
if [ "$HEALTHY" = true ]; then
    log "${GREEN}✅ 健康檢查通過！所有檢查項目正常${NC}"
    log "======================================================================"
    exit 0
else
    log "${RED}❌ 健康檢查失敗！檢測到異常${NC}"

    if [ "$AUTO_RESTART" = true ]; then
        log "🔄 自動重啟模式已啟用，準備重啟..."
        if restart_server; then
            log "${GREEN}✅ 自動重啟成功${NC}"
            log "======================================================================"
            exit 0
        else
            log "${RED}❌ 自動重啟失敗${NC}"
            log "======================================================================"
            exit 1
        fi
    else
        log "💡 提示：使用 --auto-restart 參數可自動重啟"
        log "   或手動執行: $SCRIPT_DIR/start-web-ui.sh"
        log "======================================================================"
        exit 1
    fi
fi
