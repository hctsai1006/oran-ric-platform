#!/bin/bash
###############################################################################
# Web UI Proxy Server 啟動腳本
#
# 功能：
# - 檢查 port 是否被佔用
# - 停止舊的進程
# - 啟動新的 proxy server
# - 驗證啟動成功
#
# Author: 蔡秀吉 (thc1006)
# Date: 2025-11-19
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PORT=8888
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PROXY_DIR="$PROJECT_ROOT/frontend-beam-query"
LOG_FILE="/tmp/beam-ui-proxy.log"

echo "============================================================================"
echo "🚀 Web UI Proxy Server 啟動腳本"
echo "============================================================================"
echo ""

# Step 1: Check if port is in use
echo "📍 檢查 port $PORT 狀態..."
if lsof -i :$PORT > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Port $PORT 已被使用${NC}"
    echo ""
    echo "正在使用的進程："
    lsof -i :$PORT
    echo ""

    # Kill old processes
    OLD_PIDS=$(lsof -t -i :$PORT 2>/dev/null || true)
    if [ -n "$OLD_PIDS" ]; then
        echo -e "${YELLOW}🔪 停止舊的進程: $OLD_PIDS${NC}"
        kill -9 $OLD_PIDS 2>/dev/null || true
        sleep 1
        echo -e "${GREEN}✅ 舊進程已停止${NC}"
    fi
else
    echo -e "${GREEN}✅ Port $PORT 可用${NC}"
fi
echo ""

# Step 2: Stop old proxy server processes
echo "📍 檢查舊的 proxy server 進程..."
OLD_PROXY_PIDS=$(pgrep -f "waitress-serve.*wsgi_app" || true)
if [ -z "$OLD_PROXY_PIDS" ]; then
    # Also check for old Python-based proxy servers
    OLD_PROXY_PIDS=$(pgrep -f "python3.*proxy-server.*\.py" || true)
fi

if [ -n "$OLD_PROXY_PIDS" ]; then
    echo -e "${YELLOW}🔪 發現舊的 proxy server 進程: $OLD_PROXY_PIDS${NC}"
    kill -9 $OLD_PROXY_PIDS 2>/dev/null || true
    sleep 1
    echo -e "${GREEN}✅ 舊進程已清理${NC}"
else
    echo -e "${GREEN}✅ 沒有舊的 proxy server 進程${NC}"
fi
echo ""

# Step 3: Backup old log
if [ -f "$LOG_FILE" ]; then
    BACKUP_LOG="$LOG_FILE.$(date +%Y%m%d-%H%M%S)"
    echo "📦 備份舊日誌: $LOG_FILE -> $BACKUP_LOG"
    mv "$LOG_FILE" "$BACKUP_LOG"
    # Keep only last 5 backups
    ls -t /tmp/beam-ui-proxy.log.* 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
fi
echo ""

# Step 4: Start new server
echo "🚀 啟動新的 Web UI Proxy Server (WSGI/waitress)..."
cd "$PROXY_DIR"

# Check if waitress is available
if ! command -v waitress-serve &> /dev/null; then
    echo -e "${RED}❌ waitress 未安裝！${NC}"
    echo "   請執行：pip3 install --user waitress"
    exit 1
fi

# Check if WSGI app exists
if [ ! -f "wsgi_app.py" ]; then
    echo -e "${RED}❌ wsgi_app.py 不存在！${NC}"
    exit 1
fi

# Start waitress in background
echo "   使用 WSGI app：wsgi_app:application"
nohup waitress-serve --host=0.0.0.0 --port=$PORT wsgi_app:application > "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo -e "${GREEN}✅ 已啟動，PID: $NEW_PID${NC}"
echo ""

# Step 5: Wait for server to start
echo "⏳ 等待伺服器啟動..."
sleep 3

# Step 6: Verify server is running
echo "🔍 驗證伺服器狀態..."

# Check process
if ps -p $NEW_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 進程運行中 (PID: $NEW_PID)${NC}"
else
    echo -e "${RED}❌ 進程已停止！${NC}"
    echo ""
    echo "日誌內容："
    tail -20 "$LOG_FILE"
    exit 1
fi

# Check port
if lsof -i :$PORT > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Port $PORT 監聽中${NC}"
else
    echo -e "${RED}❌ Port $PORT 未監聽！${NC}"
    echo ""
    echo "日誌內容："
    tail -20 "$LOG_FILE"
    exit 1
fi

# Check HTTP response
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ HTTP 回應正常 (200 OK)${NC}"
else
    echo -e "${RED}❌ HTTP 回應異常 ($HTTP_CODE)${NC}"
fi

echo ""
echo "============================================================================"
echo -e "${GREEN}🎉 Web UI Proxy Server 啟動成功！${NC}"
echo "============================================================================"
echo ""
echo "📱 瀏覽器訪問："
echo "   本機: http://localhost:$PORT"
echo "   遠端: http://$(hostname -I | awk '{print $1}'):$PORT"
echo ""
echo "📝 日誌檔案："
echo "   tail -f $LOG_FILE"
echo ""
echo "🔍 進程資訊："
echo "   PID: $NEW_PID"
echo "   ps -p $NEW_PID -o pid,cmd,stat,etime"
echo ""
echo "🛑 停止伺服器："
echo "   kill $NEW_PID"
echo ""
echo "============================================================================"
