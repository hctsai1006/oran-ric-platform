#!/bin/bash
#
# Beam KPI Query Tool - 極簡版
# 用途: 輸入 Beam ID，返回該 Beam 的 KPI 數據
#
# 使用方式:
#   ./scripts/query-beam.sh 1              # 查詢 Beam 1 的所有 KPI
#   ./scripts/query-beam.sh 2 throughput   # 查詢 Beam 2 的吞吐量
#   ./scripts/query-beam.sh 5 signal       # 查詢 Beam 5 的信號品質
#

BEAM_ID=${1:-1}
KPI_TYPE=${2:-all}
API_URL="http://localhost:8081"

# 顏色輸出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================================="
echo -e "${BLUE}🔍 Beam KPI Query Tool${NC}"
echo "=================================================="
echo ""

# 參數驗證
if ! [[ "$BEAM_ID" =~ ^[0-9]+$ ]]; then
    echo "X 錯誤: Beam ID 必須是數字"
    echo "使用方式: $0 <beam_id> [kpi_type]"
    echo "範例: $0 1 signal_quality"
    exit 1
fi

# 建構 API URL
if [ "$KPI_TYPE" == "all" ]; then
    QUERY_URL="${API_URL}/api/beam/${BEAM_ID}/kpi"
else
    QUERY_URL="${API_URL}/api/beam/${BEAM_ID}/kpi?kpi_type=${KPI_TYPE}"
fi

echo -e "${YELLOW} 查詢 Beam ID:${NC} $BEAM_ID"
if [ "$KPI_TYPE" != "all" ]; then
    echo -e "${YELLOW} KPI 類型:${NC} $KPI_TYPE"
fi
echo ""

# 查詢 API
echo -e "${GREEN}正在查詢...${NC}"
echo ""

RESPONSE=$(curl -s "$QUERY_URL")

# 檢查是否成功
if echo "$RESPONSE" | grep -q '"status":"success"'; then
    echo "O 查詢成功！"
    echo ""
    echo "=================================================="
    echo " Beam $BEAM_ID KPI 數據"
    echo "=================================================="
    echo ""

    # 美化輸出
    if command -v jq &> /dev/null; then
        # 使用 jq 美化
        echo "$RESPONSE" | jq '.'
    else
        # 無 jq，直接輸出 JSON
        echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    fi

else
    echo "X 查詢失敗"
    echo "$RESPONSE"
    exit 1
fi

echo ""
echo "=================================================="
echo -e "${BLUE} 用法:${NC}"
echo "=================================================="
echo ""
echo "可用的 KPI 類型:"
echo "  - all              (所有 KPI，預設)"
echo "  - throughput       (吞吐量)"
echo "  - signal_quality   (信號品質)"
echo "  - packet_loss      (封包遺失率)"
echo "  - resource_utilization  (資源利用率)"
echo ""
echo "範例:"
echo "  $0 1               # Beam 1 所有 KPI"
echo "  $0 2 throughput    # Beam 2 吞吐量"
echo "  $0 5 signal_quality # Beam 5 信號品質"
echo ""
