#!/bin/bash

# O-RAN RIC Monitoring Services Port Forwarding
# 用於透過 VS Code Remote SSH 存取監控介面

echo "=========================================="
echo "Starting Port Forwards for Monitoring"
echo "=========================================="
echo ""

# 停止現有的 port-forward
echo "Stopping existing port-forwards..."
pkill -f "kubectl port-forward" 2>/dev/null
sleep 2

# 1. Grafana (port 3000)
echo "Starting Grafana on localhost:3000..."
kubectl port-forward -n ricplt svc/oran-grafana 3000:80 > /tmp/grafana-port-forward.log 2>&1 &
GRAFANA_PID=$!

# 2. Prometheus (port 9090)
echo "Starting Prometheus on localhost:9090..."
kubectl port-forward -n ricplt svc/r4-infrastructure-prometheus-server 9090:80 > /tmp/prometheus-port-forward.log 2>&1 &
PROMETHEUS_PID=$!

# 3. KPIMON Metrics (port 8080)
echo "Starting KPIMON Metrics on localhost:8080..."
kubectl port-forward -n ricxapp svc/kpimon 8080:8080 > /tmp/kpimon-metrics-port-forward.log 2>&1 &
KPIMON_METRICS_PID=$!

# 4. KPIMON Beam API (port 8081)
echo "Starting KPIMON Beam API on localhost:8081..."
kubectl port-forward -n ricxapp svc/kpimon 8081:8081 > /tmp/kpimon-beam-api-port-forward.log 2>&1 &
KPIMON_API_PID=$!

# 5. InfluxDB (port 8086) - optional
echo "Starting InfluxDB on localhost:8086..."
kubectl port-forward -n ricplt svc/ricplt-influxdb 8086:8086 > /tmp/influxdb-port-forward.log 2>&1 &
INFLUXDB_PID=$!

# Wait for port-forwards to start
sleep 3

echo ""
echo "=========================================="
echo "✅ Port Forwards Started Successfully"
echo "=========================================="
echo ""
echo "Services available on localhost:"
echo "  📊 Grafana:           http://localhost:3000"
echo "  📈 Prometheus:        http://localhost:9090"
echo "  📡 KPIMON Metrics:    http://localhost:8080/metrics"
echo "  🎯 Beam API:          http://localhost:8081/api/beam/5/kpi"
echo "  💾 InfluxDB:          http://localhost:8086"
echo ""
echo "Process IDs:"
echo "  Grafana:     $GRAFANA_PID"
echo "  Prometheus:  $PROMETHEUS_PID"
echo "  KPIMON:      $KPIMON_METRICS_PID"
echo "  Beam API:    $KPIMON_API_PID"
echo "  InfluxDB:    $INFLUXDB_PID"
echo ""
echo "=========================================="
echo "VS Code 使用說明:"
echo "=========================================="
echo ""
echo "1. 在 VS Code 底部狀態列，點擊 'PORTS' 標籤"
echo "2. 你會看到以下 port 自動被偵測:"
echo "   - 3000 (Grafana)"
echo "   - 9090 (Prometheus)"
echo "   - 8080 (KPIMON Metrics)"
echo "   - 8081 (Beam API)"
echo "   - 8086 (InfluxDB)"
echo ""
echo "3. 點擊 port 號碼旁的 '地球圖示' 🌐 即可在瀏覽器開啟"
echo ""
echo "或是直接在本地瀏覽器輸入 http://localhost:3000"
echo ""
echo "=========================================="
echo "停止 Port Forwards:"
echo "=========================================="
echo ""
echo "方法 1: 按下 Ctrl+C (如果腳本在前景執行)"
echo "方法 2: 執行: pkill -f 'kubectl port-forward'"
echo "方法 3: 執行: kill $GRAFANA_PID $PROMETHEUS_PID $KPIMON_METRICS_PID $KPIMON_API_PID $INFLUXDB_PID"
echo ""
echo "Log 檔案位置: /tmp/*-port-forward.log"
echo ""
echo "Port forwards running in background..."
echo "Press Ctrl+C to stop monitoring (port-forwards will continue)"
echo ""

# Keep script running to show logs
tail -f /tmp/grafana-port-forward.log /tmp/prometheus-port-forward.log /tmp/kpimon-metrics-port-forward.log /tmp/kpimon-beam-api-port-forward.log 2>/dev/null
