#!/bin/bash
#
# Grafana Dashboard Import Script
# Author: Tsai Hsiu-Chi (thc1006)
# Date: 2025-11-15
#
# This script imports Grafana dashboards from JSON files into the Grafana instance

set -e

GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
GRAFANA_USER="${GRAFANA_USER:-admin}"
GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-oran-ric-admin}"
DASHBOARD_DIR="/home/thc1006/oran-ric-platform/config/dashboards"

echo "Importing Grafana dashboards..."
echo "Grafana URL: $GRAFANA_URL"

# Function to import a dashboard
import_dashboard() {
    local dashboard_file=$1
    local dashboard_name=$(basename "$dashboard_file" .json)

    echo "Importing dashboard: $dashboard_name"

    # Read the dashboard JSON
    dashboard_json=$(cat "$dashboard_file")

    # Check if the JSON already has a "dashboard" wrapper
    has_wrapper=$(echo "$dashboard_json" | jq 'has("dashboard")' 2>/dev/null || echo "false")

    if [ "$has_wrapper" = "true" ]; then
        # Already wrapped, just add overwrite flag
        import_payload=$(echo "$dashboard_json" | jq '. + {overwrite: true, message: "Imported by automation script"}')
    else
        # Need to wrap the dashboard
        import_payload=$(cat <<EOF
{
  "dashboard": $dashboard_json,
  "overwrite": true,
  "message": "Imported by automation script"
}
EOF
)
    fi

    # Import the dashboard
    response=$(curl -s -w "\n%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "$import_payload" \
        -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
        "$GRAFANA_URL/api/dashboards/db")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ]; then
        uid=$(echo "$body" | jq -r '.uid // "unknown"')
        echo "  ✓ Successfully imported dashboard with UID: $uid"
        echo "  URL: $GRAFANA_URL/d/$uid"
    else
        echo "  ✗ Failed to import dashboard (HTTP $http_code)"
        echo "  Response: $body"
    fi
}

# Import all dashboards
for dashboard_file in "$DASHBOARD_DIR"/*.json; do
    if [ -f "$dashboard_file" ]; then
        import_dashboard "$dashboard_file"
    fi
done

echo ""
echo "Dashboard import complete!"
echo "You can now access the dashboards at: $GRAFANA_URL"
