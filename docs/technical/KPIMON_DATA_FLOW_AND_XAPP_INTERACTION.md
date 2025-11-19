# KPIMON xApp 數據流與 xApp 互動完整解析

**文檔類型**: Technical Analysis
**日期**: 2025-11-19
**目標**: 完整解析 KPIMON xApp 如何獲取資料、顯示前端、以及與其他 xApp 互動

---

##   目錄

- [1. Executive Summary](#1-executive-summary)
- [2. KPIMON 獲取資料的方式](#2-kpimon-獲取資料的方式)
- [3. 前端顯示機制](#3-前端顯示機制)
- [4. 與其他 xApp 互動](#4-與其他-xapp-互動)
- [5. 完整互動流程圖](#5-完整互動流程圖)
- [6. 技術細節](#6-技術細節)

---

## 1. Executive Summary

### KPIMON xApp 核心角色

**KPIMON (KPI Monitor)** 在 O-RAN RIC Platform 中扮演 **KPI 收集與監控中心**：

```
┌─────────────────────────────────────────────────────────────┐
│                    KPIMON xApp 核心功能                     │
├─────────────────────────────────────────────────────────────┤
│ 1. 數據收集    從 E2 Simulator/gNodeB 接收 KPI 數據       │
│ 2. 數據儲存    儲存到 Redis + InfluxDB                     │
│ 3. 異常偵測    檢測信號品質異常（RSRP, SINR）              │
│ 4. Metrics 暴露 提供 Prometheus metrics                    │
│ 5. API 服務    提供 REST API 供前端查詢                    │
│ 6. xApp 互動   與其他 xApp 共享 KPI 數據                   │
└─────────────────────────────────────────────────────────────┘
```

### 三種通訊方式總覽

| 通訊方式 | 用途 | 協議 | 當前狀態 |
|---------|------|------|---------|
| **HTTP** | E2 Simulator → KPIMON（測試） | HTTP POST |  [DONE] 運行中 |
| **RMR** | E2Term → KPIMON（生產） | RMR (RIC Message Router) |  [WARN] 已部署，待啟用 |
| **SDL** | KPIMON ↔ 其他 xApps（數據共享） | Redis (Shared Data Layer) |  [DONE] 運行中 |

---

## 2. KPIMON 獲取資料的方式

### 2.1 方式一：HTTP (當前使用)  [DONE]

**架構**:
```
┌──────────────┐
│ E2 Simulator │  (Python, Flask)
└──────┬───────┘
       │ HTTP POST
       │ URL: http://kpimon.ricxapp.svc.cluster.local:8081/e2/indication
       │ Headers: Content-Type: application/json
       │ Body: {
       │   "cell_id": "cell_003",
       │   "ue_id": "ue_015",
       │   "beam_id": 5,
       │   "measurements": [
       │     {"name": "L1-RSRP.beam", "value": -78.5, "beam_id": 5},
       │     {"name": "L1-SINR.beam", "value": 22.3, "beam_id": 5}
       │   ]
       │ }
       ↓
┌──────────────────────────────────────┐
│ KPIMON Flask Server (port 8081)     │
│ @app.route('/e2/indication')        │
└──────────────────────────────────────┘
```

**程式碼實作** (`xapps/kpimon-go-xapp/src/kpimon.py:171-195`):

```python
@self.flask_app.route('/e2/indication', methods=['POST'])
def e2_indication():
    """Receive E2 indications from simulator (for testing)"""
    try:
        # Step 1: Prometheus 計數器
        MESSAGES_RECEIVED.inc()

        # Step 2: 解析 JSON 資料
        data = request.get_json()
        # data = {
        #   "beam_id": 5,
        #   "cell_id": "cell_003",
        #   "measurements": [...]
        # }

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Step 3: 處理 indication
        self._handle_indication(json.dumps(data))

        # Step 4: 更新計數器
        MESSAGES_PROCESSED.inc()

        return jsonify({
            "status": "success",
            "message": "Indication processed"
        }), 200

    except Exception as e:
        logger.error(f"Error processing E2 indication: {e}")
        return jsonify({"error": str(e)}), 500
```

**優點**:
-  [DONE] 簡單易用，適合開發測試
-  [DONE] 無需複雜配置
-  [DONE] 方便 debug（可直接用 curl 測試）

**缺點**:
-  [FAIL] 不符合 O-RAN 標準（標準是 E2AP + RMR）
-  [FAIL] 無法接入真實 gNodeB
-  [FAIL] 擴展性有限

**適用場景**:
- 開發測試環境
- Demo 展示
- 快速驗證功能

---

### 2.2 方式二：RMR (標準方式，已部署)  [WARN]

**架構**:
```
┌──────────────┐
│   gNodeB     │  (真實基站或 E2 Simulator)
└──────┬───────┘
       │ E2AP/SCTP
       │ Port: 36422
       ↓
┌──────────────────────────────────────┐
│ E2 Termination (E2Term)              │
│ - E2AP 協議解析                      │
│ - SCTP 連接管理                      │
└──────┬───────────────────────────────┘
       │ RMR (RIC Message Router)
       │ Message Type: 12050 (RIC_INDICATION)
       │ Routing: RTMgr 動態路由
       ↓
┌──────────────────────────────────────┐
│ KPIMON RMR Handler                   │
│ ricxappframe.xapp_frame.RMRXapp      │
└──────────────────────────────────────┘
```

**程式碼實作** (`xapps/kpimon-go-xapp/src/kpimon.py:251-281`):

```python
def _handle_message(self, rmr_xapp, summary, sbuf):
    """Handle incoming RMR messages"""
    MESSAGES_RECEIVED.inc()

    # 取得訊息類型
    msg_type = summary[rmr.RMR_MS_MSG_TYPE]
    logger.debug(f"Received message type: {msg_type}")

    # 提取 payload（bytes → string）
    payload_bytes = rmr.get_payload(sbuf)
    payload = payload_bytes.decode('utf-8') if payload_bytes else ""

    with PROCESSING_TIME.time():
        if msg_type == RIC_INDICATION:  # 12050
            # 處理 RIC Indication（KPI 資料）
            self._handle_indication(payload)

        elif msg_type == RIC_SUB_RESP:  # 12011
            # 處理訂閱回應
            self._handle_subscription_response(payload)

        elif msg_type == RIC_SUB_DEL_RESP:  # 12013
            # 處理訂閱刪除回應
            self._handle_subscription_delete_response(payload)

        else:
            logger.warning(f"Unknown message type: {msg_type}")

    MESSAGES_PROCESSED.inc()

    # 釋放 RMR buffer（重要！）
    rmr_xapp.rmr_free(sbuf)
```

**RMR Message Types (E2SM-KPM v3.0)**:

| Message Type | 名稱 | 方向 | 用途 |
|--------------|------|------|------|
| **12050** | RIC_INDICATION | E2Term → xApp | **KPI 數據傳輸** |
| 12010 | RIC_SUB_REQ | xApp → E2Term | 訂閱請求 |
| 12011 | RIC_SUB_RESP | E2Term → xApp | 訂閱回應 |
| 12012 | RIC_SUB_DEL_REQ | xApp → E2Term | 刪除訂閱 |
| 12013 | RIC_SUB_DEL_RESP | E2Term → E2Term | 刪除回應 |

**RTMgr 動態路由**:

```yaml
# RTMgr 路由表
messagetypes:
  - "RIC_INDICATION=12050"

PlatformRoutes:
  - messagetype: 12050
    senderendpoint: "service-ricplt-e2term-rmr-alpha.ricplt:38000"
    subscriptionid: -1
    endpoint:
      - "service-ricxapp-kpimon-rmr.ricxapp:4560"
      - "service-ricxapp-traffic-steering-rmr.ricxapp:4560"
```

**優點**:
-  [DONE] 符合 O-RAN 標準
-  [DONE] 可接入真實 gNodeB
-  [DONE] 高性能（> 1000 msg/s）
-  [DONE] 支援訂閱機制
-  [DONE] RTMgr 動態路由

**缺點**:
-  [WARN] 配置複雜（需要 RTMgr, E2Term）
-  [WARN] Debug 較困難

**當前狀態**:
-  [DONE] RMR 基礎設施已部署（E2Term, RTMgr）
-  [DONE] KPIMON 已支援 RMR handler
-  [WARN] E2 Simulator 尚未啟用 E2AP（仍使用 HTTP）

**啟用方式**:
```bash
# 啟用 KPIMON RMR
kubectl set env deployment/kpimon ENABLE_RMR=true -n ricxapp

# 啟用 E2 Simulator E2AP
kubectl set env deployment/e2-simulator ENABLE_RMR=true -n ricxapp
```

---

### 2.3 資料處理流程（共用邏輯）

**無論 HTTP 或 RMR，最終都會調用相同的處理邏輯**:

```python
def _handle_indication(self, payload):
    """Handle RIC Indication messages containing KPIs with beam_id support"""
    try:
        # Step 1: 解析 JSON
        indication = json.loads(payload)
        cell_id = indication.get('cell_id')
        ue_id = indication.get('ue_id')
        beam_id = indication.get('beam_id', 'n/a')
        measurements = indication.get('measurements', [])

        # Step 2: 處理每個 measurement
        for measurement in measurements:
            kpi_name = measurement.get('name')        # "L1-RSRP.beam"
            kpi_value = measurement.get('value')      # -78.5
            measurement_beam_id = measurement.get('beam_id', beam_id)

            # Step 3: 查找 KPI 定義
            if kpi_name in self.kpi_definitions:
                kpi_def = self.kpi_definitions[kpi_name]
                is_beam_specific = kpi_def.get('beam_specific', False)

                # Step 4: 組裝 KPI 資料
                kpi_data = {
                    'timestamp': timestamp,
                    'cell_id': cell_id,
                    'ue_id': ue_id,
                    'beam_id': measurement_beam_id,
                    'kpi_name': kpi_name,
                    'kpi_value': kpi_value,
                    'kpi_type': kpi_def['type'],
                    'unit': kpi_def['unit'],
                    'beam_specific': is_beam_specific
                }

                # Step 5: 儲存到 Redis（多層 key）
                if self.redis_client:
                    # Layer 1: KPI-centric
                    if is_beam_specific:
                        key = f"kpi:{cell_id}:{kpi_name}:beam_{measurement_beam_id}"
                    else:
                        key = f"kpi:{cell_id}:{kpi_name}"
                    self.redis_client.setex(key, 300, json.dumps(kpi_data))

                    # Layer 2: Beam-centric (Beam Query API)
                    beam_key = f"kpi:beam:{measurement_beam_id}:cell:{cell_id}:{kpi_name}"
                    self.redis_client.setex(beam_key, 300, json.dumps(kpi_data))

                    # Layer 3: UE-Beam association
                    if ue_id:
                        ue_beam_key = f"ue:beam:{measurement_beam_id}:cell:{cell_id}:{ue_id}"
                        self.redis_client.setex(ue_beam_key, 300, "1")

                    # Layer 4: Timeline (Sorted Set)
                    if is_beam_specific and measurement_beam_id != 'n/a':
                        beam_timeline_key = f"kpi:timeline:{cell_id}:beam_{measurement_beam_id}"
                        self.redis_client.zadd(beam_timeline_key, {timestamp: kpi_value})

                # Step 6: 更新 Prometheus Metrics
                KPI_VALUES.labels(
                    kpi_type=kpi_name,
                    cell_id=cell_id,
                    beam_id=str(measurement_beam_id)
                ).set(kpi_value)

                # Step 7: 儲存到 InfluxDB（可選）
                if self.influx_client:
                    self._write_to_influxdb(kpi_data)

        # Step 8: 異常偵測
        self._detect_anomalies(cell_id, measurements, beam_id)

    except Exception as e:
        logger.error(f"Error handling indication: {e}")
```

**資料儲存層次**:

```
┌─────────────────────────────────────────────────────────────┐
│ KPIMON 資料儲存架構（三層）                                 │
└─────────────────────────────────────────────────────────────┘

1. Redis (即時查詢，TTL 300s)
   ├─ kpi:beam:5:cell:cell_003:L1-RSRP.beam  ← Beam Query API
   ├─ kpi:cell_003:L1-RSRP.beam:beam_5
   ├─ ue:beam:5:cell:cell_003:ue_015
   └─ kpi:timeline:cell_003:beam_5

2. Prometheus (監控告警，保留 15 天)
   └─ kpimon_kpi_value{kpi_type="L1-RSRP.beam",cell_id="cell_003",beam_id="5"}

3. InfluxDB (長期儲存，可選)
   └─ bucket: kpimon
      measurement: kpi_metrics
      tags: cell_id, beam_id, kpi_type
      field: kpi_value
```

---

## 3. 前端顯示機制

### 3.1 前端架構

```
┌─────────────────────────────────────────────────────────────┐
│                     前端三層架構                             │
└─────────────────────────────────────────────────────────────┘

【用戶層】
    ↓
┌──────────────────┬──────────────────┬──────────────────┐
│  Web UI          │  CLI Tool        │  Grafana         │
│  (Browser)       │  (Bash)          │  (Dashboard)     │
│  localhost:8888  │  query-beam.sh   │  localhost:3000  │
└────────┬─────────┴────────┬─────────┴────────┬─────────┘
         │                  │                  │
         ↓                  ↓                  ↓
【Proxy/API 層】
    ↓                  ↓                  ↓
┌──────────────────┬──────────────────┬──────────────────┐
│ proxy-server.py  │ KPIMON API       │ Prometheus       │
│ (CORS proxy)     │ (Flask)          │ (Metrics)        │
│ port 8888        │ port 8081        │ port 9090        │
└────────┬─────────┴────────┬─────────┴────────┬─────────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
                            ↓
【數據層】
                   ┌────────────────┐
                   │ Redis / InfluxDB│
                   └────────────────┘
```

### 3.2 方式一：Web UI (Material Design)

**位置**: `frontend-beam-query/`

#### 架構流程

```
┌──────────────┐
│   Browser    │  用戶訪問 http://localhost:8888/
└──────┬───────┘
       │ HTTP GET /
       ↓
┌──────────────────────────────────────┐
│ proxy-server.py (SimpleHTTPServer)   │
│ - 提供靜態檔案（index.html, app.js）│
└──────────────────────────────────────┘
       │
       ↓ User clicks "Query Beam 5"
       │
┌──────────────┐
│   Browser    │  fetch('/api/beam/5/kpi')
└──────┬───────┘
       │ HTTP GET /api/beam/5/kpi
       ↓
┌──────────────────────────────────────┐
│ proxy-server.py (Proxy Handler)      │
│ - Proxy to http://localhost:8081    │
└──────┬───────────────────────────────┘
       │ HTTP GET http://localhost:8081/api/beam/5/kpi
       ↓
┌──────────────────────────────────────┐
│ KPIMON Flask API (port 8081)         │
│ @beam_api.route('/api/beam/<id>/kpi')│
└──────┬───────────────────────────────┘
       │ Redis KEYS "kpi:beam:5:cell:*"
       ↓
┌──────────────────────────────────────┐
│ Redis                                │
│ - kpi:beam:5:cell:cell_001:L1-RSRP  │
│ - kpi:beam:5:cell:cell_002:L1-RSRP  │
│ - kpi:beam:5:cell:cell_003:L1-RSRP  │
└──────┬───────────────────────────────┘
       │ GET all keys
       ↓
┌──────────────────────────────────────┐
│ KPIMON API (聚合計算)                │
│ - rsrp_avg = -79.47                  │
│ - sinr_avg = 21.57                   │
└──────┬───────────────────────────────┘
       │ JSON response
       ↓
┌──────────────┐
│   Browser    │  Display in Material Design UI
└──────────────┘
```

#### CORS 問題解決方案

**問題**:
```
Browser (localhost:8888) → KPIMON API (localhost:8081)
 [FAIL] CORS Error: No 'Access-Control-Allow-Origin' header
```

**解決方案**: **Proxy Server**

```python
# frontend-beam-query/proxy-server.py
class BeamProxyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)

        if parsed_path.path.startswith('/api/'):
            # Proxy 到 KPIMON API
            target_url = f"http://localhost:8081{self.path}"

            try:
                response = urllib.request.urlopen(target_url)
                content = response.read()

                # 返回給前端
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content)

            except Exception as e:
                self.send_error(500, f"Proxy error: {str(e)}")
        else:
            # 提供靜態檔案
            super().do_GET()
```

**App.js 配置**:
```javascript
// Before: CORS error
const API_BASE_URL = 'http://localhost:8081';

// After: Same origin (no CORS)
const API_BASE_URL = '';  // Empty string = same origin
```

**UI 元素**:

```html
<!-- Quick Stats Cards (Material Design) -->
<div class="stats-container">
  <div class="stat-card">
    <div class="stat-icon">📡</div>
    <div class="stat-value" id="avgRsrp">-79.47 dBm</div>
    <div class="stat-label">Average RSRP</div>
    <span class="quality-badge good">Good</span>
  </div>

  <div class="stat-card">
    <div class="stat-icon"> </div>
    <div class="stat-value" id="avgSinr">21.57 dB</div>
    <div class="stat-label">Average SINR</div>
    <span class="quality-badge excellent">Excellent</span>
  </div>

  <div class="stat-card">
    <div class="stat-icon">⚡</div>
    <div class="stat-value" id="avgThroughput">55.3 Mbps</div>
    <div class="stat-label">Average Throughput</div>
    <span class="quality-badge good">Good</span>
  </div>
</div>

<!-- Detailed Table -->
<table class="kpi-table">
  <thead>
    <tr>
      <th>Cell ID</th>
      <th>L1-RSRP (dBm)</th>
      <th>L1-SINR (dB)</th>
      <th>Throughput (Mbps)</th>
      <th>Quality</th>
    </tr>
  </thead>
  <tbody id="kpiTableBody">
    <!-- 動態填充 -->
  </tbody>
</table>
```

---

### 3.3 方式二：CLI Tool

**位置**: `scripts/query-beam.sh`

```bash
#!/bin/bash

BEAM_ID=${1:-1}
KPI_TYPE=${2:-all}
API_URL="http://localhost:8081"
QUERY_URL="${API_URL}/api/beam/${BEAM_ID}/kpi?kpi_type=${KPI_TYPE}"

echo "  Querying Beam ${BEAM_ID} KPIs (type: ${KPI_TYPE})..."
curl -s "${QUERY_URL}" | jq '.'
```

**使用範例**:
```bash
# 查詢 Beam 5 所有 KPI
./scripts/query-beam.sh 5

# 查詢 Beam 5 信號品質
./scripts/query-beam.sh 5 signal_quality
```

**輸出範例**:
```json
{
  "status": "success",
  "beam_id": 5,
  "timestamp": "2025-11-19T11:15:30",
  "data": {
    "signal_quality": {
      "rsrp_avg": -79.47,
      "rsrp_min": -80.1,
      "rsrp_max": -78.5,
      "sinr_avg": 21.57,
      "sinr_min": 20.9,
      "sinr_max": 22.3
    },
    "cells": [
      {"cell_id": "cell_001", "l1_rsrp": -78.5, "l1_sinr": 22.3},
      {"cell_id": "cell_002", "l1_rsrp": -80.1, "l1_sinr": 21.5},
      {"cell_id": "cell_003", "l1_rsrp": -79.8, "l1_sinr": 20.9}
    ]
  }
}
```

---

### 3.4 方式三：Grafana Dashboard

**數據來源**: Prometheus

```
Grafana (port 3000)
    ↓ PromQL Query
Prometheus (port 9090)
    ↓ Scrape Metrics (每 15 秒)
KPIMON Prometheus Exporter (port 8080)
    ↓ /metrics endpoint
kpimon_kpi_value{kpi_type="L1-RSRP.beam",cell_id="cell_003",beam_id="5"}
```

**PromQL 查詢範例**:

```promql
# Beam 5 平均 L1-RSRP
avg(kpimon_kpi_value{kpi_type="L1-RSRP.beam",beam_id="5"})

# Beam 5 過去 1 小時平均 SINR
avg_over_time(kpimon_kpi_value{kpi_type="L1-SINR.beam",beam_id="5"}[1h])

# Beam 5 vs Beam 0 RSRP 比較
avg(kpimon_kpi_value{kpi_type="L1-RSRP.beam",beam_id="5"}) -
avg(kpimon_kpi_value{kpi_type="L1-RSRP.beam",beam_id="0"})

# 所有 Beam 的 RSRP 分布
sum by (beam_id) (kpimon_kpi_value{kpi_type="L1-RSRP.beam"})
```

**Grafana Panel 配置**:
```json
{
  "title": "Beam 5 Signal Quality",
  "targets": [
    {
      "expr": "avg(kpimon_kpi_value{kpi_type=\"L1-RSRP.beam\",beam_id=\"5\"})",
      "legendFormat": "L1-RSRP (Avg)"
    },
    {
      "expr": "avg(kpimon_kpi_value{kpi_type=\"L1-SINR.beam\",beam_id=\"5\"})",
      "legendFormat": "L1-SINR (Avg)"
    }
  ],
  "yAxisLabel": "Signal Strength (dBm / dB)"
}
```

---

## 4. 與其他 xApp 互動

### 4.1 互動方式總覽

KPIMON 與其他 xApp 的互動主要透過 **Shared Data Layer (SDL)**：

```
┌─────────────────────────────────────────────────────────────┐
│              xApp 互動架構 (SDL-Based)                       │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐          ┌──────────────┐          ┌──────────────┐
│   KPIMON     │          │   Traffic    │          │     QoE      │
│   xApp       │          │   Steering   │          │  Predictor   │
└──────┬───────┘          └──────┬───────┘          └──────┬───────┘
       │ Write KPI               │ Read KPI                │ Read KPI
       │                         │                         │
       ↓                         ↓                         ↓
┌─────────────────────────────────────────────────────────────┐
│          Shared Data Layer (SDL) - Redis                    │
│                                                             │
│  kpi:cell_003:L1-RSRP.beam:beam_5 = {...}                 │
│  kpi:beam:5:cell:cell_003:L1-RSRP.beam = {...}            │
│  ue:beam:5:cell:cell_003:ue_015 = "1"                     │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 實際互動範例

#### 範例 1: Traffic Steering 讀取 KPIMON KPI

**場景**: Traffic Steering 需要根據 Beam 信號品質決定切換

```python
# Traffic Steering xApp
from ricxappframe.xapp_sdl import SDLWrapper

# 初始化 SDL
sdl = SDLWrapper(use_fake_sdl=False)

def make_handover_decision(ue_id, current_cell, current_beam):
    """根據 KPIMON KPI 決定是否切換"""

    # 讀取當前 Beam 的 L1-RSRP
    key = f"kpi:beam:{current_beam}:cell:{current_cell}:L1-RSRP.beam"
    kpi_data_str = sdl.get(ns="kpimon", key=key)

    if kpi_data_str:
        kpi_data = json.loads(kpi_data_str)
        current_rsrp = kpi_data['kpi_value']  # -78.5 dBm

        # 如果信號太差（< -90 dBm），觸發切換
        if current_rsrp < -90:
            # 查找更好的 Beam
            better_beam = find_better_beam(current_cell)

            if better_beam:
                logger.info(f"Handover decision: UE {ue_id} from Beam {current_beam} to Beam {better_beam}")
                return {
                    "action": "handover",
                    "target_beam": better_beam,
                    "reason": f"Poor RSRP: {current_rsrp} dBm"
                }

    return {"action": "stay"}

def find_better_beam(cell_id):
    """找到信號最好的 Beam"""
    best_beam = None
    best_rsrp = -120.0  # 最差值

    for beam_id in range(8):  # Beam 0-7
        key = f"kpi:beam:{beam_id}:cell:{cell_id}:L1-RSRP.beam"
        kpi_data_str = sdl.get(ns="kpimon", key=key)

        if kpi_data_str:
            kpi_data = json.loads(kpi_data_str)
            rsrp = kpi_data['kpi_value']

            if rsrp > best_rsrp:
                best_rsrp = rsrp
                best_beam = beam_id

    return best_beam
```

**數據流**:
```
KPIMON → Redis (寫入 KPI)
          ↓
Traffic Steering ← Redis (讀取 KPI)
          ↓
Traffic Steering → E2Term (發送切換命令)
```

---

#### 範例 2: QoE Predictor 讀取 KPIMON KPI

**場景**: QoE Predictor 預測用戶體驗品質

```python
# QoE Predictor xApp
import numpy as np
from ricxappframe.xapp_sdl import SDLWrapper

sdl = SDLWrapper(use_fake_sdl=False)

def predict_qoe(ue_id, cell_id, beam_id):
    """根據 KPIMON KPI 預測 QoE"""

    # 讀取 L1-RSRP
    rsrp_key = f"kpi:beam:{beam_id}:cell:{cell_id}:L1-RSRP.beam"
    rsrp_data_str = sdl.get(ns="kpimon", key=rsrp_key)

    # 讀取 L1-SINR
    sinr_key = f"kpi:beam:{beam_id}:cell:{cell_id}:L1-SINR.beam"
    sinr_data_str = sdl.get(ns="kpimon", key=sinr_key)

    if rsrp_data_str and sinr_data_str:
        rsrp = json.loads(rsrp_data_str)['kpi_value']  # -78.5 dBm
        sinr = json.loads(sinr_data_str)['kpi_value']  # 22.3 dB

        # 簡單的 QoE 預測模型
        qoe_score = calculate_qoe_score(rsrp, sinr)

        return {
            "ue_id": ue_id,
            "beam_id": beam_id,
            "qoe_score": qoe_score,
            "quality_level": get_quality_level(qoe_score)
        }

    return None

def calculate_qoe_score(rsrp, sinr):
    """QoE 評分演算法（簡化版）"""
    # RSRP 分數 (0-50)
    rsrp_score = max(0, min(50, (rsrp + 120) / 40 * 50))

    # SINR 分數 (0-50)
    sinr_score = max(0, min(50, sinr / 30 * 50))

    # 總分
    qoe_score = rsrp_score + sinr_score

    return qoe_score

def get_quality_level(score):
    """品質等級判定"""
    if score >= 80:
        return "Excellent"
    elif score >= 60:
        return "Good"
    elif score >= 40:
        return "Fair"
    else:
        return "Poor"
```

---

#### 範例 3: RAN Control 讀取 KPIMON KPI

**場景**: RAN Control 根據負載調整功率

```python
# RAN Control xApp
def adjust_beam_power(cell_id):
    """根據所有 Beam 的 KPI 調整功率"""

    beam_stats = {}

    for beam_id in range(8):
        # 讀取每個 Beam 的 L1-RSRP
        key = f"kpi:beam:{beam_id}:cell:{cell_id}:L1-RSRP.beam"
        kpi_data_str = sdl.get(ns="kpimon", key=key)

        if kpi_data_str:
            kpi_data = json.loads(kpi_data_str)
            beam_stats[beam_id] = kpi_data['kpi_value']

    # 找出信號最弱的 Beam
    weakest_beam = min(beam_stats, key=beam_stats.get)
    weakest_rsrp = beam_stats[weakest_beam]

    # 如果最弱的 Beam < -100 dBm，增加功率
    if weakest_rsrp < -100:
        logger.info(f"Increasing power for Beam {weakest_beam} (RSRP: {weakest_rsrp} dBm)")
        send_power_control_command(cell_id, weakest_beam, power_increase=3)  # +3 dB
```

---

### 4.3 SDL (Shared Data Layer) 詳細架構

**SDL 技術棧**:
```
┌─────────────────────────────────────────────────────────────┐
│                 SDL Architecture                            │
└─────────────────────────────────────────────────────────────┘

【xApp 層】
    ↓ ricxappframe.xapp_sdl.SDLWrapper
【DBaaS 層】
    ↓ DBaaS Service (port 6379)
【Redis Cluster 層】
    ├─ redis-cluster-0 (Master)
    ├─ redis-cluster-1 (Replica)
    └─ redis-cluster-2 (Replica)
```

**SDL API 使用**:

```python
from ricxappframe.xapp_sdl import SDLWrapper

# 初始化
sdl = SDLWrapper(use_fake_sdl=False)

# 寫入資料
sdl.set(
    ns="kpimon",
    key="kpi:beam:5:cell:cell_003:L1-RSRP.beam",
    value=json.dumps({"kpi_value": -78.5, "timestamp": "2025-11-19T11:15:30"})
)

# 讀取資料
data_str = sdl.get(ns="kpimon", key="kpi:beam:5:cell:cell_003:L1-RSRP.beam")
data = json.loads(data_str)

# 批量讀取
keys = sdl.find_keys(ns="kpimon", prefix="kpi:beam:5:cell:*")
# keys = [
#   "kpi:beam:5:cell:cell_001:L1-RSRP.beam",
#   "kpi:beam:5:cell:cell_002:L1-RSRP.beam",
#   "kpi:beam:5:cell:cell_003:L1-RSRP.beam"
# ]

# 刪除資料
sdl.remove(ns="kpimon", key="kpi:beam:5:cell:cell_003:L1-RSRP.beam")
```

**Namespace 規範**:

| xApp | Namespace | Key Pattern |
|------|-----------|-------------|
| **KPIMON** | `kpimon` | `kpi:beam:{id}:cell:{cell}:{kpi_name}` |
| **Traffic Steering** | `traffic-steering` | `handover:{ue_id}:target_beam` |
| **QoE Predictor** | `qoe-predictor` | `qoe:{ue_id}:score` |
| **RAN Control** | `ran-control` | `control:{cell_id}:beam_{id}:power` |

---

### 4.4 RMR-based 互動（未來）

**當前狀態**: RMR 基礎設施已部署，但 xApp 間互動仍使用 SDL

**未來架構** (完全 RMR):

```
┌──────────────┐                    ┌──────────────┐
│   KPIMON     │                    │   Traffic    │
│   xApp       │                    │   Steering   │
└──────┬───────┘                    └──────┬───────┘
       │ RMR Send                          │ RMR Send
       │ msg_type=30000 (TS_UE_LIST)      │ msg_type=40000 (TS_DECISION)
       ↓                                   ↓
┌─────────────────────────────────────────────────────────────┐
│                 RTMgr (Routing Manager)                     │
│  - 動態路由管理                                             │
│  - Message type 映射                                        │
└──────┬──────────────────────────────────────────┬──────────┘
       │                                           │
       ↓                                           ↓
┌──────────────┐                    ┌──────────────┐
│   Traffic    │                    │   KPIMON     │
│   Steering   │                    │   xApp       │
└──────────────┘                    └──────────────┘
```

**RMR Send 範例** (Traffic Steering → KPIMON):

```python
# Traffic Steering xApp
from ricxappframe.xapp_frame import RMRXapp

xapp = RMRXapp(...)

# 發送 UE 列表給 KPIMON
ue_list = {"ue_ids": ["ue_001", "ue_015", "ue_020"]}
payload = json.dumps(ue_list).encode('utf-8')

sbuf = xapp.rmr_alloc_msg(
    payload=payload,
    mtype=30000,  # TS_UE_LIST
    state=0
)

xapp.rmr_send(sbuf, mtype=30000)
xapp.rmr_free(sbuf)
```

---

## 5. 完整互動流程圖

### 5.1 端到端資料流（當前架構）

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: KPI 生成與傳輸                                      │
└─────────────────────────────────────────────────────────────┘

  ┌──────────────┐
  │ E2 Simulator │  每 5 秒生成 KPI
  └──────┬───────┘
         │ HTTP POST /e2/indication
         │ {"beam_id": 5, "measurements": [...]}
         ↓
  ┌──────────────────────────────────────┐
  │ KPIMON Flask Server (port 8081)      │
  │ @app.route('/e2/indication')         │
  └──────┬───────────────────────────────┘
         │ _handle_indication()
         ↓

┌─────────────────────────────────────────────────────────────┐
│ Phase 2: 資料處理與儲存                                      │
└─────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────┐
  │ KPIMON Processing                    │
  │ - Extract beam_id: 5                 │
  │ - Parse measurements                 │
  │ - Validate KPI definitions           │
  └──────┬───────────────────────────────┘
         │
         ├─────────────────┬─────────────────┬────────────────┐
         ↓                 ↓                 ↓                ↓
  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
  │   Redis     │  │ Prometheus  │  │  InfluxDB   │  │  Anomaly    │
  │  (4 layers) │  │  (Metrics)  │  │ (Optional)  │  │  Detection  │
  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Phase 3: xApp 互動（SDL-based）                              │
└─────────────────────────────────────────────────────────────┘

  ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
  │   Traffic    │          │     QoE      │          │     RAN      │
  │   Steering   │          │  Predictor   │          │   Control    │
  └──────┬───────┘          └──────┬───────┘          └──────┬───────┘
         │ SDL Read                │ SDL Read                │ SDL Read
         │                         │                         │
         ↓                         ↓                         ↓
  ┌─────────────────────────────────────────────────────────────┐
  │           Redis (Shared Data Layer)                         │
  │  kpi:beam:5:cell:cell_003:L1-RSRP.beam                     │
  └─────────────────────────────────────────────────────────────┘
         │
         ↓ 讀取 KPI 後執行決策
         │
  ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
  │ Handover     │          │   QoE        │          │   Power      │
  │ Decision     │          │   Prediction │          │   Control    │
  └──────────────┘          └──────────────┘          └──────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Phase 4: 前端顯示                                            │
└─────────────────────────────────────────────────────────────┘

  ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
  │   Web UI     │          │   CLI Tool   │          │   Grafana    │
  │ (Browser)    │          │  (Bash)      │          │ (Dashboard)  │
  └──────┬───────┘          └──────┬───────┘          └──────┬───────┘
         │ fetch()                 │ curl                     │ PromQL
         ↓                         ↓                         ↓
  ┌──────────────┐          ┌──────────────────────────────────────┐
  │proxy-server.py│         │ KPIMON API (port 8081)               │
  └──────┬───────┘          └──────┬───────────────────────────────┘
         │                         │
         └─────────────────────────┘
                    ↓
         ┌──────────────────────┐
         │ Redis / Prometheus   │
         └──────────────────────┘
```

---

## 6. 技術細節

### 6.1 當前通訊方式總結

| 通訊對象 | 方式 | 協議 | Port | 狀態 |
|---------|------|------|------|------|
| **E2 Sim → KPIMON** | HTTP | HTTP POST | 8081 |  [DONE] 運行中 |
| **KPIMON → Redis** | TCP | Redis Protocol | 6379 |  [DONE] 運行中 |
| **KPIMON → Prometheus** | HTTP | Pull (Scrape) | 8080 |  [DONE] 運行中 |
| **KPIMON → InfluxDB** | HTTP | InfluxDB Line Protocol | 8086 |  [WARN] 可選 |
| **Web UI → KPIMON** | HTTP (via Proxy) | HTTP GET | 8888→8081 |  [DONE] 運行中 |
| **CLI → KPIMON** | HTTP | HTTP GET | 8081 |  [DONE] 運行中 |
| **Grafana → Prometheus** | HTTP | PromQL | 9090 |  [DONE] 運行中 |
| **Traffic Steering → KPIMON** | SDL | Redis Protocol | 6379 |  [DONE] 運行中 |
| **QoE Predictor → KPIMON** | SDL | Redis Protocol | 6379 |  [DONE] 運行中 |

### 6.2 未來遷移計畫（RMR）

| 通訊對象 | 當前 | 未來 | 遷移複雜度 |
|---------|------|------|-----------|
| **E2 Sim → KPIMON** | HTTP | E2AP + RMR |  |
| **KPIMON → Redis** | Direct | Via SDL (DBaaS) |  |
| **xApp ↔ xApp** | SDL | RMR |  |

### 6.3 性能指標

| 指標 | 當前值 | 目標值 | 測量方式 |
|------|--------|--------|---------|
| **E2 Indication 處理延遲** | ~50ms | < 100ms | `kpimon_processing_time_seconds` |
| **Redis 查詢延遲** | ~5ms | < 10ms | Redis SLOWLOG |
| **Prometheus Scrape 間隔** | 15s | 15s | Prometheus config |
| **Web UI 查詢回應時間** | ~100ms | < 200ms | Browser DevTools |
| **KPIMON 訊息處理率** | ~12 msg/min | > 1000 msg/s (RMR) | `kpimon_messages_processed_total` |

---

## 7. 總結

### 核心通訊方式

```
┌─────────────────────────────────────────────────────────────┐
│ KPIMON xApp 三種主要通訊方式                                 │
└─────────────────────────────────────────────────────────────┘

1. 數據接收（Input）
   HTTP (當前)    E2 Simulator → KPIMON Flask API (port 8081)
   RMR (未來)     E2Term → KPIMON RMR Handler (port 4560)

2. 數據儲存（Storage）
   Redis          KPIMON → Redis Cluster (4 層 key 結構)
   Prometheus     KPIMON → Prometheus (Metrics export)
   InfluxDB       KPIMON → InfluxDB (可選，長期儲存)

3. 數據查詢（Output）
   Web UI         Browser → proxy-server.py → KPIMON API
   CLI            Bash → curl → KPIMON API
   Grafana        Grafana → PromQL → Prometheus

4. xApp 互動（Inter-xApp）
   SDL (當前)     xApps ↔ Redis (via ricxappframe.xapp_sdl)
   RMR (未來)     xApps ↔ RTMgr → RMR routing
```

### 關鍵設計

-  [DONE] **雙接口支援**: HTTP (測試) + RMR (生產)
-  [DONE] **多層儲存**: Redis (即時) + Prometheus (監控) + InfluxDB (長期)
-  [DONE] **SDL 互動**: 透過 Redis 與其他 xApp 共享 KPI
-  [DONE] **CORS 解決**: proxy-server.py 解決前端跨域問題
-  [DONE] **向後相容**: beam_id 預設值 'n/a'

---

**文檔完成！**  

**下一步**:
- 啟用 RMR 模式: `kubectl set env deployment/kpimon ENABLE_RMR=true`
- 查看實際 RMR 訊息流: `kubectl logs -n ricxapp kpimon -f | grep RMR`

---

**最後更新**: 2025-11-19
**版本**: 1.0.0
