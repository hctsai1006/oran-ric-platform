#!/bin/bash
# Beam KPI Query API - Example Requests
# Demonstrates various API usage patterns

set -e

# Configuration
API_BASE="http://localhost:30081/api"
BEAM_ID=1

echo "======================================================"
echo "Beam KPI Query API - Example Requests"
echo "======================================================"
echo "API Base URL: $API_BASE"
echo "Target Beam ID: $BEAM_ID"
echo "======================================================"
echo ""

# Function to print section headers
print_section() {
    echo ""
    echo "------------------------------------------------------"
    echo "$1"
    echo "------------------------------------------------------"
}

# Function to execute and display curl command
execute_curl() {
    local description=$1
    local url=$2
    local params=$3

    print_section "$description"

    if [ -n "$params" ]; then
        echo "GET $url?$params"
        echo ""
        curl -s "$url?$params" | jq '.'
    else
        echo "GET $url"
        echo ""
        curl -s "$url" | jq '.'
    fi
}

# Example 1: Health Check
execute_curl \
    "Example 1: Health Check - Verify API is alive" \
    "$API_BASE/../health/alive"

# Example 2: Get Current KPIs for Beam 1 (All KPIs)
execute_curl \
    "Example 2: Get Current KPIs for Beam 1 (All KPIs)" \
    "$API_BASE/beam/$BEAM_ID/kpi" \
    "kpi_type=all&time_range=current"

# Example 3: Get Signal Quality Only (RSRP, RSRQ, SINR)
execute_curl \
    "Example 3: Get Signal Quality Only (RSRP, RSRQ, SINR)" \
    "$API_BASE/beam/$BEAM_ID/kpi" \
    "kpi_type=rsrp,rsrq,sinr&time_range=current"

# Example 4: Get Throughput Metrics Only
execute_curl \
    "Example 4: Get Throughput Metrics Only" \
    "$API_BASE/beam/$BEAM_ID/kpi" \
    "kpi_type=throughput_dl,throughput_ul&time_range=current"

# Example 5: Get Historical Data (Last 15 minutes, averaged)
execute_curl \
    "Example 5: Get Historical Data (Last 15 minutes, averaged)" \
    "$API_BASE/beam/$BEAM_ID/kpi" \
    "kpi_type=rsrp,rsrq,sinr&time_range=last_15m&aggregation=mean"

# Example 6: Get Historical Data (Last 1 hour, max values)
execute_curl \
    "Example 6: Get Historical Data (Last 1 hour, max values)" \
    "$API_BASE/beam/$BEAM_ID/kpi" \
    "kpi_type=sinr&time_range=last_1h&aggregation=max"

# Example 7: Get Time-Series Data for RSRP
print_section "Example 7: Get Time-Series Data for RSRP (30s intervals)"
echo "GET $API_BASE/beam/$BEAM_ID/kpi/timeseries?kpi_type=rsrp&interval=30s"
echo ""
curl -s "$API_BASE/beam/$BEAM_ID/kpi/timeseries?kpi_type=rsrp&interval=30s" | jq '.'

# Example 8: List All Active Beams
execute_curl \
    "Example 8: List All Active Beams" \
    "$API_BASE/beam/list"

# Example 9: List Beams with Good Signal (RSRP > -95 dBm)
execute_curl \
    "Example 9: List Beams with Good Signal (RSRP > -95 dBm)" \
    "$API_BASE/beam/list" \
    "min_rsrp=-95"

# Example 10: List Beams for Specific Cell
execute_curl \
    "Example 10: List Beams for Specific Cell" \
    "$API_BASE/beam/list" \
    "cell_id=cell_001"

# Example 11: Query Beam 2 (Different Beam)
execute_curl \
    "Example 11: Query Beam 2 (Different Beam)" \
    "$API_BASE/beam/2/kpi" \
    "kpi_type=all&time_range=current"

# Example 12: Error Case - Invalid Beam ID
print_section "Example 12: Error Case - Invalid Beam ID (should return 400)"
echo "GET $API_BASE/beam/999/kpi"
echo ""
curl -s "$API_BASE/beam/999/kpi" | jq '.'

# Example 13: Get KPIs for Specific UE
execute_curl \
    "Example 13: Get KPIs for Specific UE on Beam 1" \
    "$API_BASE/beam/$BEAM_ID/kpi" \
    "kpi_type=all&ue_id=ue_005"

# Example 14: Compare Beam Performance
print_section "Example 14: Compare Beam 1 vs Beam 2 Signal Quality"
echo "Beam 1:"
curl -s "$API_BASE/beam/1/kpi?kpi_type=rsrp,rsrq,sinr" | jq '.data.signal_quality'
echo ""
echo "Beam 2:"
curl -s "$API_BASE/beam/2/kpi?kpi_type=rsrp,rsrq,sinr" | jq '.data.signal_quality'

echo ""
echo "======================================================"
echo "All examples completed!"
echo "======================================================"
