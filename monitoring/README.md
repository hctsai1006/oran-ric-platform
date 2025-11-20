# O-RAN RIC Platform Monitoring

**O-RAN SC Release J - Dual-Path Communication Monitoring**

本目錄包含用於監控 O-RAN RIC 平台的 Grafana 和 Prometheus 配置。

---

## 📁 目錄結構

```
monitoring/
├── grafana/
│   ├── dashboards/
│   │   └── dual-path-communication.json    # 雙路徑通訊監控面板
│   └── grafana-dashboard-configmap.yaml    # Kubernetes ConfigMap
├── prometheus/
│   ├── alerts/
│   │   ├── dual-path-alerts.yml            # 雙路徑告警規則
│   │   └── xapp-alerts.yml                 # xApp 通用告警規則
│   └── prometheus-server-configmap-backup.yaml
└── README.md                                # 本文件
```

---

## 🚀 快速開始

### 1. 設置 Grafana Dashboard

#### 方法 A：自動設置（推薦）

```bash
# 在項目根目錄執行
./scripts/setup-grafana-dashboard.sh
```

這將自動：
- 檢測 Grafana 服務
- 建立 port-forward
- 導入 Dashboard
- 驗證安裝

#### 方法 B：手動導入

```bash
# Port-forward to Grafana
kubectl port-forward -n ricplt svc/grafana 3000:80

# 瀏覽器打開 http://localhost:3000
# 登錄後：Dashboards → Import → Upload JSON
# 選擇：monitoring/grafana/dashboards/dual-path-communication.json
```

#### 方法 C：Kubernetes ConfigMap

```bash
# 創建 ConfigMap
kubectl apply -f monitoring/grafana/grafana-dashboard-configmap.yaml

# 配置 Grafana 加載（見 docs/GRAFANA_DASHBOARD_SETUP.md）
```

### 2. 配置 Prometheus 告警

```bash
# 創建告警規則 ConfigMap
kubectl create configmap dual-path-alerts \
  --from-file=monitoring/prometheus/alerts/dual-path-alerts.yml \
  -n ricplt

# 重啟 Prometheus 以加載新規則
kubectl rollout restart statefulset -n ricplt r4-infrastructure-prometheus-server
```

### 3. 驗證設置

```bash
# 檢查 Grafana
kubectl get pod -n ricplt -l app=grafana

# 檢查 Prometheus
kubectl get pod -n ricplt -l app=prometheus

# 測試指標抓取
curl http://prometheus-server.ricplt/api/v1/query?query=dual_path_active_path
```

---

## 📊 Dashboard 功能

### 主要監控面板

1. **Active Communication Path**
   - 當前使用的通訊路徑（RMR/HTTP）
   - Gauge 顯示，藍色 = RMR，橙色 = HTTP

2. **Failover Event Rate**
   - 路徑切換頻率
   - 時間序列圖

3. **Message Success Rate by Path**
   - 各路徑的消息成功率
   - 目標：> 95%

4. **Path Health Status**
   - RMR 和 HTTP 路徑的健康狀態
   - 綠色 = 健康，紅色 = 不健康

5. **Message Latency by Path**
   - 各路徑的消息延遲
   - 毫秒級監控

6. **Message Throughput by Path**
   - 消息吞吐量
   - 按路徑和結果堆疊顯示

7. **Consecutive Failures**
   - 連續失敗計數
   - 達到 3 次觸發切換

8. **Registered Endpoints**
   - 各 xApp 註冊的端點數量
   - 餅圖顯示

### 過濾器

- **xApp**: 選擇特定 xApp（支援多選）
- **Namespace**: 選擇 Kubernetes namespace

### 自動刷新

預設每 10 秒刷新一次，可調整為：
- 5s, 10s, 30s, 1m, 5m, 15m, 30m, 1h

---

## 🚨 告警規則

### 告警級別

- **Critical**: 需要立即處理
- **Warning**: 需要關注，但非緊急

### 告警清單

| 告警名稱 | 級別 | 觸發條件 | 持續時間 |
|---------|------|---------|---------|
| FrequentDualPathFailover | Warning | 5分鐘內切換 > 3次 | 5m |
| DualPathStuckOnHTTP | Warning | 使用 HTTP 路徑 | 15m |
| HighMessageFailureRate | Critical | 失敗率 > 10% | 5m |
| RMRPathUnhealthy | Warning | RMR 不健康 | 5m |
| HTTPPathUnhealthy | Critical | HTTP 不健康 | 5m |
| BothPathsUnhealthy | Critical | 雙路徑都不健康 | 2m |
| HighMessageLatency | Warning | 延遲 > 500ms | 5m |
| ApproachingFailoverThreshold | Warning | 連續失敗 >= 2 | 1m |
| NoEndpointsRegistered | Warning | 無註冊端點 | 5m |
| NoMessageThroughput | Warning | 無消息發送 | 10m |

### 告警通知

配置 Alertmanager 發送通知到：
- Slack
- Email
- PagerDuty
- Webhook

參考 Prometheus 官方文檔配置。

---

## 📈 監控指標

### DualPathMessenger 指標

所有指標都以 `dual_path_` 為前綴：

```
# 當前使用的路徑（0=RMR, 1=HTTP）
dual_path_active_path

# 消息發送計數
dual_path_messages_sent_total{path="rmr|http", result="success|failure"}

# 故障切換事件
dual_path_failover_events_total

# 路徑健康狀態
dual_path_rmr_health_status
dual_path_http_health_status

# 消息延遲
dual_path_message_latency_seconds{path="rmr|http"}

# 連續失敗計數
dual_path_consecutive_failures{path="rmr|http"}

# 註冊的端點數量
dual_path_registered_endpoints
```

### 標籤

所有指標包含以下標籤：
- `app`: xApp 名稱（如 traffic-steering）
- `xapp_name`: xApp 實例名稱
- `namespace`: Kubernetes namespace
- `path`: 通訊路徑（rmr 或 http）
- `result`: 結果（success 或 failure）

---

## 🔍 使用示例

### 查詢當前活躍路徑

```promql
dual_path_active_path
```

### 查詢消息成功率

```promql
100 * (
  rate(dual_path_messages_sent_total{result="success"}[5m]) /
  rate(dual_path_messages_sent_total[5m])
)
```

### 查詢平均延遲

```promql
rate(dual_path_message_latency_seconds_sum[5m]) /
rate(dual_path_message_latency_seconds_count[5m])
```

### 查詢故障切換頻率

```promql
rate(dual_path_failover_events_total[5m])
```

---

## 🛠️ 維護

### 更新 Dashboard

```bash
# 修改 JSON 文件
vim monitoring/grafana/dashboards/dual-path-communication.json

# 重新導入
./scripts/setup-grafana-dashboard.sh
```

### 更新告警規則

```bash
# 修改告警文件
vim monitoring/prometheus/alerts/dual-path-alerts.yml

# 更新 ConfigMap
kubectl create configmap dual-path-alerts \
  --from-file=monitoring/prometheus/alerts/dual-path-alerts.yml \
  -n ricplt \
  --dry-run=client -o yaml | kubectl apply -f -

# 重啟 Prometheus
kubectl rollout restart statefulset -n ricplt r4-infrastructure-prometheus-server
```

### 備份配置

```bash
# 導出當前 Dashboard
curl -u admin:oran-ric-admin \
  http://localhost:3000/api/dashboards/uid/oran-dual-path | \
  jq '.dashboard' > backup-dashboard.json

# 導出 Prometheus 配置
kubectl get configmap -n ricplt r4-infrastructure-prometheus-server \
  -o yaml > backup-prometheus-config.yaml
```

---

## 📚 相關文檔

- [Grafana Dashboard 設置指南](../docs/GRAFANA_DASHBOARD_SETUP.md)
- [雙路徑實現文檔](../docs/DUAL_PATH_IMPLEMENTATION.md)
- [測試報告](../docs/COMPREHENSIVE_TEST_REPORT.md)
- [設置腳本](../scripts/setup-grafana-dashboard.sh)

---

## 🐛 故障排除

### Dashboard 沒有數據

1. 檢查 Prometheus 數據源配置
2. 檢查 xApp Pod 的 annotations
3. 檢查 Prometheus 抓取配置
4. 測試指標端點

```bash
# 檢查 xApp 指標
kubectl exec -n ricxapp deploy/traffic-steering -- curl localhost:8080/metrics

# 檢查 Prometheus 目標
kubectl port-forward -n ricplt sts/r4-infrastructure-prometheus-server 9090:9090
# 瀏覽器打開：http://localhost:9090/targets
```

### 告警不觸發

1. 檢查 Prometheus 是否加載了告警規則
2. 檢查 Alertmanager 配置
3. 驗證告警表達式

```bash
# 檢查告警規則
curl http://localhost:9090/api/v1/rules

# 檢查告警狀態
curl http://localhost:9090/api/v1/alerts
```

---

## 👥 支持

如有問題，請：

1. 查看文檔：`docs/GRAFANA_DASHBOARD_SETUP.md`
2. 檢查日誌：`kubectl logs -n ricplt -l app=grafana`
3. 提交 Issue：專案 Issue tracker

---

**監控愉快！** 📊
