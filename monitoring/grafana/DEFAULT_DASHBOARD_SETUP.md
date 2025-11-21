# Grafana 預設 Dashboard 設定

**設定日期**: 2025-11-21
**狀態**: ✅ 已完成

---

## 🎯 設定內容

### **預設首頁 Dashboard**
```
Dashboard: O-RAN RIC - Dual-Path Communication (Enhanced)
UID: oran-dual-path-enhanced
Panels: 12 個
```

### **功能特色**
- ✅ 實時 xApp 狀態監控
- ✅ KPIMON 消息統計
- ✅ Traffic Steering E2 Indications
- ✅ xApp 健康狀態表格
- ✅ 消息處理速率趨勢圖
- ✅ 網絡流量監控
- ✅ CPU/Memory 使用率

---

## 🔧 配置詳情

### **Grafana 配置** (`config/grafana-values.yaml`)
```yaml
grafana.ini:
  dashboards:
    default_home_dashboard_path: /var/lib/grafana/dashboards/dual-path-enhanced/dual-path-communication-enhanced.json
```

### **配置檔案位置**
```
Pod 內部路徑: /etc/grafana/grafana.ini
Dashboard 檔案: /var/lib/grafana/dashboards/dual-path-enhanced/dual-path-communication-enhanced.json
```

---

## 📋 使用說明

### **訪問方式**

當你打開 Grafana 並登入後，系統會自動顯示 **Enhanced Dual-Path Communication Dashboard**。

#### **1. 直接訪問**
```
URL: http://localhost:3000/grafana
Username: admin
Password: oran-ric-admin
```
登入後會自動跳轉到預設 Dashboard。

#### **2. 透過 Proxy 訪問**
```
URL: http://localhost:38888/grafana
Username: admin
Password: oran-ric-admin
```

#### **3. 透過 NodePort 訪問**
```
URL: http://localhost:30030/grafana
Username: admin
Password: oran-ric-admin
```

---

## 🔍 驗證設定

### **檢查配置是否生效**
```bash
# 1. 進入 Grafana Pod
kubectl exec -n ricplt deployment/oran-grafana -- \
  cat /etc/grafana/grafana.ini | grep default_home_dashboard

# 預期輸出:
# default_home_dashboard_path = /var/lib/grafana/dashboards/dual-path-enhanced/dual-path-communication-enhanced.json

# 2. 驗證 Dashboard 檔案存在
kubectl exec -n ricplt deployment/oran-grafana -- \
  ls -l /var/lib/grafana/dashboards/dual-path-enhanced/

# 預期看到:
# dual-path-communication-enhanced.json
```

---

## 📊 Dashboard 內容

### **12 個監控面板**

1. **Active xApps** - 顯示當前運行的 xApp 數量
2. **KPIMON Processed** - KPIMON 處理的消息總數
3. **KPIMON Received** - KPIMON 接收的消息總數
4. **E2 Indications** - Traffic Steering 接收的 E2 指示
5. **xApp Health Status** - 各 xApp 健康狀態表格
6. **Message Processing Rate** - 消息處理速率趨勢
7. **E2 Indication Rate** - E2 指示速率趨勢
8. **Network Receive Rate** - 網絡接收速率
9. **Network Transmit Rate** - 網絡傳輸速率
10. **CPU Usage per xApp** - 各 xApp CPU 使用率
11. **Memory Usage per xApp** - 各 xApp Memory 使用率
12. **Communication Details** - 詳細通信統計表格

---

## 🔄 修改預設 Dashboard

如果想更改為其他 Dashboard，修改 `config/grafana-values.yaml`:

### **選項 1: Platform Monitoring Dashboard**
```yaml
grafana.ini:
  dashboards:
    default_home_dashboard_path: /var/lib/grafana/dashboards/oran-ric-platform/oran-ric-platform-monitoring.json
```

### **選項 2: Original Dual-Path Dashboard**
如果有需要，可以創建舊版的 ConfigMap 並設定路徑。

### **應用變更**
```bash
# 更新 Grafana
helm upgrade oran-grafana grafana/grafana -n ricplt \
  -f config/grafana-values.yaml

# 等待 Pod 重啟
kubectl rollout status deployment/oran-grafana -n ricplt
```

---

## 📝 注意事項

### **重要提醒**
1. ✅ **登入後自動顯示**: 預設 Dashboard 會在登入後自動顯示
2. ✅ **首頁按鈕行為**: 點擊 Grafana 左上角的首頁圖標會回到此 Dashboard
3. ⚠️ **需要登入**: 必須先登入才能看到預設 Dashboard
4. ⚠️ **Persistence 關閉**: 目前 Grafana persistence 是關閉的，Pod 重啟後用戶偏好設定會重置

### **最佳實踐**
- 建議將常用的 Dashboard 加入書籤
- 可以在 Dashboard 右上角點擊 ⭐ 星號收藏
- 使用 Grafana 的 "Starred" 功能快速訪問

---

## 🛠️ 故障排除

### **問題: 預設 Dashboard 沒有顯示**

#### 檢查步驟:
```bash
# 1. 確認配置正確
kubectl exec -n ricplt deployment/oran-grafana -- \
  cat /etc/grafana/grafana.ini | grep default_home

# 2. 確認檔案存在
kubectl exec -n ricplt deployment/oran-grafana -- \
  test -f /var/lib/grafana/dashboards/dual-path-enhanced/dual-path-communication-enhanced.json \
  && echo "OK" || echo "MISSING"

# 3. 檢查 Dashboard 是否被正確加載
kubectl logs -n ricplt deployment/oran-grafana | grep -i dashboard
```

#### 解決方案:
```bash
# 重啟 Grafana
kubectl rollout restart deployment/oran-grafana -n ricplt

# 清除瀏覽器緩存並重新登入
```

---

## 📞 支援資訊

### **相關文檔**
- Grafana 配置: `config/grafana-values.yaml`
- Dashboard JSON: `monitoring/grafana/dual-path-dashboard-improved.json`
- 部署摘要: `monitoring/grafana/DEPLOYMENT_SUMMARY.md`

### **快速連結**
- Enhanced Dashboard 直接連結: http://localhost:3000/grafana/d/oran-dual-path-enhanced
- Platform Dashboard: http://localhost:3000/grafana/d/oran-ric-platform-monitoring

---

**設定完成時間**: 2025-11-21 14:35 UTC
**Grafana 版本**: v12.3.0
**Helm Revision**: 9
**狀態**: ✅ 預設 Dashboard 已設定為 Enhanced Dual-Path Communication
