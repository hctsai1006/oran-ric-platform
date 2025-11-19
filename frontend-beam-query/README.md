# Beam KPI Query Dashboard - 專業版

**作者**: 蔡秀吉 (thc1006)
**日期**: 2025-11-19
**版本**: 2.0.0
**設計風格**: Kubernetes Dashboard (Material Design + Bootstrap 5)

---

## ✨ 特色

### 專業化 UI 設計

✅ **Material Design 風格**（與 Kubernetes Dashboard 一致）
✅ **響應式設計**（支援手機/平板/桌面）
✅ **即時數據展示**（Quick Stats + 詳細表格）
✅ **清晰的視覺層次**（卡片式佈局）
✅ **專業配色**（Deep Purple & Amber）

### 功能特色

- 📡 **多 Beam 查詢**（Beam 1-7）
- 📊 **多種 KPI 類型**（Signal Quality, Throughput, etc.）
- ⚡ **即時響應**（< 100ms）
- 🎯 **智慧品質標籤**（Excellent, Good, Fair, Poor）
- 📈 **詳細指標表格**（時間戳、單位、品質等級）

---

## 🚀 快速開始

### 方式 1：專業 Web UI（新！）⭐⭐⭐⭐⭐

```bash
# 1. 啟動 UI Server
cd frontend-beam-query
python3 server.py 8000

# 2. 在瀏覽器開啟
http://localhost:8000/
```

**操作步驟**：
1. 選擇 **Beam ID** (1-7)
2. 選擇 **KPI Type** (All / Signal Quality / Throughput / etc.)
3. 選擇 **Time Range** (Current / Last 5 Min / Last Hour)
4. 點擊 **Query** 按鈕
5. 查看結果：
   - **Quick Stats**：RSRP, SINR, DL/UL Throughput
   - **Detailed Table**：完整 KPI 指標
   - **Metadata**：Beam ID, Cell ID, UE Count

**Screenshots**:
```
┌────────────────────────────────────────────────┐
│  O-RAN RIC - Beam KPI Query Dashboard         │
│  Real-time Beam Performance Monitoring        │
└────────────────────────────────────────────────┘
┌───────────┬───────────┬───────────┬───────────┐
│  RSRP     │  SINR     │  DL Thpt  │  UL Thpt  │
│  -95.5    │  15.3     │  45.2     │  22.1     │
│  [Good]   │  [Good]   │  Mbps     │  Mbps     │
└───────────┴───────────┴───────────┴───────────┘
┌────────────────────────────────────────────────┐
│  Detailed KPI Metrics                          │
│  ┌──────────┬────────┬───────┬──────┬────────┐│
│  │ Category │ Metric │ Value │ Unit │ Quality││
│  ├──────────┼────────┼───────┼──────┼────────┤│
│  │ Signal   │ RSRP   │ -95.5 │ dBm  │ [Good] ││
│  │ Signal   │ SINR   │ 15.3  │ dB   │ [Good] ││
│  └──────────┴────────┴───────┴──────┴────────┘│
└────────────────────────────────────────────────┘
```

---

### 方式 2：CLI 工具（甲方最愛）⭐⭐⭐⭐⭐

```bash
# 查詢 Beam 1 的所有 KPI
./scripts/query-beam.sh 1

# 查詢 Beam 2 的吞吐量
./scripts/query-beam.sh 2 throughput

# 查詢 Beam 5 的信號品質
./scripts/query-beam.sh 5 signal_quality
```

**優點**：
- ✅ 最簡單！一條命令搞定
- ✅ 適合 Demo 展示
- ✅ 彩色輸出，清晰易讀

---

### 方式 3：REST API⭐⭐⭐⭐

```bash
# 查詢 Beam 1 所有 KPI
curl "http://localhost:8081/api/beam/1/kpi"

# 查詢 Beam 2 的吞吐量
curl "http://localhost:8081/api/beam/2/kpi?kpi_type=throughput"

# 使用 jq 格式化
curl -s "http://localhost:8081/api/beam/5/kpi?kpi_type=signal_quality" | jq '.'
```

**優點**：
- ✅ 標準 RESTful API
- ✅ 適合程式化調用
- ✅ 可整合到其他系統

---

## 📁 專案結構

```
frontend-beam-query/
├── index.html      # 主頁面（Material Design 風格）
├── app.js          # JavaScript 應用邏輯
├── server.py       # HTTP Server (Python 3)
└── README.md       # 本文件
```

---

## 🎨 設計風格

### 配色方案（Material Design）

- **Primary**: Deep Purple (#673ab7)
- **Accent**: Amber (#ffc107)
- **Success**: Green (#4caf50)
- **Warning**: Orange (#ff9800)
- **Error**: Red (#f44336)

### UI 組件

- ✅ **Cards**: Material Design 卡片佈局
- ✅ **Buttons**: Material Design 按鈕（大寫、陰影）
- ✅ **Tables**: 懸浮效果、斑馬紋
- ✅ **Badges**: 動態品質標籤（顏色編碼）
- ✅ **Loading**: Material Design Spinner

---

## 🔧 配置

### API 端點配置

編輯 `app.js` 的 `CONFIG` 物件：

```javascript
const CONFIG = {
    API_BASE_URL: 'http://localhost:8081',  // KPIMON API
    AUTO_REFRESH_INTERVAL: 0,                // 自動刷新間隔（毫秒），0 = 停用
    DEFAULT_BEAM_ID: 5                       // 預設 Beam ID
};
```

### 自動刷新

如需啟用自動刷新（每 5 秒）：

```javascript
AUTO_REFRESH_INTERVAL: 5000  // 5 seconds
```

---

## 📊 KPI 品質標準

### RSRP (Reference Signal Received Power)

| 範圍 | 品質 | Badge 顏色 |
|------|------|-----------|
| > -80 dBm | Excellent | 🟢 Green |
| -80 ~ -90 dBm | Good | 🟢 Green |
| -90 ~ -100 dBm | Fair | 🟡 Orange |
| < -100 dBm | Poor | 🔴 Red |

### SINR (Signal-to-Interference-plus-Noise Ratio)

| 範圍 | 品質 | Badge 顏色 |
|------|------|-----------|
| > 20 dB | Excellent | 🟢 Green |
| 13 ~ 20 dB | Good | 🟢 Green |
| 0 ~ 13 dB | Fair | 🟡 Orange |
| < 0 dB | Poor | 🔴 Red |

---

## 🧪 測試

### 功能測試

```bash
# 1. 確認 KPIMON 運行
curl http://localhost:8081/health/alive
# Expected: {"status":"alive"}

# 2. 測試 API
curl "http://localhost:8081/api/beam/5/kpi?kpi_type=all"
# Expected: JSON response with KPI data

# 3. 測試 UI
curl http://localhost:8000/
# Expected: HTTP 200
```

### 瀏覽器測試

1. 開啟 http://localhost:8000/
2. 開啟瀏覽器開發者工具（F12）
3. 查看 Console 確認無錯誤
4. 查看 Network tab 確認 API 調用成功

---

## 📦 部署建議

### 生產環境部署

#### 方案 1：Nginx 反向代理

```nginx
server {
    listen 80;
    server_name beam-query.example.com;

    location / {
        root /path/to/frontend-beam-query;
        index index.html;
    }

    location /api/ {
        proxy_pass http://kpimon.ricxapp.svc.cluster.local:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### 方案 2：Kubernetes Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: beam-query-ui
  namespace: ricxapp
spec:
  rules:
  - host: beam-query.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: beam-query-ui
            port:
              number: 80
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: kpimon
            port:
              number: 8081
```

---

## 🆚 與舊版 UI 比較

| 特性 | 舊版 (beam-query-interface.html) | 新版 (專業版) |
|------|----------------------------------|---------------|
| **設計風格** | 基本 HTML/CSS | Material Design |
| **UI 框架** | 無 | Bootstrap 5 |
| **響應式** | ❌ | ✅ |
| **Quick Stats** | ❌ | ✅ |
| **品質標籤** | ❌ | ✅ (動態顏色) |
| **詳細表格** | ❌ | ✅ |
| **Loading 狀態** | ❌ | ✅ |
| **Error 處理** | 基本 | 完善 |
| **專業感** | ⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 🔐 安全注意事項

1. **CORS**: 生產環境應限制 CORS origin
2. **Authentication**: 建議加入身份驗證
3. **HTTPS**: 生產環境必須使用 HTTPS
4. **Input Validation**: API 端已實作輸入驗證

---

## 📞 Support

### 問題回報

請聯繫：蔡秀吉 (thc1006)

### 相關文檔

- [Beam Query API 文檔](../docs/BEAM_QUERY_USAGE_GUIDE.md)
- [KPIMON README](../xapps/kpimon-go-xapp/README.md)
- [E2 Simulator README](../simulator/e2-simulator/README.md)

---

## 📝 更新日誌

### v2.0.0 (2025-11-19)

- ✨ 全新 Material Design UI
- ✨ Quick Stats 卡片
- ✨ 智慧品質標籤
- ✨ 詳細 KPI 表格
- ✨ Loading / Error 狀態
- ✨ 響應式設計

### v1.0.0 (2025-11-18)

- 🎉 初版發布（基本 HTML UI）

---

**Enjoy querying Beam KPIs! 📡**
