# Beam KPI 查詢系統 - 數據流程詳解

**作者**: 蔡秀吉 (thc1006)
**日期**: 2025-11-19
**目的**: 詳細說明前端和 CLI 工具如何獲取 Beam KPI 數據

---

##   完整數據流程圖

```
┌─────────────────────────────────────────────────────────────────┐
│  第一階段：數據生成與儲存                                        │
└─────────────────────────────────────────────────────────────────┘

1. E2 Simulator 生成 KPI 數據
   ├─ 模擬 3 個 Cells (cell_001, cell_002, cell_003)
   ├─ 模擬 ~20 個 UEs (ue_001 ~ ue_020)
   ├─ 生成 8 個 Beams (Beam 0-7) 的 KPI
   └─ 每 5 秒生成一次

              ↓ HTTP POST /e2/indication

2. KPIMON 接收並處理
   ├─ 解析 E2 indication message
   ├─ 提取每個 Beam 的 KPI 數據:
   │   ├─ Signal Quality: RSRP, RSRQ, SINR
   │   ├─ Throughput: Downlink/Uplink Mbps
   │   ├─ Packet Loss: Downlink/Uplink %
   │   └─ Resource Utilization: PRB Usage DL/UL
   └─ 計算品質等級 (Excellent/Good/Fair/Poor)

              ↓ 儲存到 Redis

3. Redis 數據結構
   Key 格式: "beam:{beam_id}:kpi"
   例如: "beam:5:kpi"

   Value (JSON):
   {
     "beam_id": 5,
     "cell_id": "cell_002",
     "signal_quality": {
       "rsrp": {"value": -95.5, "unit": "dBm", "quality": "good"},
       "rsrq": {"value": -10.2, "unit": "dB", "quality": "good"},
       "sinr": {"value": 15.3, "unit": "dB", "quality": "good"}
     },
     "throughput": {
       "downlink": {"value": 45.2, "unit": "Mbps"},
       "uplink": {"value": 22.1, "unit": "Mbps"}
     },
     "packet_loss": {
       "downlink": {"value": 0.5, "unit": "%"},
       "uplink": {"value": 0.3, "unit": "%"}
     },
     "resource_utilization": {
       "prb_usage_dl": {"value": 35.0, "unit": "%"},
       "prb_usage_ul": {"value": 20.0, "unit": "%"}
     },
     "metadata": {
       "ue_count": 5,
       "timestamp": "2025-11-19T10:30:45Z"
     }
   }

┌─────────────────────────────────────────────────────────────────┐
│  第二階段：數據查詢（三種方式）                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

##   方式 1: CLI 工具 (scripts/query-beam.sh)

### 1.1 腳本內容

```bash
#!/bin/bash
# scripts/query-beam.sh

BEAM_ID=${1:-1}
KPI_TYPE=${2:-all}

# API 基礎 URL
API_URL="http://localhost:8081"

# 構建查詢 URL
QUERY_URL="${API_URL}/api/beam/${BEAM_ID}/kpi"

# 如果指定 KPI 類型，添加參數
if [ "$KPI_TYPE" != "all" ]; then
    QUERY_URL="${QUERY_URL}?kpi_type=${KPI_TYPE}"
fi

# 發送 HTTP GET 請求
curl -s "${QUERY_URL}" | jq '.'
```

### 1.2 數據流程

```
使用者執行: ./scripts/query-beam.sh 5
              ↓
┌──────────────────────────────┐
│  1. Bash 腳本執行            │
│     - BEAM_ID=5              │
│     - KPI_TYPE=all           │
└──────────────┬───────────────┘
              ↓
┌──────────────────────────────┐
│  2. 構建 URL                 │
│     http://localhost:8081/   │
│     api/beam/5/kpi           │
└──────────────┬───────────────┘
              ↓
┌──────────────────────────────┐
│  3. curl 發送 HTTP GET       │
│     curl -s <URL>            │
└──────────────┬───────────────┘
              ↓
         [網路請求]
              ↓
┌──────────────────────────────┐
│  4. KPIMON API 接收          │
│     Port: 8081               │
│     Endpoint: /api/beam/5/kpi│
└──────────────┬───────────────┘
              ↓
┌──────────────────────────────┐
│  5. KPIMON 查詢 Redis        │
│     redis_client.get(        │
│       "beam:5:kpi"           │
│     )                        │
└──────────────┬───────────────┘
              ↓
         [Redis 查詢]
              ↓
┌──────────────────────────────┐
│  6. Redis 返回數據           │
│     {JSON 格式 KPI 數據}     │
└──────────────┬───────────────┘
              ↓
┌──────────────────────────────┐
│  7. KPIMON 格式化回應        │
│     添加 status, timestamp   │
└──────────────┬───────────────┘
              ↓
┌──────────────────────────────┐
│  8. HTTP Response (JSON)     │
│     Status: 200 OK           │
│     Content-Type: json       │
└──────────────┬───────────────┘
              ↓
┌──────────────────────────────┐
│  9. curl 接收回應            │
└──────────────┬───────────────┘
              ↓
┌──────────────────────────────┐
│  10. jq 格式化輸出           │
│      (彩色 JSON)             │
└──────────────┬───────────────┘
              ↓
         終端顯示結果
```

### 1.3 實際範例

```bash
$ ./scripts/query-beam.sh 5

# 執行過程:
# 1. curl http://localhost:8081/api/beam/5/kpi
# 2. KPIMON API 處理
# 3. 查詢 Redis: GET beam:5:kpi
# 4. 返回 JSON

# 輸出:
{
  "beam_id": 5,
  "status": "success",
  "timestamp": "2025-11-19T10:30:45Z",
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
    },
    "throughput": {
      "downlink": {
        "value": 45.2,
        "unit": "Mbps"
      }
    }
  }
}
```

---

##   方式 2: Web UI (frontend-beam-query/)

### 2.1 架構組件

```
frontend-beam-query/
├── index.html         # Material Design UI
├── app.js             # JavaScript 應用邏輯
└── proxy-server.py    # HTTP Proxy Server (解決 CORS)
```

### 2.2 完整數據流程

```
用戶在瀏覽器操作
    ↓
┌─────────────────────────────────────────────┐
│  1. 用戶動作                                │
│     - 在下拉選單選擇 Beam ID = 5            │
│     - 點擊 "Query" 按鈕                     │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  2. JavaScript 事件處理 (app.js)           │
│     function handleQuery(event) {           │
│       event.preventDefault();               │
│       const beamID = 5;                     │
│       const kpiType = 'all';                │
│       queryBeamKPI(beamID, kpiType);        │
│     }                                       │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  3. 構建 API URL (app.js)                  │
│     const url =                             │
│       `/api/beam/${beamID}/kpi?kpi_type=all`;│
│                                             │
│     注意: API_BASE_URL = '' (空字串)        │
│     = Same Origin (使用 proxy)              │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  4. 發送 Fetch 請求 (瀏覽器)               │
│     fetch('/api/beam/5/kpi?kpi_type=all')   │
│                                             │
│     請求目標: http://localhost:8888/        │
│               api/beam/5/kpi                │
│     (因為 Web UI 從 port 8888 載入)         │
└─────────────────┬───────────────────────────┘
                  ↓
         [HTTP GET Request]
         Origin: http://localhost:8888
                  ↓
┌─────────────────────────────────────────────┐
│  5. proxy-server.py 接收請求                │
│     class BeamProxyHandler:                 │
│       def do_GET(self):                     │
│         if path.startswith('/api/'):        │
│           self.proxy_to_api()               │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  6. Proxy 轉發請求                          │
│     target_url =                            │
│       "http://localhost:8081" + self.path   │
│       = "http://localhost:8081/api/beam/5/kpi"│
│                                             │
│     urllib.request.urlopen(target_url)      │
└─────────────────┬───────────────────────────┘
                  ↓
         [HTTP GET to KPIMON API]
         Target: localhost:8081
                  ↓
┌─────────────────────────────────────────────┐
│  7. KPIMON API 接收 (同 CLI 工具)          │
│     @app.route('/api/beam/<int:beam_id>/kpi')│
│     def get_beam_kpi(beam_id):              │
│       # beam_id = 5                         │
│       kpi_type = request.args.get('kpi_type')│
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  8. KPIMON 查詢 Redis                       │
│     redis_key = f"beam:{beam_id}:kpi"       │
│     redis_client.get(redis_key)             │
│     # 查詢 "beam:5:kpi"                     │
└─────────────────┬───────────────────────────┘
                  ↓
         [Redis GET beam:5:kpi]
                  ↓
┌─────────────────────────────────────────────┐
│  9. Redis 返回數據                          │
│     {JSON 格式的 Beam 5 KPI 數據}           │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  10. KPIMON 格式化回應                      │
│      response = {                           │
│        "beam_id": 5,                        │
│        "status": "success",                 │
│        "timestamp": "...",                  │
│        "data": {...}                        │
│      }                                      │
│      return jsonify(response), 200          │
└─────────────────┬───────────────────────────┘
                  ↓
         [HTTP 200 OK + JSON]
                  ↓
┌─────────────────────────────────────────────┐
│  11. proxy-server.py 接收回應               │
│      content = response.read()              │
│      self.send_response(200)                │
│      self.send_header('Content-Type', 'json')│
│      self.wfile.write(content)              │
└─────────────────┬───────────────────────────┘
                  ↓
         [HTTP Response 返回瀏覽器]
         Origin: http://localhost:8888
                  ↓
┌─────────────────────────────────────────────┐
│  12. 瀏覽器接收回應                         │
│      fetch(...).then(response =>            │
│        response.json()                      │
│      )                                      │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  13. JavaScript 處理數據 (app.js)          │
│      function displayResults(data) {        │
│        updateQuickStats(data.data);         │
│        updateKPITable(data.data);           │
│        updateMetadata(data);                │
│      }                                      │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  14. 更新 UI 元素                           │
│      A. Quick Stats 卡片:                   │
│         document.getElementById('statRSRP') │
│           .textContent = -95.5              │
│                                             │
│      B. KPI 表格:                           │
│         插入 <tr> rows 到 table             │
│                                             │
│      C. 品質標籤:                           │
│         <span class="badge-success">        │
│           Good                              │
│         </span>                             │
└─────────────────┬───────────────────────────┘
                  ↓
         用戶看到視覺化結果
```

### 2.3 為什麼需要 Proxy Server？

#### 問題: CORS (Cross-Origin Resource Sharing)

```
瀏覽器安全策略:
  同源政策 (Same-Origin Policy) 禁止:

  http://localhost:8000  (Web UI)
        ↓ fetch()
  http://localhost:8081  (KPIMON API)   [FAIL] 不同 Port = 不同 Origin

  錯誤:
  Access to fetch at 'http://localhost:8081/api/beam/5/kpi'
  from origin 'http://localhost:8000' has been blocked by CORS policy
```

#### 解決方案: Proxy Server

```
瀏覽器 ←→ proxy-server.py (port 8888) ←→ KPIMON API (port 8081)
         同一 Origin  [DONE]               Server-to-Server  [DONE]
         (http://localhost:8888)     (無 CORS 限制)
```

**proxy-server.py 核心邏輯**:

```python
class BeamProxyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)

        # 檢查是否為 API 請求
        if parsed_path.path.startswith('/api/'):
            # 轉發到 KPIMON API
            target_url = f"http://localhost:8081{self.path}"

            # 發送請求到 KPIMON
            req = urllib.request.Request(target_url)
            response = urllib.request.urlopen(req, timeout=10)

            # 讀取回應
            content = response.read()

            # 返回給瀏覽器（添加 CORS headers）
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(content)
        else:
            # 靜態文件 (index.html, app.js)
            super().do_GET()
```

---

## 🔌 方式 3: REST API (直接調用)

### 3.1 cURL 範例

```bash
# 基本查詢
curl "http://localhost:8081/api/beam/5/kpi"

# 指定 KPI 類型
curl "http://localhost:8081/api/beam/5/kpi?kpi_type=signal_quality"

# 指定時間範圍
curl "http://localhost:8081/api/beam/5/kpi?time_range=last_5min"

# 組合參數
curl "http://localhost:8081/api/beam/5/kpi?kpi_type=throughput&time_range=current"
```

### 3.2 Python 範例

```python
import requests

# 查詢 Beam 5 的所有 KPI
response = requests.get('http://localhost:8081/api/beam/5/kpi')

if response.status_code == 200:
    data = response.json()

    # 提取 RSRP 值
    rsrp = data['data']['signal_quality']['rsrp']['value']
    print(f"Beam 5 RSRP: {rsrp} dBm")

    # 提取吞吐量
    dl_throughput = data['data']['throughput']['downlink']['value']
    print(f"Downlink Throughput: {dl_throughput} Mbps")
```

### 3.3 JavaScript 範例

```javascript
// 在瀏覽器 Console 或 Node.js 中使用
fetch('http://localhost:8081/api/beam/5/kpi')
  .then(response => response.json())
  .then(data => {
    console.log('Beam ID:', data.beam_id);
    console.log('RSRP:', data.data.signal_quality.rsrp.value);
    console.log('Quality:', data.data.signal_quality.rsrp.quality);
  })
  .catch(error => console.error('Error:', error));
```

---

## 📡 KPIMON API 實現細節

### 4.1 API Endpoint 定義

**檔案位置**: `xapps/kpimon-go-xapp/src/api.py`

```python
from flask import Flask, request, jsonify
import redis
import json
import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Redis 連接
redis_client = redis.Redis(
    host='dbaas-tcp.ricplt.svc.cluster.local',
    port=6379,
    decode_responses=True
)

@app.route('/api/beam/<int:beam_id>/kpi', methods=['GET'])
def get_beam_kpi(beam_id):
    """
    查詢指定 Beam 的 KPI 數據

    參數:
        beam_id (int): Beam ID (0-7)
        kpi_type (str, optional): KPI 類型
            - all (默認)
            - signal_quality
            - throughput
            - packet_loss
            - resource_utilization
        time_range (str, optional): 時間範圍
            - current (默認)
            - last_5min
            - last_hour

    返回:
        JSON: {
            "beam_id": int,
            "status": "success" | "error",
            "timestamp": str,
            "data": {...}
        }
    """

    # 1. 驗證 Beam ID
    if not (0 <= beam_id <= 7):
        return jsonify({
            "beam_id": beam_id,
            "status": "error",
            "message": f"Invalid beam_id. Must be 0-7, got {beam_id}"
        }), 400

    # 2. 獲取查詢參數
    kpi_type = request.args.get('kpi_type', 'all')
    time_range = request.args.get('time_range', 'current')

    # 3. 構建 Redis Key
    redis_key = f"beam:{beam_id}:kpi"

    try:
        # 4. 查詢 Redis
        kpi_data_str = redis_client.get(redis_key)

        if not kpi_data_str:
            return jsonify({
                "beam_id": beam_id,
                "status": "error",
                "message": f"No data found for Beam {beam_id}"
            }), 404

        # 5. 解析 JSON
        kpi_data = json.loads(kpi_data_str)

        # 6. 過濾 KPI 類型
        if kpi_type != 'all':
            filtered_data = {
                kpi_type: kpi_data.get(kpi_type, {})
            }
        else:
            filtered_data = kpi_data

        # 7. 構建回應
        response = {
            "beam_id": beam_id,
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "data": filtered_data
        }

        logger.info(f"Successfully queried Beam {beam_id}, KPI type: {kpi_type}")

        return jsonify(response), 200

    except redis.exceptions.ConnectionError as e:
        logger.error(f"Redis connection error: {e}")
        return jsonify({
            "beam_id": beam_id,
            "status": "error",
            "message": "Database connection failed"
        }), 503

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return jsonify({
            "beam_id": beam_id,
            "status": "error",
            "message": "Invalid data format in database"
        }), 500

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return jsonify({
            "beam_id": beam_id,
            "status": "error",
            "message": "Internal server error"
        }), 500

# 啟動 API Server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081)
```

### 4.2 Redis 數據儲存邏輯

**檔案位置**: `xapps/kpimon-go-xapp/src/kpi_processor.py`

```python
def store_beam_kpi(beam_id, kpi_data):
    """
    儲存 Beam KPI 數據到 Redis

    參數:
        beam_id (int): Beam ID
        kpi_data (dict): KPI 數據字典
    """
    redis_key = f"beam:{beam_id}:kpi"

    # 轉換為 JSON
    kpi_json = json.dumps(kpi_data)

    # 儲存到 Redis (設定 TTL 5 分鐘)
    redis_client.setex(
        redis_key,
        300,  # 5 minutes TTL
        kpi_json
    )

    logger.debug(f"Stored KPI for Beam {beam_id}: {redis_key}")
```

---

##   完整循環：從數據生成到顯示

### 5秒循環週期

```
T=0s:
  E2 Simulator 生成 Iteration 1 KPI
    → KPIMON 處理並儲存到 Redis
    → Redis 更新 beam:0:kpi ~ beam:7:kpi
    → 用戶可以立即查詢

T=5s:
  E2 Simulator 生成 Iteration 2 KPI
    → 覆蓋 Redis 中的舊數據
    → 用戶查詢會得到最新數據

T=10s:
  E2 Simulator 生成 Iteration 3 KPI
    ...
```

### 數據一致性

- **寫入頻率**: 每 5 秒更新一次 (E2 Simulator 週期)
- **TTL (Time To Live)**: 300 秒 (5 分鐘)
- **讀取**: 隨時可讀，返回最新寫入的數據

---

##   總結

### 三種查詢方式對比

| 特性 | CLI 工具 | Web UI | REST API |
|------|---------|--------|----------|
| **用戶界面** | 命令列 | 瀏覽器圖形界面 | 程式化調用 |
| **技術** | Bash + cURL | HTML/JS + Proxy | HTTP Client |
| **數據獲取** | HTTP GET | Fetch API → Proxy → HTTP GET | HTTP GET |
| **CORS 問題** | 無 (Server-to-Server) | 有 (用 Proxy 解決) | 無 (Server-to-Server) |
| **適合對象** | 技術人員、Demo | 所有人、視覺化監控 | 開發者、自動化 |
| **響應時間** | ~50ms | ~100ms (含渲染) | ~50ms |

### 核心數據路徑

**所有三種方式的共同點**:
```
查詢請求 → KPIMON API (port 8081)
              ↓
        Redis 查詢 (GET beam:X:kpi)
              ↓
        JSON 回應 → 顯示給用戶
```

**差異在於**:
- **CLI**: 直接 cURL → KPIMON
- **Web UI**: 瀏覽器 → Proxy → KPIMON
- **REST API**: 應用程式 → KPIMON

---

**文檔作者**: 蔡秀吉 (thc1006)
**最後更新**: 2025-11-19
**版本**: 1.0
