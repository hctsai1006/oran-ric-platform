# Grafana Dashboard Setup Guide

**O-RAN SC Release J - Dual-Path Communication Monitoring**

本指南說明如何設置 Grafana Dashboard 來監控雙路徑通訊系統。

---

## 📊 Dashboard 功能

我們創建的 Dashboard 包含以下監控面板：

### 1. 通訊路徑狀態
- **Active Communication Path** - 當前使用的通訊路徑（RMR/HTTP）
- **Path Health Status** - 兩個路徑的健康狀態

### 2. 故障切換監控
- **Failover Event Rate** - 故障切換發生頻率
- **Total Failover Events** - 總故障切換次數
- **Consecutive Failures** - 連續失敗計數（達到 3 次觸發切換）

### 3. 消息傳輸監控
- **Message Success Rate by Path** - 各路徑消息成功率
- **Message Throughput by Path** - 各路徑消息吞吐量
- **Message Latency by Path** - 各路徑消息延遲

### 4. 端點配置
- **Registered Endpoints by xApp** - 各 xApp 註冊的端點數量

---

## 🚀 快速開始

### 方法 1：自動設置（推薦）

使用我們提供的 CLI 腳本自動設置：

```bash
# 在集群內自動檢測 Grafana 並設置
./scripts/setup-grafana-dashboard.sh

# 或指定 Grafana URL
./scripts/setup-grafana-dashboard.sh -g http://grafana.example.com:3000

# 使用自定義憑證
./scripts/setup-grafana-dashboard.sh \
  -g http://localhost:3000 \
  -u admin \
  -p your-password
```

**腳本會自動：**
1. ✅ 檢測 Grafana 服務
2. ✅ 建立 port-forward 連接
3. ✅ 驗證 Prometheus 數據源
4. ✅ 導入 Dashboard
5. ✅ 驗證安裝成功

### 方法 2：手動導入

#### 步驟 1：訪問 Grafana

```bash
# Port-forward to Grafana
kubectl port-forward -n ricplt svc/grafana 3000:80

# 瀏覽器打開
# http://localhost:3000
```

#### 步驟 2：登錄 Grafana

- **用戶名**：admin
- **密碼**：oran-ric-admin（或查看 `config/grafana-values.yaml`）

#### 步驟 3：導入 Dashboard

1. 點擊左側菜單 **「+」** → **「Import」**
2. 點擊 **「Upload JSON file」**
3. 選擇文件：`monitoring/grafana/dashboards/dual-path-communication.json`
4. 點擊 **「Import」**

### 方法 3：Kubernetes ConfigMap（自動加載）

在 Kubernetes 中部署 Dashboard ConfigMap：

```bash
# 創建 ConfigMap
kubectl apply -f monitoring/grafana/grafana-dashboard-configmap.yaml

# 驗證
kubectl get configmap -n ricplt grafana-dual-path-dashboard
```

然後更新 Grafana Helm values：

```yaml
# config/grafana-values.yaml
dashboardsConfigMaps:
  - configMapName: grafana-dual-path-dashboard
    fileName: dual-path-communication.json
```

重新部署 Grafana：

```bash
helm upgrade grafana ric-dep/infrastructure \
  -n ricplt \
  -f config/grafana-values.yaml
```

---

## 🔧 配置 Prometheus 數據源

Dashboard 需要 Prometheus 作為數據源。

### 檢查數據源

```bash
# 通過 API 檢查
curl -u admin:oran-ric-admin \
  http://localhost:3000/api/datasources | jq '.[] | select(.type=="prometheus")'
```

### 手動添加數據源

如果沒有 Prometheus 數據源：

1. 進入 **Configuration** → **Data Sources**
2. 點擊 **「Add data source」**
3. 選擇 **Prometheus**
4. 配置：
   - **Name**: Prometheus
   - **URL**: `http://r4-infrastructure-prometheus-server.ricplt:80`
   - **Access**: Server (default)
5. 點擊 **「Save & Test」**

### 自動配置（Helm）

在 `config/grafana-values.yaml` 中已配置：

```yaml
datasources:
  datasources.yaml:
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      url: http://r4-infrastructure-prometheus-server.ricplt:80
      access: proxy
      isDefault: true
```

---

## 📈 使用 Dashboard

### 訪問 Dashboard

1. 登錄 Grafana
2. 進入 **Dashboards** → **Browse**
3. 找到 **「O-RAN RIC - Dual-Path Communication」**
4. 點擊打開

或直接訪問：
```
http://localhost:3000/d/oran-dual-path
```

### 過濾器

Dashboard 提供兩個過濾器：

- **xApp** - 選擇要監控的 xApp（可多選）
- **Namespace** - 選擇 Kubernetes namespace（可多選）

### 自動刷新

Dashboard 默認每 10 秒自動刷新。可以在右上角調整：

- 5s, 10s, 30s, 1m, 5m, 15m, 30m, 1h

### 時間範圍

默認顯示最近 1 小時數據。可以在右上角調整。

---

## 🔍 監控指標說明

### dual_path_active_path
- **類型**：Gauge
- **值**：0 = RMR, 1 = HTTP
- **含義**：當前使用的通訊路徑

### dual_path_messages_sent_total
- **類型**：Counter
- **標籤**：path (rmr/http), result (success/failure)
- **含義**：已發送的消息總數

### dual_path_failover_events_total
- **類型**：Counter
- **含義**：路徑切換事件總數

### dual_path_rmr_health_status / dual_path_http_health_status
- **類型**：Gauge
- **值**：1 = Healthy, 0 = Unhealthy
- **含義**：路徑健康狀態

### dual_path_message_latency_seconds
- **類型**：Histogram
- **標籤**：path (rmr/http)
- **含義**：消息延遲分布

### dual_path_consecutive_failures
- **類型**：Gauge
- **標籤**：path (rmr/http)
- **含義**：當前連續失敗次數（達到 3 次觸發切換）

### dual_path_registered_endpoints
- **類型**：Gauge
- **含義**：已註冊的端點數量

---

## 🎯 監控場景

### 場景 1：正常運行

**預期狀態**：
- Active Path = **RMR** (藍色)
- Message Success Rate = **100%** (綠色)
- Failover Events = **0**
- Both Paths = **Healthy** (綠色)

### 場景 2：RMR 故障 → HTTP 接管

**觀察指標**：
1. **Consecutive Failures** 從 0 → 1 → 2 → 3
2. **Failover Event** 發生（計數器 +1）
3. **Active Path** 從 RMR → **HTTP** (藍色 → 橙色)
4. **RMR Health** 變為 **Unhealthy** (紅色)
5. **Message Success Rate** 保持高（透過 HTTP 發送）

### 場景 3：RMR 恢復 → 切回 RMR

**觀察指標**：
1. **RMR Health** 恢復為 **Healthy** (綠色)
2. RMR 連續成功達到 5 次
3. **Failover Event** 發生（計數器 +1）
4. **Active Path** 從 HTTP → **RMR** (橙色 → 藍色)

### 場景 4：頻繁切換（問題狀態）

**警告信號**：
- **Failover Events** 頻繁增加
- **Consecutive Failures** 持續在 2-3 之間波動
- **Message Success Rate** 下降

**可能原因**：
- 網絡不穩定
- RMR 路由配置問題
- 資源不足

---

## 🚨 告警設置

### 建議的告警規則

#### 告警 1：頻繁故障切換

```yaml
- alert: FrequentDualPathFailover
  expr: increase(dual_path_failover_events_total[5m]) > 3
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "頻繁的雙路徑故障切換"
    description: "xApp {{ $labels.app }} 在 5 分鐘內切換了 {{ $value }} 次"
```

#### 告警 2：HTTP 路徑長時間使用

```yaml
- alert: DualPathStuckOnHTTP
  expr: dual_path_active_path == 1
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "長時間使用 HTTP 路徑"
    description: "xApp {{ $labels.app }} 已使用 HTTP 路徑超過 15 分鐘"
```

#### 告警 3：消息失敗率高

```yaml
- alert: HighMessageFailureRate
  expr: |
    100 * (
      rate(dual_path_messages_sent_total{result="failure"}[5m]) /
      rate(dual_path_messages_sent_total[5m])
    ) > 10
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "消息失敗率過高"
    description: "xApp {{ $labels.app }} 在 {{ $labels.path }} 路徑上的失敗率為 {{ $value }}%"
```

### 添加告警到 Prometheus

```bash
# 編輯 Prometheus 配置
kubectl edit configmap -n ricplt r4-infrastructure-prometheus-server

# 添加告警規則到 alerting_rules.yml
# 或使用單獨的告警文件
kubectl apply -f monitoring/prometheus/alerts/dual-path-alerts.yml
```

---

## 🐛 故障排除

### 問題 1：Dashboard 顯示「No Data」

**可能原因**：
1. Prometheus 數據源未配置
2. xApp 未暴露指標
3. Prometheus 未抓取到指標

**解決方法**：

```bash
# 1. 檢查 Prometheus 數據源
curl -u admin:oran-ric-admin \
  http://localhost:3000/api/datasources

# 2. 檢查 xApp 指標端點
kubectl exec -n ricxapp deploy/traffic-steering -- \
  curl localhost:8080/metrics

# 3. 檢查 Prometheus 抓取配置
kubectl exec -n ricplt sts/r4-infrastructure-prometheus-server -- \
  cat /etc/prometheus/prometheus.yml

# 4. 測試 Prometheus 查詢
curl 'http://prometheus-server.ricplt/api/v1/query?query=dual_path_active_path'
```

### 問題 2：指標不完整

**檢查 Pod 標註**：

```bash
kubectl get pod -n ricxapp -l app=traffic-steering -o yaml | \
  grep -A 5 annotations
```

**應該包含**：
```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8080"
  prometheus.io/path: "/metrics"
```

### 問題 3：無法連接 Grafana

**檢查 Grafana Pod**：

```bash
kubectl get pod -n ricplt -l app=grafana
kubectl logs -n ricplt -l app=grafana
```

**重啟 Grafana**：

```bash
kubectl rollout restart deployment -n ricplt grafana
```

---

## 📚 參考文檔

### 相關文件
- Dashboard JSON: `monitoring/grafana/dashboards/dual-path-communication.json`
- 設置腳本: `scripts/setup-grafana-dashboard.sh`
- Grafana 配置: `config/grafana-values.yaml`
- Prometheus 配置: `config/prometheus-values.yaml`

### 相關指南
- 雙路徑實現: `docs/DUAL_PATH_IMPLEMENTATION.md`
- 測試報告: `docs/COMPREHENSIVE_TEST_REPORT.md`
- 部署腳本: `scripts/enable-dual-path-all-xapps.sh`

### 外部資源
- [Grafana 官方文檔](https://grafana.com/docs/)
- [Prometheus 查詢語法](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [O-RAN SC 文檔](https://docs.o-ran-sc.org/)

---

## ✅ 驗證清單

設置完成後，請驗證：

- [ ] Grafana 可以正常訪問
- [ ] Prometheus 數據源已配置且連接正常
- [ ] Dashboard 已成功導入
- [ ] Dashboard 中所有面板都有數據
- [ ] 可以看到各 xApp 的指標
- [ ] 過濾器（xApp, Namespace）正常工作
- [ ] 自動刷新功能正常
- [ ] 時間範圍選擇器正常

---

**設置完成！** 🎉

現在您可以通過 Grafana Dashboard 實時監控雙路徑通訊系統的運行狀態了。
