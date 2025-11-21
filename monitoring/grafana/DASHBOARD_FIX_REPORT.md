# Grafana Dashboard 修復報告

**日期**: 2025-11-21
**問題**: Active xApps 和 xApp Health Status 顯示 "No data"
**狀態**: ✅ 已修復

---

## 🔍 問題診斷

### **問題 #1: Active xApps 顯示 No data**

**症狀**:
- Enhanced Dual-Path Communication Dashboard 中的 "Active xApps" 面板顯示 "No data"
- xApp Health Status 表格也是空的

**根本原因**:
Dashboard 使用的 Prometheus 查詢 `count(up{namespace="ricxapp"} == 1)` 無法返回數據，因為：
1. ricxapp namespace 的 xApp pods **沒有被 Prometheus 直接抓取為 targets**
2. xApp services 沒有 `prometheus.io/scrape` annotations
3. 沒有配置 ServiceMonitor 資源

**診斷過程**:
```bash
# 1. 檢查 xApp pods 狀態
kubectl get pods -n ricxapp
# 結果: 8 個 xApps 全部 Running

# 2. 測試原始查詢
curl 'http://localhost:38888/api/prometheus/api/v1/query?query=up{namespace="ricxapp"}'
# 結果: {"status":"success","data":{"result":[]}}  ❌ 空結果

# 3. 測試替代查詢 (使用 kube-state-metrics)
curl 'http://localhost:38888/api/prometheus/api/v1/query?query=count(kube_pod_status_phase{namespace="ricxapp",phase="Running"})'
# 結果: {"value":[..., "8"]}  ✅ 正確返回 8 個 xApps
```

---

## 🔧 修復方案

### **解決方法**: 改用 kube-state-metrics 提供的指標

將所有使用 `up{namespace="ricxapp"}` 的查詢改為使用 `kube_pod_status_phase{namespace="ricxapp", phase="Running"}`

### **修復的查詢 (3 處)**

#### 1. **Active xApps 統計面板**
```diff
- "expr": "count(up{namespace=\"ricxapp\"} == 1)"
+ "expr": "count(kube_pod_status_phase{namespace=\"ricxapp\", phase=\"Running\"})"
```

#### 2. **xApp Health Status 表格**
```diff
- "expr": "up{namespace=\"ricxapp\"}"
+ "expr": "kube_pod_status_phase{namespace=\"ricxapp\", phase=\"Running\"}"
```

#### 3. **xApp Communication Details 表格**
```diff
- "expr": "up{namespace=\"ricxapp\"}"
+ "expr": "kube_pod_status_phase{namespace=\"ricxapp\", phase=\"Running\"}"
```

### **修復步驟**

1. **更新 Dashboard JSON**
   ```bash
   vi monitoring/grafana/dual-path-dashboard-improved.json
   # 修改 3 處查詢
   ```

2. **更新 ConfigMap**
   ```bash
   kubectl create configmap grafana-dual-path-enhanced -n ricplt \
     --from-file=dual-path-communication-enhanced.json=monitoring/grafana/dual-path-dashboard-improved.json \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

3. **重啟 Grafana**
   ```bash
   kubectl rollout restart deployment/oran-grafana -n ricplt
   kubectl rollout status deployment/oran-grafana -n ricplt
   ```

4. **驗證修復**
   ```bash
   # 測試新查詢
   curl 'http://localhost:38888/api/prometheus/api/v1/query?query=count(kube_pod_status_phase{namespace="ricxapp",phase="Running"})'
   # 結果: "8"  ✅
   ```

---

## 📊 E2 Simulator 狀態分析

### **問題 #2: E2 Simulator 是否需要一直發資料？**

**答案**: ✅ **是的，這是正常且必要的行為**

### **E2 Simulator 的作用**

E2 Simulator 模擬 RAN (無線接入網) 的行為，持續向 RIC Platform 發送 E2 messages：

```
功能:
1. 模擬 KPI indications (每 5 秒)
2. 模擬 QoE metrics
3. 模擬 handover events
4. 模擬 control events (interference mitigation)
```

### **當前狀態** ✅ 正常運行

```bash
# E2 Simulator 狀態
NAME                            READY   STATUS    RESTARTS   AGE
e2-simulator-58c557f9cc-d2dpw   1/1     Running   0          2d5h

# 最新日誌 (每 5 秒發送一次)
2025-11-21 06:37:07 - INFO - === Simulation Iteration 38462 ===
2025-11-21 06:37:07 - INFO - Generated KPI indication for cell_001/ue_002 on beam 2
2025-11-21 06:37:07 - INFO - Generated QoE metrics for ue_003: QoE=91.5
2025-11-21 06:37:07 - INFO - Waiting 5 seconds...
```

### **KPIMON 接收狀態** ✅ 正常接收

```bash
# KPIMON 統計
kpimon_messages_received_total: 38,495 messages
接收速率: ~12 messages/minute (每 5 秒一次)

# KPIMON 日誌
10.42.0.67 - - [21/Nov/2025 06:37:07] "POST /e2/indication HTTP/1.1" 200 -
{"ts": 1763707027446, "crit": "WARNING", "id": "KPIMON",
 "msg": "Anomaly detected in cell cell_001, beam 2: [...]"}
```

### **為什麼需要持續發送？**

1. **實時監控**: xApps (如 KPIMON) 需要持續接收數據進行實時分析
2. **異常檢測**: KPIMON 檢測 RSRP、SINR 等 KPI 的異常情況
3. **性能測試**: 驗證 RIC Platform 處理大量消息的能力
4. **Dashboard 更新**: Grafana Dashboard 需要持續的數據流來顯示趨勢

### **是否需要關注？**

| 狀況 | 是否正常 | 建議 |
|------|---------|------|
| E2 Simulator 持續發送 | ✅ 正常 | 無需擔心，這是預期行為 |
| KPIMON 接收消息並分析 | ✅ 正常 | 系統工作正常 |
| 檢測到 anomaly warnings | ✅ 正常 | 這是模擬的異常情況，用於測試 |
| CPU/Memory 使用穩定 | ✅ 正常 | 資源使用在合理範圍內 |

### **何時需要注意？**

⚠️ **需要注意的情況**:
- E2 Simulator 停止發送 (Pod Crash)
- KPIMON 停止接收 (連線問題)
- 消息處理速率急劇下降
- CPU/Memory 使用率異常飆高
- Pod 頻繁重啟

---

## ✅ 修復後的狀態

### **Dashboard 現在可以正常顯示**:

1. **Active xApps**: 8 個 ✅
2. **KPIMON Messages Processed**: 38,495+ ✅
3. **KPIMON Messages Received**: 38,495+ ✅
4. **E2 Indications**: (Traffic Steering 統計) ✅
5. **xApp Health Status**: 顯示所有 8 個 xApps ✅
6. **Message Processing Rate**: 顯示趨勢圖 ✅
7. **Network Traffic**: 顯示各 xApp 流量 ✅
8. **CPU/Memory**: 顯示各 xApp 資源使用 ✅

### **E2 Simulator 持續運行**:
```
狀態: Running
Iteration: 38,462+
發送頻率: 每 5 秒一次
數據類型:
  - KPI indications (cell/UE/beam)
  - QoE metrics
  - Handover events
  - Control events
```

### **KPIMON 正常處理**:
```
已接收: 38,495+ messages
處理速率: ~12 msg/min
異常檢測: 正常運作 (檢測 RSRP/SINR 閾值)
```

---

## 📝 技術細節

### **為什麼 `up` 指標不可用？**

`up` 指標由 Prometheus 在抓取 target 時自動生成，表示 target 是否可達：
- `up=1`: Target 可達
- `up=0`: Target 不可達

**ricxapp namespace 的情況**:
- xApp services 沒有配置為 Prometheus targets
- 沒有 ServiceMonitor 或 PodMonitor 資源
- xApp services 缺少 `prometheus.io/scrape: "true"` annotations

**解決方案**:
使用 `kube-state-metrics` 提供的 `kube_pod_status_phase` 指標：
- 由 kube-state-metrics 收集所有 Pod 的狀態
- 不需要直接抓取 xApp endpoints
- 提供更可靠的 Pod 狀態信息

### **kube-state-metrics 提供的指標**

```prometheus
# Pod 狀態
kube_pod_status_phase{namespace="ricxapp", phase="Running"} = 1

# Pod 標籤包含
{
  namespace: "ricxapp"
  pod: "kpimon-5554d76bc8-8nmgv"
  phase: "Running"
  ...
}
```

---

## 🎯 建議

### **短期 (已完成)**
- ✅ 修復 Dashboard 查詢使用 kube-state-metrics
- ✅ 驗證所有面板正常顯示數據
- ✅ 確認 E2 Simulator 持續運行

### **中期 (可選)**
- [ ] 為 xApp services 添加 Prometheus annotations
  ```yaml
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8080"
    prometheus.io/path: "/ric/v1/metrics"
  ```
- [ ] 創建 ServiceMonitor 資源讓 Prometheus 直接抓取 xApp metrics
- [ ] 添加更多 xApp 特定的業務指標到 Dashboard

### **長期**
- [ ] 配置 Alerting rules (如: Pod down, High CPU, Message rate drop)
- [ ] 添加 Dashboard annotations 標記重要事件
- [ ] 實現 Grafana Dashboard 版本控制 (GitOps)

---

## 📞 驗證步驟

### **檢查 Dashboard 是否正常**

1. **訪問 Grafana**
   ```
   URL: http://localhost:3000/grafana
   Username: admin
   Password: oran-ric-admin
   ```

2. **打開 Enhanced Dual-Path Dashboard**
   - 登入後會自動顯示
   - 或訪問: http://localhost:3000/grafana/d/oran-dual-path-enhanced

3. **驗證面板數據**
   - Active xApps: 應顯示 **8**
   - KPIMON Processed/Received: 應顯示 **38,000+** 且持續增長
   - xApp Health Status: 應顯示 8 個 xApps 的表格
   - 所有圖表應顯示趨勢線

4. **檢查 E2 Simulator**
   ```bash
   # 查看最新日誌
   kubectl logs -n ricxapp -l app=e2-simulator --tail=10

   # 應該看到每 5 秒一次的 "Simulation Iteration" 消息
   ```

---

**修復完成時間**: 2025-11-21 14:45 UTC
**測試狀態**: ✅ 所有面板正常顯示數據
**E2 Simulator**: ✅ 持續運行，無需干預
**KPIMON**: ✅ 正常接收和處理消息

---

## 📄 相關文檔

- Grafana 配置: `config/grafana-values.yaml`
- Dashboard JSON: `monitoring/grafana/dual-path-dashboard-improved.json`
- Dashboard ConfigMap: 已更新為最新版本
- 部署摘要: `monitoring/grafana/DEPLOYMENT_SUMMARY.md`
