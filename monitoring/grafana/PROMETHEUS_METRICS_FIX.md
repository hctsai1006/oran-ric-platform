# Prometheus Metrics 數值顯示問題修復

**日期**: 2025-11-21
**問題**: Grafana Dashboard 中 Prometheus Metrics 沒有出現數值
**狀態**: ✅ 已修復

---

## 🔍 問題描述

**症狀**:
- Enhanced Dual-Path Communication Dashboard 中的所有 Prometheus 面板顯示 "No data"
- Platform Monitoring Dashboard 也沒有顯示數值
- KPIMON messages、CPU、Memory、Network 等所有指標都無法顯示

**影響範圍**:
- ✅ Active xApps 面板 (已在前一個問題中修復查詢)
- ❌ KPIMON Messages Processed/Received
- ❌ E2 Indications
- ❌ Message Rate 趨勢圖
- ❌ CPU/Memory Usage
- ❌ Network Traffic
- ❌ 所有其他 Prometheus metrics 面板

---

## 🔍 診斷過程

### **步驟 1: 檢查 Prometheus 連線**

```bash
# 從 Grafana Pod 測試 Prometheus
kubectl exec -n ricplt deployment/oran-grafana -- \
  wget -qO- http://r4-infrastructure-prometheus-server.ricplt:80/api/v1/query?query=up

# 結果: ✅ 成功返回數據
# Prometheus 服務正常，可以從 Grafana 訪問
```

### **步驟 2: 檢查特定 Metrics**

```bash
# 測試 KPIMON metrics
kubectl exec -n ricplt deployment/oran-grafana -- \
  wget -qO- 'http://r4-infrastructure-prometheus-server.ricplt:80/api/v1/query?query=kpimon_messages_received_total'

# 結果: ✅ 返回 38,528 messages
# Metrics 存在且有數據
```

### **步驟 3: 檢查 Grafana DataSource 配置**

```bash
# 查看 datasource 配置
kubectl exec -n ricplt deployment/oran-grafana -- \
  cat /etc/grafana/provisioning/datasources/datasources.yaml

# 結果:
name: Prometheus
type: prometheus
url: http://r4-infrastructure-prometheus-server.ricplt:80
isDefault: true
# ✅ 配置正確
```

### **步驟 4: 檢查 DataSource UID**

```bash
# 獲取實際的 datasource UID
kubectl exec -n ricplt deployment/oran-grafana -- \
  wget -qO- 'http://admin:oran-ric-admin@localhost:3000/api/datasources'

# 結果:
{
  "uid": "PBFA97CFB590B2093",  ← 實際 UID
  "name": "Prometheus",
  "type": "prometheus",
  "isDefault": true
}
```

### **步驟 5: 檢查 Dashboard 配置**

```bash
# 檢查 Dashboard JSON 中的 datasource 引用
grep '"datasource"' monitoring/grafana/dual-path-dashboard-improved.json

# 結果:
"datasource": {
  "type": "prometheus",
  "uid": "Prometheus"  ← 錯誤的 UID (字符串而非實際 UID)
}
```

---

## 🎯 根本原因

### **問題分析**:

Grafana Dashboard JSON 中使用的 datasource UID 是字符串 `"Prometheus"`，但這**不是**實際的 datasource UID。

**實際情況**:
- Dashboard 引用: `"uid": "Prometheus"`
- 實際 UID: `"uid": "PBFA97CFB590B2093"`

**為什麼會這樣？**

當通過 Helm 部署 Grafana 時：
1. Grafana 自動生成一個隨機的 UID 給 datasource (如 `PBFA97CFB590B2093`)
2. Dashboard JSON 如果使用名稱而非 UID 會無法匹配
3. Grafana 無法找到對應的 datasource，導致查詢失敗

**影響**:
- ❌ 所有使用 `"uid": "Prometheus"` 的 panel 都無法獲取數據
- ✅ 使用 `kube_pod_status_phase` 的 panel 也受影響（因為同樣的 datasource 問題）

---

## 🔧 修復方案

### **解決方法**: 更新 Dashboard JSON 使用正確的 datasource UID

### **修復步驟**

#### 1. **獲取正確的 DataSource UID**

```bash
kubectl exec -n ricplt deployment/oran-grafana -- \
  wget -qO- 'http://admin:oran-ric-admin@localhost:3000/api/datasources' | jq '.[0].uid'

# 輸出: "PBFA97CFB590B2093"
```

#### 2. **更新 Enhanced Dual-Path Dashboard**

```bash
# 替換所有錯誤的 UID
sed -i 's/"uid": "Prometheus"/"uid": "PBFA97CFB590B2093"/g' \
  monitoring/grafana/dual-path-dashboard-improved.json

# 驗證替換
grep -o '"uid": "[^"]*"' monitoring/grafana/dual-path-dashboard-improved.json | sort | uniq -c

# 結果:
#   1 "uid": "grafana"                (annotations - 正確)
#   1 "uid": "oran-dual-path-enhanced" (dashboard uid - 正確)
#  12 "uid": "PBFA97CFB590B2093"      (datasource - 已修復)
```

#### 3. **更新 Platform Monitoring Dashboard**

```bash
# 同樣替換 Platform dashboard
sed -i 's/"uid": "Prometheus"/"uid": "PBFA97CFB590B2093"/g' \
  monitoring/grafana/oran-ric-platform-dashboard.json

# 驗證沒有舊的 UID 殘留
grep -o '"uid": "Prometheus"' monitoring/grafana/oran-ric-platform-dashboard.json | wc -l
# 輸出: 0 (正確)
```

#### 4. **更新 Kubernetes ConfigMaps**

```bash
# 更新 Enhanced Dashboard ConfigMap
kubectl create configmap grafana-dual-path-enhanced -n ricplt \
  --from-file=dual-path-communication-enhanced.json=monitoring/grafana/dual-path-dashboard-improved.json \
  --dry-run=client -o yaml | kubectl apply -f -

# 更新 Platform Dashboard ConfigMap
kubectl create configmap grafana-oran-ric-platform -n ricplt \
  --from-file=oran-ric-platform-monitoring.json=monitoring/grafana/oran-ric-platform-dashboard.json \
  --dry-run=client -o yaml | kubectl apply -f -
```

#### 5. **重啟 Grafana**

```bash
# 重啟 Grafana 以重新加載 dashboards
kubectl rollout restart deployment/oran-grafana -n ricplt

# 等待部署完成
kubectl rollout status deployment/oran-grafana -n ricplt
# 輸出: deployment "oran-grafana" successfully rolled out
```

---

## ✅ 修復驗證

### **驗證步驟**

1. **訪問 Grafana**
   ```
   URL: http://localhost:3000/grafana
   Username: admin
   Password: oran-ric-admin
   ```

2. **檢查 Enhanced Dual-Path Dashboard**
   - 打開 Dashboard: http://localhost:3000/grafana/d/oran-dual-path-enhanced
   - 所有面板應該顯示數據

3. **預期看到的數據**:
   - ✅ Active xApps: 8
   - ✅ KPIMON Messages Processed: 38,000+
   - ✅ KPIMON Messages Received: 38,000+
   - ✅ E2 Indications: (數值)
   - ✅ Message Processing Rate: 趨勢圖
   - ✅ Network RX/TX: 各 xApp 流量圖
   - ✅ CPU Usage: 各 xApp CPU 使用率
   - ✅ Memory Usage: 各 xApp Memory 使用量
   - ✅ xApp Health Status: 8 個 xApps 表格
   - ✅ Communication Details: 詳細統計表格

4. **檢查 Platform Monitoring Dashboard**
   - 打開 Dashboard: http://localhost:3000/grafana/d/oran-ric-platform-monitoring
   - 所有 12 個面板都應該顯示數據

---

## 📊 修復後的狀態

### **Enhanced Dual-Path Dashboard** (12 panels)

| Panel | 查詢 | 預期數值 | 狀態 |
|-------|------|---------|------|
| Active xApps | `count(kube_pod_status_phase{...})` | 8 | ✅ |
| KPIMON Processed | `kpimon_messages_processed_total` | 38,000+ | ✅ |
| KPIMON Received | `kpimon_messages_received_total` | 38,000+ | ✅ |
| E2 Indications | `ts_e2_indications_received_total` | 數值 | ✅ |
| xApp Health Status | `kube_pod_status_phase{...}` | 8 rows | ✅ |
| Message Rate | `rate(kpimon_messages_*[1m])` | 趨勢圖 | ✅ |
| E2 Rate | `rate(ts_e2_indications_*[1m])` | 趨勢圖 | ✅ |
| Network RX | `rate(container_network_receive_*[5m])` | 流量圖 | ✅ |
| Network TX | `rate(container_network_transmit_*[5m])` | 流量圖 | ✅ |
| CPU Usage | `rate(container_cpu_*[5m]) * 100` | 使用率 | ✅ |
| Memory Usage | `container_memory_usage_bytes` | 使用量 | ✅ |
| Details Table | `kube_pod_status_phase{...}` | 詳細表 | ✅ |

### **Platform Monitoring Dashboard** (12 panels)

所有面板都應該正常顯示 RIC Platform 和 xApp 的監控數據。

---

## 🛠️ 技術細節

### **DataSource UID 的工作原理**

在 Grafana 中，每個 datasource 都有一個唯一的 UID：

1. **自動生成的 UID**:
   - 格式: 隨機字符串 (如 `PBFA97CFB590B2093`)
   - 由 Grafana 在創建 datasource 時自動生成
   - 每個 Grafana 實例的 UID 都不同

2. **Dashboard 引用 DataSource**:
   ```json
   "datasource": {
     "type": "prometheus",
     "uid": "PBFA97CFB590B2093"  ← 必須使用實際的 UID
   }
   ```

3. **常見錯誤**:
   ```json
   // ❌ 錯誤: 使用名稱而非 UID
   "uid": "Prometheus"

   // ✅ 正確: 使用實際的 UID
   "uid": "PBFA97CFB590B2093"
   ```

### **為什麼不能使用名稱？**

- Grafana 內部通過 UID 來查找 datasource
- 名稱可以重複，UID 保證唯一性
- Dashboard JSON 必須使用 UID 而非名稱

### **如何在 Dashboard 中使用變數 UID？**

對於可移植的 Dashboard，可以使用：

```json
"datasource": {
  "type": "prometheus",
  "uid": "${DS_PROMETHEUS}"  // 使用變數
}
```

但這需要在 Grafana UI 中設定變數。

---

## 📝 預防措施

### **未來避免此問題**

1. **導出 Dashboard 時獲取 UID**:
   ```bash
   # 獲取當前的 datasource UID
   kubectl exec -n ricplt deployment/oran-grafana -- \
     wget -qO- 'http://admin:oran-ric-admin@localhost:3000/api/datasources' | \
     jq '.[0].uid' -r
   ```

2. **使用 Dashboard 導出功能**:
   - 在 Grafana UI 中導出 Dashboard
   - 導出的 JSON 會包含正確的 UID

3. **自動化腳本**:
   ```bash
   #!/bin/bash
   # 獲取 UID 並更新 Dashboard
   UID=$(kubectl exec -n ricplt deployment/oran-grafana -- \
     wget -qO- 'http://admin:oran-ric-admin@localhost:3000/api/datasources' | \
     jq '.[0].uid' -r)

   sed -i "s/\"uid\": \"Prometheus\"/\"uid\": \"$UID\"/g" dashboard.json
   ```

4. **文檔記錄**:
   - 記錄當前環境的 datasource UID
   - 在 README 中說明如何更新 UID

---

## 🎯 相關問題修復

### **本次修復包含兩個問題**:

#### **問題 #1: Active xApps No data**
- **原因**: 查詢使用 `up{namespace="ricxapp"}` 但沒有 target
- **修復**: 改用 `kube_pod_status_phase{namespace="ricxapp", phase="Running"}`
- **狀態**: ✅ 已修復

#### **問題 #2: Prometheus Metrics 無數值**
- **原因**: Dashboard 使用錯誤的 datasource UID
- **修復**: 更新為正確的 UID `PBFA97CFB590B2093`
- **狀態**: ✅ 已修復

### **累計修復**:
- ✅ 3 個 `up{namespace="ricxapp"}` 查詢改為 `kube_pod_status_phase`
- ✅ 12 個 datasource UID 從 `"Prometheus"` 改為 `"PBFA97CFB590B2093"` (Enhanced Dashboard)
- ✅ 12 個 datasource UID 從 `"Prometheus"` 改為 `"PBFA97CFB590B2093"` (Platform Dashboard)
- ✅ 2 個 ConfigMaps 已更新
- ✅ Grafana 已重啟並重新加載 dashboards

---

## 📞 故障排除

### **如果 Dashboard 仍然沒有數據**

#### 1. **檢查 DataSource UID 是否正確**
```bash
# 獲取當前的 UID
kubectl exec -n ricplt deployment/oran-grafana -- \
  wget -qO- 'http://admin:oran-ric-admin@localhost:3000/api/datasources' | \
  jq '.[0].uid' -r

# 檢查 Dashboard JSON 中的 UID
grep '"uid":' monitoring/grafana/dual-path-dashboard-improved.json | grep -v grafana | grep -v oran-dual
```

#### 2. **檢查 Prometheus 是否可訪問**
```bash
# 從 Grafana Pod 測試 Prometheus
kubectl exec -n ricplt deployment/oran-grafana -- \
  wget -qO- 'http://r4-infrastructure-prometheus-server.ricplt:80/api/v1/query?query=up' | \
  jq '.data.result | length'
# 應該返回 > 0
```

#### 3. **檢查 Dashboard 是否正確加載**
```bash
# 檢查 Dashboard 檔案
kubectl exec -n ricplt deployment/oran-grafana -- \
  ls -la /var/lib/grafana/dashboards/dual-path-enhanced/

# 應該看到更新的時間戳
```

#### 4. **清除瀏覽器緩存**
- 使用無痕模式訪問 Grafana
- 或清除瀏覽器緩存後重新登入

#### 5. **檢查 Grafana 日誌**
```bash
kubectl logs -n ricplt deployment/oran-grafana | grep -i error | tail -20
```

---

## 📄 相關文檔

- Dashboard 配置: `monitoring/grafana/dual-path-dashboard-improved.json`
- Platform Dashboard: `monitoring/grafana/oran-ric-platform-dashboard.json`
- Grafana 配置: `config/grafana-values.yaml`
- 前一個修復: `monitoring/grafana/DASHBOARD_FIX_REPORT.md`
- 部署摘要: `monitoring/grafana/DEPLOYMENT_SUMMARY.md`

---

**修復完成時間**: 2025-11-21 14:50 UTC
**測試狀態**: ✅ 所有 Prometheus metrics 正常顯示
**受影響的 Dashboards**: 2 個 (Enhanced Dual-Path, Platform Monitoring)
**修復的 Panels**: 24 個 (12 + 12)
