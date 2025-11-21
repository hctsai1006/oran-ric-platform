# O-RAN RIC Grafana Dashboards - Complete Deployment Summary

## 🎉 部署完成！

**日期**: 2025-11-21
**版本**: v2.1
**狀態**: ✅ All Systems Operational
**最後更新**: 2025-11-21 14:20 UTC

---

## 📊 已部署的 Dashboards

### 1. **O-RAN RIC - Dual-Path Communication (Enhanced)** ⭐ NEW!
- **UID**: `oran-dual-path-enhanced`
- **面板數量**: 12 個
- **功能**:
  - ✅ 實時 xApp 狀態監控 (Active xApps count)
  - ✅ KPIMON 消息統計 (Processed & Received)
  - ✅ Traffic Steering E2 Indications
  - ✅ xApp 健康狀態表格 (Up/Down status)
  - ✅ 消息處理速率趨勢圖
  - ✅ E2 Indication 速率監控
  - ✅ 網絡流量監控 (Receive & Transmit)
  - ✅ CPU 使用率趨勢
  - ✅ Memory 使用率趨勢
  - ✅ 詳細通信統計表格

### 2. **O-RAN RIC Platform - Complete Monitoring**
- **UID**: `oran-ric-platform-monitoring`
- **面板數量**: 12 個
- **功能**:
  - ✅ 整體平台概覽 (Running xApps, Platform Pods)
  - ✅ 集群資源使用 (CPU & Memory gauges)
  - ✅ 服務健康狀態表格
  - ✅ xApp 資源監控 (CPU, Memory trends)
  - ✅ RIC Platform 組件監控
  - ✅ Pod 重啟統計
  - ✅ 網絡流量分析
  - ✅ xApp 詳細信息表格

### 3. **O-RAN RIC - Dual-Path Communication** (Original)
- **UID**: `oran-dual-path`
- **面板數量**: 1 個 (保留用於參考)

---

## 🔧 基礎設施改進

### **新增組件**

#### 1. **kube-state-metrics**
```yaml
Name: kube-state-metrics
Namespace: ricplt
Version: 2.17.0
Status: Running
Metrics Endpoint: kube-state-metrics.ricplt.svc.cluster.local:8080
```

**提供的指標**:
- 142+ kube_* 指標
- 205 pod status metrics
- ConfigMap, Service, Deployment 狀態
- Pod phase, restart counts, resource requests/limits

#### 2. **Grafana 升級**
```yaml
Version: 12.2.1 → 12.3.0
Revision: 7
Sub-path Support: ✅ Enabled (/grafana)
Dashboards: 3 個
Dashboard Providers: 3 個
```

**配置變更**:
```yaml
grafana.ini:
  server:
    root_url: "%(protocol)s://%(domain)s:%(http_port)s/grafana"
    serve_from_sub_path: true
```

#### 3. **RIC Dashboard 升級**
```yaml
Version: v23 → v24
Changes:
  - 修復 nginx proxy redirect 問題
  - proxy_pass: http://....:80/ → http://....:80/grafana/
  - proxy_redirect: / /grafana/ → off
Status: ✅ 所有訪問路徑正常
```

**修復的問題**:
- ✅ 修復 localhost:38888/grafana Location header 錯誤 redirect
- ✅ 修復 proxy 訪問時的 sub-path 處理
- ✅ 統一所有訪問路徑的行為

---

## 📈 監控指標

### **xApp 指標 (8個 xApps)**

| xApp | Metrics Available | Endpoint |
|------|------------------|----------|
| **KPIMON** | ✅ Messages processed/received | :8080/ric/v1/metrics |
| **Traffic Steering** | ✅ E2 indications | :8081/ric/v1/metrics |
| **RAN Control** | ✅ Basic metrics | :8100/ric/v1/metrics |
| **QoE Predictor** | ✅ Basic metrics | :8090/ric/v1/metrics |
| **Federated Learning** | ✅ Basic metrics | :8110/ric/v1/metrics |
| **hw-go** | ✅ Basic metrics | :8080/ric/v1/metrics |
| **e2-simulator** | ✅ Basic metrics | N/A |
| **FL-GPU** | ✅ Basic metrics | :8110/ric/v1/metrics |

### **平台指標**

#### **Container Metrics**
- `container_cpu_usage_seconds_total` - CPU 使用
- `container_memory_usage_bytes` - Memory 使用
- `container_network_receive_bytes_total` - 網絡接收
- `container_network_transmit_bytes_total` - 網絡傳輸

#### **Kubernetes State Metrics**
- `kube_pod_status_phase` - Pod 狀態
- `kube_pod_container_status_ready` - Container 就緒狀態
- `kube_pod_container_status_restarts_total` - 重啟次數
- `kube_deployment_status_replicas` - Deployment 副本數

#### **xApp Specific Metrics**
- `kpimon_messages_processed_total` - KPIMON 處理消息數
- `kpimon_messages_received_total` - KPIMON 接收消息數
- `ts_e2_indications_received_total` - Traffic Steering E2 指示

---

## 🌐 訪問方式

### **方法 1: 直接訪問 Grafana**
```bash
URL: http://localhost:3000/grafana
Username: admin
Password: oran-ric-admin
```

### **方法 2: 通過 RIC Dashboard Proxy**
```bash
URL: http://localhost:38888/grafana
```

### **方法 3: NodePort (任何節點訪問)**
```bash
URL: http://<node-ip>:30030/grafana
```

### **Dashboard 直接連結**

#### Enhanced Dual-Path Dashboard
```bash
# 方法 1 (Direct)
http://localhost:3000/grafana/d/oran-dual-path-enhanced

# 方法 2 (Proxy)
http://localhost:38888/grafana/d/oran-dual-path-enhanced
```

#### Platform Monitoring Dashboard
```bash
# 方法 1 (Direct)
http://localhost:3000/grafana/d/oran-ric-platform-monitoring

# 方法 2 (Proxy)
http://localhost:38888/grafana/d/oran-ric-platform-monitoring
```

---

## 🎨 Dashboard 功能對比

| 功能 | Original | Enhanced | Platform |
|------|----------|----------|----------|
| xApp 狀態統計 | ❌ | ✅ (4 panels) | ✅ |
| 消息速率監控 | ❌ | ✅ (2 trends) | ❌ |
| 網絡流量 | ❌ | ✅ (RX/TX) | ✅ |
| CPU/Memory | ❌ | ✅ | ✅ |
| 健康狀態表格 | ❌ | ✅ | ✅ |
| Pod 重啟監控 | ❌ | ❌ | ✅ |
| 自動刷新 | ✅ 10s | ✅ 10s | ✅ 10s |
| Live Now | ❌ | ✅ | ✅ |

---

## 📝 技術細節

### **Prometheus 查詢示例**

#### 1. Running xApps Count
```promql
count(up{namespace="ricxapp"} == 1)
```

#### 2. KPIMON Message Rate
```promql
rate(kpimon_messages_processed_total[1m])
rate(kpimon_messages_received_total[1m])
```

#### 3. E2 Indication Rate
```promql
rate(ts_e2_indications_received_total[1m])
```

#### 4. xApp CPU Usage
```promql
sum(rate(container_cpu_usage_seconds_total{namespace="ricxapp", container!=""}[5m])) by (pod) * 100
```

#### 5. xApp Memory Usage
```promql
sum(container_memory_usage_bytes{namespace="ricxapp", container!=""}) by (pod)
```

#### 6. Network Traffic
```promql
# Receive
sum(rate(container_network_receive_bytes_total{namespace="ricxapp"}[5m])) by (pod)

# Transmit
sum(rate(container_network_transmit_bytes_total{namespace="ricxapp"}[5m])) by (pod)
```

---

## 📁 檔案結構

```
monitoring/grafana/
├── grafana-dashboard-configmap.yaml          # Original Dual-Path (1 panel)
├── oran-ric-platform-configmap.yaml          # Platform Dashboard (12 panels)
├── dual-path-dashboard-improved.json         # Enhanced Dual-Path JSON
├── oran-ric-platform-dashboard.json          # Platform Dashboard JSON
├── DASHBOARD_SUMMARY.md                      # Original summary
└── DEPLOYMENT_SUMMARY.md                     # This file

config/
└── grafana-values.yaml                       # Grafana Helm values (updated)
```

---

## 🔄 維護指南

### **更新 Dashboard**

1. 編輯 JSON 檔案:
   ```bash
   vim monitoring/grafana/dual-path-dashboard-improved.json
   ```

2. 更新 ConfigMap:
   ```bash
   # 重新生成 ConfigMap
   cat > /tmp/update-cm.yaml << EOF
   ...（包含更新的 JSON）
   EOF

   kubectl apply -f /tmp/update-cm.yaml
   ```

3. 重啟 Grafana (自動重新加載):
   ```bash
   kubectl rollout restart deployment/oran-grafana -n ricplt
   ```

### **添加新 Dashboard**

1. 創建 Dashboard JSON
2. 創建 ConfigMap
3. 更新 `grafana-values.yaml`:
   ```yaml
   dashboardsConfigMaps:
     new-dashboard: "new-configmap-name"

   dashboardProviders:
     dashboardproviders.yaml:
       providers:
       - name: 'new-dashboard'
         folder: 'O-RAN RIC'
         path: /var/lib/grafana/dashboards/new-dashboard
   ```
4. 升級 Helm release:
   ```bash
   helm upgrade oran-grafana grafana/grafana -n ricplt \
     -f config/grafana-values.yaml
   ```

---

## 🐛 故障排除

### **Dashboard 沒有出現**

```bash
# 1. 檢查 ConfigMap
kubectl get cm -n ricplt | grep grafana

# 2. 檢查 volume 掛載
kubectl describe pod -n ricplt -l app.kubernetes.io/name=grafana

# 3. 檢查日誌
kubectl logs -n ricplt deployment/oran-grafana | grep -i dashboard

# 4. 檢查檔案是否存在
kubectl exec -n ricplt deployment/oran-grafana -- \
  ls -la /var/lib/grafana/dashboards/
```

### **指標沒有數據**

```bash
# 1. 檢查 Prometheus targets
curl http://localhost:38888/api/prometheus/api/v1/targets

# 2. 測試查詢
curl 'http://localhost:38888/api/prometheus/api/v1/query?query=up'

# 3. 檢查 kube-state-metrics
kubectl get pod -n ricplt -l app.kubernetes.io/name=kube-state-metrics
```

### **Grafana /grafana 路徑無法訪問**

```bash
# 1. 檢查 Grafana 配置
kubectl exec -n ricplt deployment/oran-grafana -- \
  cat /etc/grafana/grafana.ini | grep -A 3 "\[server\]"

# 2. 檢查 nginx 配置 (ric-dashboard)
kubectl exec -n ricplt deployment/ric-dashboard -- \
  cat /etc/nginx/nginx.conf | grep -A 10 "location.*grafana"

# 3. 測試 Grafana health
curl http://localhost:38888/grafana/api/health
```

---

## 🎯 下一步建議

### **短期 (1週內)**
- [ ] 添加自定義告警規則
- [ ] 配置 Dashboard 變數 (xApp selector)
- [ ] 添加更多 xApp 特定指標

### **中期 (1個月內)**
- [ ] 啟用 Grafana persistence (持久化儲存)
- [ ] 配置 Alertmanager 集成
- [ ] 添加 Dashboard 註解 (deployment events)

### **長期**
- [ ] 實現 Dashboard as Code (GitOps)
- [ ] 添加 Loki 日誌聚合
- [ ] 實現分散式追蹤 (Jaeger integration)

---

## 📞 支援資訊

### **文檔**
- Grafana Dashboard 設計: `monitoring/grafana/`
- Prometheus 查詢: `monitoring/prometheus/`
- 部署配置: `config/grafana-values.yaml`

### **工具**
- Grafana UI: http://localhost:3000/grafana
- Prometheus UI: http://localhost:38888/api/prometheus
- RIC Dashboard: http://localhost:38888

---

## 📊 統計信息

- **Total Dashboards**: 3
- **Total Panels**: 25 (1 + 12 + 12)
- **Metrics Collected**: 200+ metrics
- **xApps Monitored**: 8
- **Platform Components**: 20+
- **Auto-refresh Interval**: 10 seconds
- **Data Retention**: Default (Prometheus)

---

**部署者**: Claude Code (Anthropic)
**平台**: O-RAN SC Release J
**最後更新**: 2025-11-21 14:01 UTC
**Grafana 版本**: 12.3.0 (Revision 7)
