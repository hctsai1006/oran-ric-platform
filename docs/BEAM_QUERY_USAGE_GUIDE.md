# Beam KPI Query - 使用指南

**日期**: 2025-11-19
**版本**: 1.0.0

---

##   目錄

- [1. 功能概述](#1-功能概述)
- [2. 架構說明](#2-架構說明)
- [3. 使用方式比較](#3-使用方式比較)
- [4. 快速開始](#4-快速開始)
- [5. 進階使用](#5-進階使用)
- [6. 甲方需求分析](#6-甲方需求分析)

---

## 1. 功能概述

### 核心功能

 [DONE] **輸入 Beam ID → 返回該 Beam 的 KPI 數據**

```
使用者輸入: Beam ID = 1
          ↓
    Query API 查詢
          ↓
返回: Beam 1 的 KPI 數據（RSRP, SINR, Throughput, etc.）
```

### 支援的 Beam IDs

- **範圍**: 0-7（對應 5G NR SSB Index）
- **說明**: 每個 Beam 代表一個波束方向，有獨立的信號品質和性能指標

### 支援的 KPI 類型

| KPI 類型 | 說明 | 關鍵指標 |
|---------|------|----------|
| **signal_quality** | 信號品質 | RSRP, RSRQ, SINR |
| **throughput** | 吞吐量 | Downlink/Uplink Mbps |
| **packet_loss** | 封包遺失率 | Downlink/Uplink % |
| **resource_utilization** | 資源利用率 | PRB Usage DL/UL % |
| **all** | 所有 KPI | （預設） |

---

## 2. 架構說明

### 2.1 數據流程

```
┌─────────────────┐
│  E2 Simulator   │  持續生成 Beam 0-7 的 KPI 數據
└────────┬────────┘
         │ HTTP POST /e2/indication
         │ (包含 beam_id)
         ↓
┌─────────────────┐
│    KPIMON       │  接收並按 beam_id 分組儲存
│  (Flask API)    │
└────────┬────────┘
         │ 存儲到 Redis
         │ Key: kpi:beam:{beam_id}:*
         ↓
┌─────────────────┐
│  Redis          │  持久化儲存（按 Beam ID 分類）
└────────┬────────┘
         ↑ 查詢
         │
┌─────────────────┐
│ Beam Query API  │  GET /api/beam/{beam_id}/kpi
│  (Flask API)    │
└────────┬────────┘
         ↑ HTTP GET
         │
┌─────────────────┐
│   使用者        │  選擇查詢方式（見下方）
└─────────────────┘
```

### 2.2 Redis 數據結構

```redis
# Beam 1 的數據
kpi:beam:1:throughput:downlink
kpi:beam:1:throughput:uplink
kpi:beam:1:signal:rsrp
kpi:beam:1:signal:rsrq
kpi:beam:1:signal:sinr
kpi:beam:1:packet_loss:downlink

# Beam 2 的數據
kpi:beam:2:throughput:downlink
...
```

---

## 3. 使用方式比較

### 方案 A：CLI 工具 （推薦給甲方）

**最簡單！一條命令搞定！**

```bash
# 查詢 Beam 1 的所有 KPI
./scripts/query-beam.sh 1

# 查詢 Beam 2 的吞吐量
./scripts/query-beam.sh 2 throughput

# 查詢 Beam 5 的信號品質
./scripts/query-beam.sh 5 signal_quality
```

**優點**：
-  [DONE] **極度簡單**：一條命令，不需要記憶 API 格式
-  [DONE] **適合 Demo**：快速展示不同 Beam 的 KPI
-  [DONE] **彩色輸出**：清晰易讀
-  [DONE] **自動格式化**：JSON 自動美化

**缺點**：
-  [WARN] 需要終端機環境
-  [WARN] 不適合程式化調用（使用 REST API 更好）

---

### 方案 B：REST API 

**適合程式化調用**

```bash
# 查詢 Beam 1 所有 KPI
curl http://localhost:8081/api/beam/1/kpi

# 查詢 Beam 2 的吞吐量
curl "http://localhost:8081/api/beam/2/kpi?kpi_type=throughput"

# 查詢 Beam 5 的信號品質
curl "http://localhost:8081/api/beam/5/kpi?kpi_type=signal_quality"
```

**API 規格**：

```
Endpoint: GET /api/beam/{beam_id}/kpi
Parameters:
  - beam_id: integer (0-7)
  - kpi_type: string (可選)
    - all (預設)
    - throughput
    - signal_quality
    - packet_loss
    - resource_utilization
  - time_range: string (可選)
    - current (預設)
    - last_5min
    - last_hour

Response:
{
  "beam_id": 1,
  "status": "success",
  "count": 11,
  "data": {
    "signal_quality": {
      "rsrp": {"value": -95.5, "unit": "dBm"},
      "rsrq": {"value": -10.2, "unit": "dB"},
      "sinr": {"value": 15.3, "unit": "dB"}
    },
    "throughput": {
      "downlink": {"value": 45.2, "unit": "Mbps"},
      "uplink": {"value": 22.1, "unit": "Mbps"}
    }
  }
}
```

**優點**：
-  [DONE] 標準 RESTful API
-  [DONE] 適合程式化調用（Python, JavaScript 等）
-  [DONE] 可整合到其他系統
-  [DONE] 支援參數化查詢

**缺點**：
-  [WARN] 需要記憶 API 格式
-  [WARN] 手動調用需要 curl 或其他工具

---

### 方案 C：Web UI 

**圖形化介面**

```bash
# 開啟瀏覽器
http://localhost:8889/

# 在 UI 中:
# 1. 選擇 Beam ID (下拉選單)
# 2. 選擇 KPI Type
# 3. 點擊 "查詢"
# 4. 查看結果（表格和圖表）
```

**優點**：
-  [DONE] 視覺化友善
-  [DONE] 不需要記憶命令
-  [DONE] 支援圖表展示
-  [DONE] 適合非技術人員

**缺點**：
-  [WARN] 需要瀏覽器
-  [WARN] 需要 port forwarding（遠端環境）

---

### 方案 D：Python 腳本 

**程式化查詢**

```python
import requests

def query_beam_kpi(beam_id, kpi_type='all'):
    url = f"http://localhost:8081/api/beam/{beam_id}/kpi"
    params = {'kpi_type': kpi_type}
    response = requests.get(url, params=params)
    return response.json()

# 使用
data = query_beam_kpi(beam_id=1, kpi_type='signal_quality')
print(f"Beam 1 RSRP: {data['data']['signal_quality']['rsrp']['value']} dBm")
```

**優點**：
-  [DONE] 完全程式化
-  [DONE] 可自動化批次查詢
-  [DONE] 可整合到分析流程

**缺點**：
-  [WARN] 需要撰寫程式碼

---

## 4. 快速開始

### 4.1 環境確認

```bash
# 1. 確認 KPIMON 運行
kubectl get pods -n ricxapp | grep kpimon
# Expected: kpimon-xxx  1/1  Running

# 2. 確認 E2 Simulator 運行
kubectl get pods -n ricxapp | grep e2-simulator
# Expected: e2-simulator-xxx  1/1  Running

# 3. 確認 port forwarding
curl -s http://localhost:8081/health/alive
# Expected: {"status":"alive"}
```

### 4.2 方式 1：CLI 工具（最簡單）

```bash
# 查詢 Beam 1 的所有 KPI
bash scripts/query-beam.sh 1

# 查詢 Beam 2 的吞吐量
bash scripts/query-beam.sh 2 throughput

# 查詢 Beam 5 的信號品質
bash scripts/query-beam.sh 5 signal_quality
```

### 4.3 方式 2：REST API

```bash
# 使用 curl
curl "http://localhost:8081/api/beam/1/kpi?kpi_type=signal_quality" | jq '.'

# 使用 httpie（更友善）
http GET localhost:8081/api/beam/1/kpi kpi_type==signal_quality
```

### 4.4 方式 3：Web UI

```bash
# 開啟瀏覽器
open http://localhost:8889/

# 或在 VS Code 的 PORTS 標籤點擊 8889 旁的地球圖示
```

---

## 5. 進階使用

### 5.1 批次查詢多個 Beams

```bash
# Bash 腳本
for beam in 1 2 3 5; do
    echo "=== Beam $beam ==="
    bash scripts/query-beam.sh $beam signal_quality
    echo ""
done
```

### 5.2 監控特定 Beam 的變化

```bash
# 每 5 秒查詢一次 Beam 1 的 RSRP
watch -n 5 'curl -s "http://localhost:8081/api/beam/1/kpi?kpi_type=signal_quality" | jq ".data.signal_quality.rsrp.value"'
```

### 5.3 比較多個 Beams 的性能

```python
import requests
import pandas as pd

beams = [1, 2, 3, 5]
results = []

for beam_id in beams:
    url = f"http://localhost:8081/api/beam/{beam_id}/kpi?kpi_type=signal_quality"
    data = requests.get(url).json()

    results.append({
        'beam_id': beam_id,
        'rsrp': data['data']['signal_quality']['rsrp']['value'],
        'sinr': data['data']['signal_quality']['sinr']['value']
    })

df = pd.DataFrame(results)
print(df)

# Output:
#    beam_id      rsrp      sinr
# 0        1    -95.5      15.3
# 1        2    -92.3      18.7
# 2        3    -98.1      12.4
# 3        5    -89.7      21.2
```

---

## 6. 甲方需求分析

### 6.1 原始需求

> "希望有一個介面可以輸入 Beam ID 例如 1 或是 2，KPM 就可以有一個回傳的資訊"

### 6.2 需求解讀

| 需求面向 | 甲方期望 | 我們的實作 | 狀態 |
|---------|---------|-----------|------|
| **輸入方式** | 可以指定 Beam ID | CLI / REST API / Web UI |  [DONE] 已實作 |
| **查詢模式** | 主動查詢（Pull） | GET /api/beam/{id}/kpi |  [DONE] 已實作 |
| **返回數據** | Beam 的 KPI 數據 | 完整 KPI（RSRP, SINR, etc.） |  [DONE] 已實作 |
| **簡易性** | 越簡單越好 | CLI 工具一條命令 |  [DONE] 已實作 |
| **即時性** | 即時返回結果 | < 100ms 響應時間 |  [DONE] 已實作 |

### 6.3 建議方案（給甲方）

根據甲方說：
> "用 web API 整應該比較麻煩吧？我是想說現在就用愈簡單的方式秀一下愈好"

**推薦方案排序**：

#### 🥇 第一推薦：CLI 工具

```bash
# 最簡單！一條命令搞定
./scripts/query-beam.sh 1
./scripts/query-beam.sh 2 throughput
```

**理由**：
-  [DONE] 不需要記 API 格式
-  [DONE] 適合 Demo 展示
-  [DONE] 輸出美觀易讀

#### 🥈 第二推薦：Web UI

```
http://localhost:8889/
```

**理由**：
-  [DONE] 圖形化，直覺
-  [DONE] 適合非技術人員
-  [DONE] 支援視覺化

#### 🥉 第三推薦：REST API

```bash
curl http://localhost:8081/api/beam/1/kpi
```

**理由**：
-  [DONE] 標準化
-  [DONE] 可程式化調用
-  [WARN] 需要記憶 API 格式

---

## 7. Troubleshooting

### 問題 1：查詢失敗（Connection refused）

```bash
# 確認 port forwarding
ps aux | grep "kubectl port-forward" | grep 8081

# 如果沒有，啟動 port forwarding
kubectl port-forward -n ricxapp svc/kpimon 8081:8081
```

### 問題 2：返回空數據

```bash
# 確認 E2 Simulator 正在發送數據
kubectl logs -n ricxapp e2-simulator --tail=20

# 確認 KPIMON 正在接收
kubectl logs -n ricxapp kpimon --tail=20
```

### 問題 3：特定 Beam ID 沒有數據

```bash
# 檢查 Redis 中是否有該 Beam 的數據
kubectl exec -n ricplt redis-cluster-0 -- redis-cli KEYS "kpi:beam:1:*"

# 如果沒有，可能是 Simulator 隨機分配，等待下一次數據生成
```

---

## 8. 附錄

### 8.1 完整 API 文檔

參考：[BEAM_KPI_COMPLETE_GUIDE.md](./BEAM_KPI_COMPLETE_GUIDE.md)

### 8.2 架構圖

參考：`docs/diagrams/beam-kpi-architecture.png`

### 8.3 相關文件

- [KPIMON README](../xapps/kpimon-go-xapp/README.md)
- [E2 Simulator README](../simulator/e2-simulator/README.md)

---

**更新日期**: 2025-11-19
**維護者**: 蔡秀吉 (thc1006)
**版本**: 1.0.0
