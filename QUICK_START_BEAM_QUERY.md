# Beam KPI Query - 快速開始指南

**作者**: 蔡秀吉 (thc1006)
**日期**: 2025-11-19
**專案**: O-RAN RIC Platform - Beam KPI Query System

---

## 🎯 給甲方：最簡單的使用方式

親愛的甲方，我們提供了**三種查詢方式**，按簡易度排序：

---

### 方式 1：專業 Web UI ⭐⭐⭐⭐⭐（推薦！）

**一鍵啟動，瀏覽器查詢**

```bash
# 1. 啟動服務器
cd frontend-beam-query
python3 proxy-server.py

# 2. 在瀏覽器開啟
http://localhost:8888/
```

**操作超簡單**：
1. 選擇 **Beam ID** (1-7)
2. 點擊 **Query** 按鈕
3. 查看結果！

**看到什麼**：
- ✅ Quick Stats（RSRP, SINR, Throughput）
- ✅ 詳細表格（所有 KPI 指標）
- ✅ 品質標籤（Excellent, Good, Fair, Poor）
- ✅ 專業設計（Material Design 風格）

**截圖範例**：
```
┌──────────────────────────────────────────────┐
│ O-RAN RIC - Beam KPI Query Dashboard        │
└──────────────────────────────────────────────┘
┌─────────┬─────────┬──────────┬──────────────┐
│ RSRP    │ SINR    │ DL Thpt  │ UL Thpt      │
│ -95.5   │ 15.3    │ 45.2     │ 22.1         │
│ [Good]  │ [Good]  │ Mbps     │ Mbps         │
└─────────┴─────────┴──────────┴──────────────┘
```

---

### 方式 2：命令列工具 ⭐⭐⭐⭐⭐（最快！）

**一條命令搞定**

```bash
# 查詢 Beam 1 的所有 KPI
./scripts/query-beam.sh 1

# 查詢 Beam 2 的吞吐量
./scripts/query-beam.sh 2 throughput

# 查詢 Beam 5 的信號品質
./scripts/query-beam.sh 5 signal_quality
```

**優點**：
- ✅ 最簡單！一條命令
- ✅ 適合 Demo 展示
- ✅ 彩色輸出，清晰易讀

---

### 方式 3：REST API ⭐⭐⭐⭐（程式化調用）

**適合整合到其他系統**

```bash
# 查詢 Beam 1 所有 KPI
curl "http://localhost:8081/api/beam/1/kpi"

# 查詢 Beam 2 的吞吐量
curl "http://localhost:8081/api/beam/2/kpi?kpi_type=throughput"

# 美化輸出
curl -s "http://localhost:8081/api/beam/5/kpi" | jq '.'
```

---

## 📊 支援的 Beam IDs 和 KPI 類型

### Beam IDs
- **範圍**: 1-7（對應 5G NR SSB Index）
- **說明**: 每個 Beam 代表一個波束方向

### KPI 類型
| KPI Type | 說明 | 包含指標 |
|----------|------|---------|
| `all` | 所有 KPI（預設） | 所有以下指標 |
| `signal_quality` | 信號品質 | RSRP, RSRQ, SINR |
| `throughput` | 吞吐量 | Downlink/Uplink Mbps |
| `packet_loss` | 封包遺失率 | Downlink/Uplink % |
| `resource_utilization` | 資源利用率 | PRB Usage DL/UL % |

---

## 🚀 完整使用範例

### 範例 1：查詢 Beam 1 的信號品質

**CLI**：
```bash
./scripts/query-beam.sh 1 signal_quality
```

**Web UI**：
1. 開啟 http://localhost:8888/
2. 選擇 Beam ID = 1
3. 選擇 KPI Type = Signal Quality
4. 點擊 Query

**API**：
```bash
curl "http://localhost:8081/api/beam/1/kpi?kpi_type=signal_quality"
```

**返回範例**：
```json
{
  "beam_id": 1,
  "status": "success",
  "data": {
    "signal_quality": {
      "rsrp": {
        "value": -95.5,
        "unit": "dBm",
        "quality": "good"
      },
      "sinr": {
        "value": 15.3,
        "unit": "dB",
        "quality": "good"
      }
    }
  }
}
```

---

### 範例 2：比較多個 Beams 的吞吐量

**CLI**：
```bash
for beam in 1 2 5; do
    echo "=== Beam $beam ==="
    ./scripts/query-beam.sh $beam throughput
done
```

**Web UI**：
依序選擇 Beam 1, 2, 5 查詢

---

## 🔧 環境檢查

在使用前，確認以下服務運行：

```bash
# 1. 檢查 KPIMON（必須運行）
kubectl get pods -n ricxapp | grep kpimon
# Expected: kpimon-xxx  1/1  Running

# 2. 檢查 E2 Simulator（必須運行）
kubectl get pods -n ricxapp | grep e2-simulator
# Expected: e2-simulator-xxx  1/1  Running

# 3. 檢查 API 健康狀態
curl http://localhost:8081/health/alive
# Expected: {"status":"alive"}
```

---

## 🆚 三種方式比較

| 特性 | Web UI | CLI 工具 | REST API |
|------|--------|----------|----------|
| **簡易度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **視覺化** | ✅ 完整 | ⚠️ 文字 | ❌ JSON |
| **適合對象** | 所有人 | 技術人員 | 開發者 |
| **Demo 展示** | ✅ 最佳 | ✅ 快速 | ⚠️ 需工具 |
| **程式化調用** | ❌ | ⚠️ Shell 腳本 | ✅ 最佳 |
| **學習曲線** | 最低 | 低 | 中 |

---

## 🎓 使用建議

### 給甲方（Demo/展示）
推薦：**Web UI** 或 **CLI 工具**
理由：直觀、快速、視覺化

### 給開發者（整合/測試）
推薦：**REST API** 或 **CLI 工具**
理由：可程式化、可自動化

### 給運維人員（日常監控）
推薦：**Web UI**
理由：完整視覺化、易於監控

---

## ❓ 常見問題

### Q1: Web UI 無法載入數據？

**解決**：
1. 確認使用 **http://localhost:8888/**（不是 8000）
2. 確認 KPIMON 運行：`kubectl get pods -n ricxapp`
3. 查看瀏覽器 Console（F12）檢查錯誤

### Q2: CLI 工具顯示 "Connection failed"？

**解決**：
```bash
# 檢查 port forwarding
ps aux | grep "kubectl port-forward" | grep 8081

# 如果沒有，啟動 port forwarding
kubectl port-forward -n ricxapp svc/kpimon 8081:8081
```

### Q3: 某個 Beam 沒有數據？

**原因**: E2 Simulator 隨機生成 Beams，該 Beam 可能還沒有數據

**解決**: 等待幾秒鐘，E2 Simulator 會持續發送數據（每 5 秒一次）

---

## 📞 支援

**問題回報**：蔡秀吉 (thc1006)

**相關文檔**：
- [完整使用指南](docs/BEAM_QUERY_USAGE_GUIDE.md)
- [Web UI README](frontend-beam-query/README.md)
- [KPIMON README](xapps/kpimon-go-xapp/README.md)

---

## 🎉 Quick Tips

1. ✅ **最快方式**：CLI 工具（一條命令）
2. ✅ **最專業**：Web UI（視覺化完整）
3. ✅ **最靈活**：REST API（可程式化）
4. ✅ **Demo 展示**：Web UI + 投影螢幕
5. ✅ **日常使用**：依個人習慣選擇

---

**That's it! 現在開始查詢 Beam KPIs! 📡**
