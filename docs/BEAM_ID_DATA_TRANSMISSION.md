# Beam ID 資料傳輸完整流程分析

**文檔類型**: Technical Deep Dive
**作者**: 蔡秀吉 (thc1006)
**日期**: 2025-11-19
**目標**: 完整解析 beam_id 從生成到查詢的完整數據流

---

##   目錄

- [1. Executive Summary](#1-executive-summary)
- [2. Beam ID 生成階段](#2-beam-id-生成階段)
- [3. HTTP 傳輸階段](#3-http-傳輸階段)
- [4. KPIMON 接收與處理](#4-kpimon-接收與處理)
- [5. Redis 多層儲存策略](#5-redis-多層儲存策略)
- [6. 查詢階段](#6-查詢階段)
- [7. 完整資料流程圖](#7-完整資料流程圖)
- [8. 技術細節與設計決策](#8-技術細節與設計決策)

---

## 1. Executive Summary

### Beam ID 是什麼？

**Beam ID (SSB Index)** 在 5G NR 系統中代表**波束索引**：

- **範圍**: 0-7（8 個波束方向）
- **用途**: 5G 波束成形（Beamforming）中的不同覆蓋方向
- **重要性**: 每個 beam 有獨立的信號品質（L1-RSRP, L1-SINR）

### 資料傳輸概覽

```
┌──────────────┐
│ E2 Simulator │  生成 beam_id (0-7)
└──────┬───────┘
       │ HTTP POST /e2/indication
       │ JSON: {"beam_id": 5, "measurements": [...]}
       ↓
┌──────────────┐
│   KPIMON     │  接收並解析 beam_id
└──────┬───────┘
       │ 多層 Redis 儲存
       ↓
┌──────────────────────────────────────┐
│           Redis 儲存結構             │
│ 1. kpi:beam:{beam_id}:cell:{cell_id}│
│ 2. kpi:timeline:{cell_id}:beam_{id} │
│ 3. ue:beam:{beam_id}:cell:{cell_id} │
└──────┬───────────────────────────────┘
       │ 查詢
       ↓
┌──────────────────────────────────────┐
│     三種查詢方式                     │
│ 1. CLI:     ./scripts/query-beam.sh │
│ 2. Web UI:  http://localhost:8888/  │
│ 3. REST API: GET /api/beam/{id}/kpi │
└──────────────────────────────────────┘
```

**核心特色**:
-  [DONE] **動態配置**: 可透過環境變數 `BEAM_IDS` 控制生成哪些 beam
-  [DONE] **多層儲存**: Redis 中有 4 種不同的 key 結構儲存 beam 資料
-  [DONE] **向後相容**: 支援舊版沒有 beam_id 的資料格式
-  [DONE] **Beam-specific KPIs**: L1-RSRP 和 L1-SINR 按 beam 分別記錄

---

## 2. Beam ID 生成階段

### 2.1 E2 Simulator 配置

**位置**: `simulator/e2-simulator/src/e2_simulator.py`

#### 配置載入優先順序

```python
# Line 76-148: _load_beam_config()

優先順序（由高到低）:
1. 環境變數 BEAM_IDS       (最高優先)
2. config/simulator.yaml
3. 預設值: all beams (0-7)
```

#### 環境變數範例

```bash
# 方式 1: 只生成 Beam 1 和 Beam 2
export BEAM_IDS="1,2"
kubectl set env deployment/e2-simulator BEAM_IDS="1,2" -n ricxapp

# 方式 2: 只生成 Beam 5
export BEAM_IDS="5"

# 方式 3: 生成所有 Beam (0-7)
export BEAM_IDS="all"

# 當前運行狀態（從 kubectl logs 可見）:
# Active Beam IDs: [0, 1, 2, 3, 4, 5, 6, 7]
```

#### 配置驗證

```python
# Line 106-110: 驗證 beam_id 範圍必須是 0-7
invalid_beams = [b for b in beam_ids if b < 0 or b > 7]
if invalid_beams:
    logger.warning(f"Invalid beam IDs: {invalid_beams} (must be 0-7)")
    return list(range(8))  # Fallback to all beams
```

### 2.2 KPI Indication 生成

**位置**: `simulator/e2-simulator/src/e2_simulator.py:150-239`

#### Step 1: 選擇 Beam ID

```python
# Line 157: 從 active_beam_ids 中隨機選擇一個
beam_id = random.choice(self.active_beam_ids)

# 範例:
# active_beam_ids = [1, 2, 5]  → 只會生成 Beam 1, 2, 5 的資料
# active_beam_ids = [0..7]     → 生成所有 Beam 的資料
```

#### Step 2: 生成基本 KPI 測量值

```python
# Line 160-201: 生成 10 種基本 KPI
measurements = [
    {
        'name': 'DRB.PacketLossDl',
        'value': random.uniform(0.1, 5.0)  # 0.1% - 5%
    },
    {
        'name': 'DRB.UEThpDl',
        'value': random.uniform(10.0, 100.0)  # 10-100 Mbps
    },
    # ... 其他 KPIs
]
```

#### Step 3: 生成 Beam-Specific KPIs

```python
# Line 203-229: 生成波束專屬測量值
# L1-RSRP (Layer 1 Reference Signal Received Power)
# L1-SINR (Layer 1 Signal-to-Interference-plus-Noise Ratio)

# Beam Quality Factor (beam 0 通常最好)
beam_quality_factor = 1.0 - (beam_id * 0.05)

# Beam 0: quality = 1.0    (最佳)
# Beam 1: quality = 0.95
# Beam 2: quality = 0.90
# ...
# Beam 7: quality = 0.65   (最差)

# 生成 L1-RSRP (較好的範圍 -100 to -70 dBm)
l1_rsrp = random.uniform(-100.0, -70.0) * beam_quality_factor

# 生成 L1-SINR (較好的範圍 8 to 30 dB)
l1_sinr = random.uniform(8.0, 30.0) * beam_quality_factor

measurements.extend([
    {
        'name': 'L1-RSRP.beam',
        'value': l1_rsrp,
        'beam_id': beam_id  # ← 重要！測量值帶有 beam_id
    },
    {
        'name': 'L1-SINR.beam',
        'value': l1_sinr,
        'beam_id': beam_id
    }
])
```

#### Step 4: 組裝完整 Indication

```python
# Line 231-239: 組裝 JSON 資料
return {
    'timestamp': datetime.now().isoformat(),  # "2025-11-19T10:30:45.123456"
    'cell_id': cell_id,                       # "cell_001"
    'ue_id': ue_id,                           # "ue_005"
    'beam_id': beam_id,                       # ← 重要！頂層 beam_id
    'measurements': measurements,              # ← 包含 L1-RSRP.beam, L1-SINR.beam
    'indication_sn': int(time.time() * 1000), # 序號
    'indication_type': 'report'
}
```

**關鍵設計**:
-  [DONE] **雙層 beam_id**: 頂層有 `beam_id: 5`，measurement 內 L1-RSRP/L1-SINR 也有 `beam_id: 5`
-  [DONE] **Beam Quality Degradation**: 越大的 beam_id，信號品質越差（模擬真實場景）
-  [DONE] **向後相容**: 即使不設定 `BEAM_IDS`，系統仍會自動生成所有 beam

### 2.3 日誌輸出範例

```log
INFO - Generated KPI indication for cell_003/ue_015 on beam 5
```

**實際生成的 JSON 資料**:
```json
{
  "timestamp": "2025-11-19T10:30:45.123456",
  "cell_id": "cell_003",
  "ue_id": "ue_015",
  "beam_id": 5,
  "measurements": [
    {"name": "DRB.UEThpDl", "value": 55.3},
    {"name": "UE.RSRP", "value": -95.2},
    {"name": "UE.SINR", "value": 18.5},
    {
      "name": "L1-RSRP.beam",
      "value": -78.5,
      "beam_id": 5
    },
    {
      "name": "L1-SINR.beam",
      "value": 22.3,
      "beam_id": 5
    }
  ],
  "indication_sn": 1732001445123,
  "indication_type": "report"
}
```

---

## 3. HTTP 傳輸階段

### 3.1 發送方 (E2 Simulator)

**位置**: `simulator/e2-simulator/src/e2_simulator.py:300-330`

```python
def send_to_xapp(self, xapp_name: str, data: Dict) -> bool:
    """Send indication to xApp via HTTP"""
    try:
        # KPIMON 配置
        xapp_config = {
            'host': 'kpimon.ricxapp.svc.cluster.local',
            'port': 8081,
            'endpoint': '/e2/indication'
        }

        # 組裝 URL
        url = f"http://{xapp_config['host']}:{xapp_config['port']}{xapp_config['endpoint']}"
        # 結果: http://kpimon.ricxapp.svc.cluster.local:8081/e2/indication

        # 發送 HTTP POST
        response = requests.post(
            url,
            json=data,  # ← 自動序列化為 JSON，包含 beam_id
            timeout=5,
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code == 200:
            logger.debug(f"Successfully sent data to {xapp_name}")
            return True
        else:
            logger.warning(f"Failed to send to {xapp_name}: HTTP {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        logger.debug(f"Connection error for {xapp_name}")
        return False
```

### 3.2 傳輸過程

```
E2 Simulator Pod (ricxapp namespace)
    │
    │ HTTP POST
    │ URL: http://kpimon.ricxapp.svc.cluster.local:8081/e2/indication
    │ Headers: Content-Type: application/json
    │ Body: {"beam_id": 5, "cell_id": "cell_003", ...}
    │
    ↓
Kubernetes Service (kpimon.ricxapp.svc.cluster.local)
    │
    │ Port Forwarding: 8081 → 8081
    │
    ↓
KPIMON Pod (ricxapp namespace)
    │
    │ Flask Server listening on 0.0.0.0:8081
    │
    ↓
Flask Route: @app.route('/e2/indication', methods=['POST'])
```

### 3.3 網路層細節

**Kubernetes Service Discovery**:
```yaml
# KPIMON Service
apiVersion: v1
kind: Service
metadata:
  name: kpimon
  namespace: ricxapp
spec:
  selector:
    app: kpimon
  ports:
  - name: api
    port: 8081
    targetPort: 8081
    protocol: TCP
```

**DNS Resolution**:
```
kpimon.ricxapp.svc.cluster.local
  │
  ├─ kpimon: Service 名稱
  ├─ ricxapp: Namespace
  ├─ svc: Service 類型
  └─ cluster.local: Cluster domain
```

---

## 4. KPIMON 接收與處理

### 4.1 Flask Route 接收

**位置**: `xapps/kpimon-go-xapp/src/kpimon.py:171-195`

```python
@self.flask_app.route('/e2/indication', methods=['POST'])
def e2_indication():
    """Receive E2 indications from simulator (for testing)"""
    try:
        # Step 1: 增加接收計數器
        MESSAGES_RECEIVED.inc()

        # Step 2: 解析 JSON 資料
        data = request.get_json()
        # data = {"beam_id": 5, "cell_id": "cell_003", "measurements": [...]}

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Step 3: 轉換為 JSON 字串並處理
        self._handle_indication(json.dumps(data))

        # Step 4: 增加處理計數器
        MESSAGES_PROCESSED.inc()

        return jsonify({
            "status": "success",
            "message": "Indication processed"
        }), 200

    except Exception as e:
        logger.error(f"Error processing E2 indication: {e}")
        return jsonify({"error": str(e)}), 500
```

### 4.2 Indication 處理邏輯

**位置**: `xapps/kpimon-go-xapp/src/kpimon.py:283-362`

#### Step 1: 解析 JSON 並提取 beam_id

```python
def _handle_indication(self, payload):
    """Handle RIC Indication messages containing KPIs with beam_id support"""
    try:
        # 解析 JSON
        indication = json.loads(payload)

        # 提取基本資訊
        cell_id = indication.get('cell_id')          # "cell_003"
        ue_id = indication.get('ue_id')              # "ue_015"
        beam_id = indication.get('beam_id', 'n/a')   # 5 (預設 'n/a' 向後相容)
        timestamp = indication.get('timestamp', datetime.now().isoformat())
        measurements = indication.get('measurements', [])

        logger.debug(f"Received {len(measurements)} measurements from cell {cell_id}, beam {beam_id}")
```

**向後相容設計**:
- 如果 indication 沒有 `beam_id` 欄位 → 預設為 `'n/a'`
- 適用於舊版 E2 Simulator 或其他不支援 beam_id 的資料來源

#### Step 2: 處理每個 Measurement

```python
        # 迭代每個測量值
        for measurement in measurements:
            kpi_name = measurement.get('name')          # "L1-RSRP.beam"
            kpi_value = measurement.get('value')        # -78.5

            # ← 重要！Beam-specific measurements 有自己的 beam_id
            measurement_beam_id = measurement.get('beam_id', beam_id)

            # measurement_beam_id = 5 (從測量值自己的 beam_id)
            # 或者 = beam_id (從 indication 頂層)
```

**為什麼有兩層 beam_id？**

| 層級 | 欄位 | 範例值 | 用途 |
|------|------|--------|------|
| **Indication 頂層** | `indication['beam_id']` | `5` | 整體 indication 的預設 beam |
| **Measurement 內** | `measurement['beam_id']` | `5` | 特定測量值的 beam (L1-RSRP, L1-SINR) |

**設計理由**:
- **向後相容**: 舊版 KPI 沒有 beam_id，從 indication 頂層繼承
- **精確性**: Beam-specific KPI (L1-RSRP, L1-SINR) 必須明確標記是哪個 beam

#### Step 3: KPI 定義查找

```python
            if kpi_name in self.kpi_definitions:
                kpi_def = self.kpi_definitions[kpi_name]
                is_beam_specific = kpi_def.get('beam_specific', False)

                # 範例: L1-RSRP.beam
                # kpi_def = {
                #     "id": 21,
                #     "type": "beam_signal",
                #     "unit": "dBm",
                #     "beam_specific": True  ← 關鍵標記
                # }
```

**KPI 定義 (Line 64-88)**:
```python
self.kpi_definitions = {
    # 傳統 KPIs (非 beam-specific)
    "DRB.UEThpDl": {"id": 1, "type": "throughput", "unit": "Mbps"},
    "UE.RSRP": {"id": 16, "type": "signal", "unit": "dBm"},

    # Beam-specific KPIs (5G NR beamforming)
    "L1-RSRP.beam": {
        "id": 21,
        "type": "beam_signal",
        "unit": "dBm",
        "beam_specific": True  ← 標記為 beam-specific
    },
    "L1-SINR.beam": {
        "id": 22,
        "type": "beam_signal",
        "unit": "dB",
        "beam_specific": True
    }
}
```

#### Step 4: 組裝 KPI 資料結構

```python
                kpi_data = {
                    'timestamp': timestamp,                # "2025-11-19T10:30:45"
                    'cell_id': cell_id,                    # "cell_003"
                    'ue_id': ue_id,                        # "ue_015"
                    'beam_id': measurement_beam_id,        # 5 ← 來自測量值或頂層
                    'kpi_name': kpi_name,                  # "L1-RSRP.beam"
                    'kpi_value': kpi_value,                # -78.5
                    'kpi_type': kpi_def['type'],           # "beam_signal"
                    'unit': kpi_def['unit'],               # "dBm"
                    'beam_specific': is_beam_specific      # True
                }
```

---

## 5. Redis 多層儲存策略

### 5.1 儲存策略總覽

KPIMON 將 beam 資料儲存到 **4 個不同的 Redis key 結構**，每個結構有不同的查詢用途：

| Redis Key Pattern | 用途 | TTL | 範例 |
|-------------------|------|-----|------|
| **1. kpi:{cell_id}:{kpi_name}:beam_{beam_id}** | Beam-specific KPI 查詢 | 300s | `kpi:cell_003:L1-RSRP.beam:beam_5` |
| **2. kpi:beam:{beam_id}:cell:{cell_id}:{kpi_name}** | Beam-centric 查詢 (Beam Query API) | 300s | `kpi:beam:5:cell:cell_003:L1-RSRP.beam` |
| **3. ue:beam:{beam_id}:cell:{cell_id}:{ue_id}** | UE-Beam 關聯 | 300s | `ue:beam:5:cell:cell_003:ue_015` |
| **4. kpi:timeline:{cell_id}:beam_{beam_id}** | Beam 時序資料 | ∞ | `kpi:timeline:cell_003:beam_5` |

### 5.2 詳細儲存邏輯

**位置**: `xapps/kpimon-go-xapp/src/kpimon.py:331-356`

#### 策略 1: KPI-centric Storage (傳統模式)

```python
# Line 332-339: 儲存到 Redis
if self.redis_client:
    # 根據是否為 beam-specific 決定 key 格式
    if is_beam_specific:
        # Beam-specific KPIs: 包含 beam_id
        key = f"kpi:{cell_id}:{kpi_name}:beam_{measurement_beam_id}"
        # 範例: kpi:cell_003:L1-RSRP.beam:beam_5
    else:
        # 非 Beam-specific KPIs: 傳統格式 (向後相容)
        key = f"kpi:{cell_id}:{kpi_name}"
        # 範例: kpi:cell_003:DRB.UEThpDl

    # 儲存 KPI 資料，TTL 300 秒
    self.redis_client.setex(key, 300, json.dumps(kpi_data))
```

**儲存資料範例**:
```json
// Redis Key: kpi:cell_003:L1-RSRP.beam:beam_5
// Value:
{
  "timestamp": "2025-11-19T10:30:45",
  "cell_id": "cell_003",
  "ue_id": "ue_015",
  "beam_id": 5,
  "kpi_name": "L1-RSRP.beam",
  "kpi_value": -78.5,
  "kpi_type": "beam_signal",
  "unit": "dBm",
  "beam_specific": true
}
```

#### 策略 2: Beam-centric Storage (Beam Query API)

```python
# Line 341-343: Beam-centric 儲存 (用於 Beam Query API)
beam_key = f"kpi:beam:{measurement_beam_id}:cell:{cell_id}:{kpi_name}"
# 範例: kpi:beam:5:cell:cell_003:L1-RSRP.beam

self.redis_client.setex(beam_key, 300, json.dumps(kpi_data))
```

**為什麼需要這個 key？**

這個 key 格式**以 beam_id 為主要索引**，方便 Beam Query API 快速查詢：

```bash
# 查詢 Beam 5 的所有 KPI
redis-cli KEYS "kpi:beam:5:cell:*"

# 結果:
# kpi:beam:5:cell:cell_001:L1-RSRP.beam
# kpi:beam:5:cell:cell_002:L1-RSRP.beam
# kpi:beam:5:cell:cell_003:L1-RSRP.beam
# kpi:beam:5:cell:cell_001:L1-SINR.beam
# ...
```

#### 策略 3: UE-Beam Association

```python
# Line 345-348: 記錄 UE 與 Beam 的關聯
if ue_id:
    ue_beam_key = f"ue:beam:{measurement_beam_id}:cell:{cell_id}:{ue_id}"
    # 範例: ue:beam:5:cell:cell_003:ue_015

    self.redis_client.setex(ue_beam_key, 300, "1")
```

**用途**:
- 查詢哪些 UE 正在使用 Beam 5
- 分析 Beam 的負載情況

```bash
# 查詢 Beam 5 服務的所有 UE
redis-cli KEYS "ue:beam:5:cell:cell_003:*"

# 結果:
# ue:beam:5:cell:cell_003:ue_001
# ue:beam:5:cell:cell_003:ue_015
# ue:beam:5:cell:cell_003:ue_020
```

#### 策略 4: Timeline Storage (時序資料)

```python
# Line 350-356: 儲存時序資料 (Sorted Set)

# Cell-level timeline (向後相容)
self.redis_client.zadd(f"kpi:timeline:{cell_id}", {timestamp: kpi_value})
# Key: kpi:timeline:cell_003
# Score: timestamp
# Member: kpi_value

# Beam-specific timeline (新功能)
if is_beam_specific and measurement_beam_id != 'n/a':
    beam_timeline_key = f"kpi:timeline:{cell_id}:beam_{measurement_beam_id}"
    # 範例: kpi:timeline:cell_003:beam_5

    self.redis_client.zadd(beam_timeline_key, {timestamp: kpi_value})
```

**Redis Sorted Set 結構**:
```
# Key: kpi:timeline:cell_003:beam_5
# Type: ZSET (Sorted Set)

Score (timestamp)          | Member (kpi_value)
---------------------------|-------------------
1732001445.123             | -78.5
1732001450.456             | -79.2
1732001455.789             | -77.8
```

**查詢最近 5 分鐘的資料**:
```bash
# 計算時間範圍
now=$(date +%s)
five_min_ago=$((now - 300))

# 查詢 Beam 5 最近 5 分鐘的 L1-RSRP
redis-cli ZRANGEBYSCORE kpi:timeline:cell_003:beam_5 $five_min_ago $now
```

### 5.3 Prometheus Metrics 更新

```python
# Line 324-329: 更新 Prometheus Gauge
KPI_VALUES.labels(
    kpi_type=kpi_name,        # "L1-RSRP.beam"
    cell_id=cell_id,          # "cell_003"
    beam_id=str(measurement_beam_id)  # "5"
).set(kpi_value)  # -78.5
```

**Prometheus Metric 格式**:
```
kpimon_kpi_value{kpi_type="L1-RSRP.beam",cell_id="cell_003",beam_id="5"} -78.5
kpimon_kpi_value{kpi_type="L1-SINR.beam",cell_id="cell_003",beam_id="5"} 22.3
```

### 5.4 Anomaly Detection

```python
# Line 359: 觸發異常檢測
self._detect_anomalies(cell_id, measurements, beam_id)
```

**Anomaly Detection 會檢查**:
- RSRP < -110 dBm (信號過弱)
- SINR < 10 dB (干擾過大)
- Packet Loss > 5% (丟包率過高)

**日誌範例**:
```log
WARNING - Anomaly detected in cell_003, beam 5:
  - L1-RSRP: -112.5 dBm (threshold: -110)
  - L1-SINR: 9.1 dB (threshold: 10)
```

---

## 6. 查詢階段

### 6.1 Beam Query API 實作

**位置**: `xapps/kpimon-go-xapp/src/beam_query_api.py`

#### API Endpoint

```python
@beam_api.route('/api/beam/<int:beam_id>/kpi', methods=['GET'])
def get_beam_kpi(beam_id: int):
    """
    Get KPI data for a specific beam ID

    Query Parameters:
    - kpi_type: all, signal_quality, throughput, packet_loss, resource_utilization
    - time_range: current, last_5min, last_hour
    """
```

#### 查詢流程

```python
# Step 1: 驗證 beam_id (0-7)
if not (0 <= beam_id <= 7):
    return jsonify({
        "status": "error",
        "message": f"Invalid beam_id: {beam_id}. Must be 0-7"
    }), 400

# Step 2: 從 Redis 查詢所有相關 KPI
# 使用 Beam-centric key pattern
pattern = f"kpi:beam:{beam_id}:cell:*"
keys = redis_client.keys(pattern)

# 範例結果:
# keys = [
#     'kpi:beam:5:cell:cell_001:L1-RSRP.beam',
#     'kpi:beam:5:cell:cell_002:L1-RSRP.beam',
#     'kpi:beam:5:cell:cell_003:L1-RSRP.beam',
#     'kpi:beam:5:cell:cell_001:L1-SINR.beam',
#     ...
# ]

# Step 3: 批量讀取所有 KPI 資料
kpi_data_list = []
for key in keys:
    data_str = redis_client.get(key)
    if data_str:
        kpi_data = json.loads(data_str)
        kpi_data_list.append(kpi_data)

# Step 4: 聚合並計算統計資訊
aggregated = aggregate_kpi_data(kpi_data_list, beam_id)

# Step 5: 返回 JSON
return jsonify({
    "status": "success",
    "beam_id": beam_id,
    "timestamp": datetime.now().isoformat(),
    "data": aggregated
}), 200
```

#### 聚合邏輯範例

```python
def aggregate_kpi_data(kpi_data_list, beam_id):
    """聚合多個 cell 的 beam KPI"""

    # 初始化
    result = {
        "beam_id": beam_id,
        "cells": [],
        "signal_quality": {
            "rsrp_avg": None,
            "rsrp_min": None,
            "rsrp_max": None,
            "sinr_avg": None,
            "sinr_min": None,
            "sinr_max": None
        }
    }

    # 按 cell 分組
    cells_data = {}
    for kpi in kpi_data_list:
        cell_id = kpi['cell_id']
        if cell_id not in cells_data:
            cells_data[cell_id] = {}
        cells_data[cell_id][kpi['kpi_name']] = kpi['kpi_value']

    # 計算每個 cell 的平均值
    rsrp_values = []
    sinr_values = []

    for cell_id, kpis in cells_data.items():
        l1_rsrp = kpis.get('L1-RSRP.beam')
        l1_sinr = kpis.get('L1-SINR.beam')

        if l1_rsrp is not None:
            rsrp_values.append(l1_rsrp)
        if l1_sinr is not None:
            sinr_values.append(l1_sinr)

        result["cells"].append({
            "cell_id": cell_id,
            "l1_rsrp": l1_rsrp,
            "l1_sinr": l1_sinr
        })

    # 計算統計資訊
    if rsrp_values:
        result["signal_quality"]["rsrp_avg"] = np.mean(rsrp_values)
        result["signal_quality"]["rsrp_min"] = min(rsrp_values)
        result["signal_quality"]["rsrp_max"] = max(rsrp_values)

    if sinr_values:
        result["signal_quality"]["sinr_avg"] = np.mean(sinr_values)
        result["signal_quality"]["sinr_min"] = min(sinr_values)
        result["signal_quality"]["sinr_max"] = max(sinr_values)

    return result
```

### 6.2 CLI 查詢工具

**位置**: `scripts/query-beam.sh`

```bash
#!/bin/bash

# 參數
BEAM_ID=${1:-1}
KPI_TYPE=${2:-all}

# API URL
API_URL="http://localhost:8081"
QUERY_URL="${API_URL}/api/beam/${BEAM_ID}/kpi?kpi_type=${KPI_TYPE}"

# 執行查詢
echo "Querying Beam ${BEAM_ID} KPIs (type: ${KPI_TYPE})..."
curl -s "${QUERY_URL}" | jq '.'
```

**使用範例**:
```bash
# 查詢 Beam 5 所有 KPI
./scripts/query-beam.sh 5

# 查詢 Beam 5 信號品質
./scripts/query-beam.sh 5 signal_quality

# 查詢 Beam 5 吞吐量
./scripts/query-beam.sh 5 throughput
```

**輸出範例**:
```json
{
  "status": "success",
  "beam_id": 5,
  "timestamp": "2025-11-19T10:35:22",
  "data": {
    "beam_id": 5,
    "cells": [
      {
        "cell_id": "cell_001",
        "l1_rsrp": -78.5,
        "l1_sinr": 22.3
      },
      {
        "cell_id": "cell_002",
        "l1_rsrp": -80.1,
        "l1_sinr": 21.5
      },
      {
        "cell_id": "cell_003",
        "l1_rsrp": -79.8,
        "l1_sinr": 20.9
      }
    ],
    "signal_quality": {
      "rsrp_avg": -79.47,
      "rsrp_min": -80.1,
      "rsrp_max": -78.5,
      "sinr_avg": 21.57,
      "sinr_min": 20.9,
      "sinr_max": 22.3
    }
  }
}
```

### 6.3 Web UI 查詢

**位置**: `frontend-beam-query/app.js`

```javascript
async function queryBeamKPI() {
    const beamId = document.getElementById('beamIdSelect').value;
    const kpiType = 'all';

    const url = `/api/beam/${beamId}/kpi?kpi_type=${kpiType}`;

    try {
        // 透過 proxy-server.py 發送請求
        const response = await fetch(url);
        const data = await response.json();

        if (data.status === 'success') {
            updateQuickStats(data.data);
            updateDetailedTable(data.data);
        } else {
            showError(data.message);
        }
    } catch (error) {
        console.error('Query failed:', error);
        showError('Failed to fetch Beam KPI data');
    }
}
```

**CORS 處理 (proxy-server.py)**:
```python
class BeamProxyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # 解析路徑
        parsed_path = urllib.parse.urlparse(self.path)

        if parsed_path.path.startswith('/api/'):
            # Proxy 到 KPIMON API
            target_url = f"http://localhost:8081{self.path}"

            try:
                # 發送請求到 KPIMON
                response = urllib.request.urlopen(target_url)
                content = response.read()

                # 返回給前端，加上 CORS header
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content)

            except Exception as e:
                self.send_error(500, f"Proxy error: {str(e)}")
        else:
            # 靜態檔案 (index.html, app.js)
            super().do_GET()
```

---

## 7. 完整資料流程圖

### 7.1 Complete End-to-End Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: BEAM ID 生成與配置                                     │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────────────────┐
  │ Environment Variable │
  │ BEAM_IDS="1,2,5"     │
  └──────────┬───────────┘
             │ Priority 1
             ↓
  ┌──────────────────────┐
  │ config/simulator.yaml│
  │ beams: [1,2,5]       │
  └──────────┬───────────┘
             │ Priority 2
             ↓
  ┌──────────────────────┐
  │ Default: [0..7]      │
  └──────────┬───────────┘
             │ Priority 3
             ↓
  ┌──────────────────────────────────┐
  │ E2 Simulator: active_beam_ids    │
  │ = [1, 2, 5]                      │
  └──────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: KPI INDICATION 生成                                    │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────┐
  │ E2 Simulator                         │
  │ generate_kpi_indication()            │
  └──────────┬───────────────────────────┘
             │
             ├─ Step 1: 隨機選擇 beam_id
             │  beam_id = random.choice([1,2,5]) → 5
             │
             ├─ Step 2: 生成基本 KPIs
             │  DRB.UEThpDl, UE.RSRP, UE.SINR, ...
             │
             ├─ Step 3: 生成 Beam-specific KPIs
             │  beam_quality_factor = 1.0 - (5 * 0.05) = 0.75
             │  L1-RSRP = -85.0 * 0.75 = -63.75 dBm
             │  L1-SINR = 20.0 * 0.75 = 15.0 dB
             │
             └─ Step 4: 組裝 JSON
                {
                  "beam_id": 5,
                  "cell_id": "cell_003",
                  "ue_id": "ue_015",
                  "measurements": [
                    {"name": "L1-RSRP.beam", "value": -63.75, "beam_id": 5},
                    {"name": "L1-SINR.beam", "value": 15.0, "beam_id": 5}
                  ]
                }

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3: HTTP 傳輸                                              │
└─────────────────────────────────────────────────────────────────┘

  E2 Simulator (ricxapp)
      │
      │ HTTP POST
      │ URL: http://kpimon.ricxapp.svc.cluster.local:8081/e2/indication
      │ Headers: Content-Type: application/json
      │ Body: {"beam_id": 5, ...}
      │
      ↓
  Kubernetes Service (kpimon)
      │
      │ DNS: kpimon.ricxapp.svc.cluster.local → 10.43.x.x
      │ Port Forwarding: 8081 → 8081
      │
      ↓
  KPIMON Pod (ricxapp)
      │
      │ Flask Server: 0.0.0.0:8081
      │
      ↓
  Flask Route: /e2/indication

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 4: KPIMON 接收與解析                                      │
└─────────────────────────────────────────────────────────────────┘

  Flask Route Handler
      │
      ├─ Step 1: request.get_json()
      │  data = {"beam_id": 5, "measurements": [...]}
      │
      ├─ Step 2: MESSAGES_RECEIVED.inc()
      │
      ├─ Step 3: _handle_indication(json.dumps(data))
      │
      └─ Step 4: MESSAGES_PROCESSED.inc()

  _handle_indication()
      │
      ├─ Step 1: 解析 JSON
      │  indication = json.loads(payload)
      │  beam_id = indication.get('beam_id', 'n/a')  → 5
      │
      ├─ Step 2: 迭代 measurements
      │  for measurement in measurements:
      │      kpi_name = "L1-RSRP.beam"
      │      kpi_value = -63.75
      │      measurement_beam_id = measurement.get('beam_id', beam_id) → 5
      │
      ├─ Step 3: 查找 KPI 定義
      │  kpi_def = self.kpi_definitions["L1-RSRP.beam"]
      │  is_beam_specific = True
      │
      └─ Step 4: 組裝 kpi_data
         {
           "beam_id": 5,
           "kpi_name": "L1-RSRP.beam",
           "kpi_value": -63.75,
           "beam_specific": true
         }

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 5: REDIS 多層儲存                                         │
└─────────────────────────────────────────────────────────────────┘

  Redis Storage (4 層結構)
      │
      ├─ Layer 1: KPI-centric
      │  Key: kpi:cell_003:L1-RSRP.beam:beam_5
      │  Value: {"beam_id": 5, "kpi_value": -63.75, ...}
      │  TTL: 300s
      │
      ├─ Layer 2: Beam-centric (Beam Query API)
      │  Key: kpi:beam:5:cell:cell_003:L1-RSRP.beam
      │  Value: {"beam_id": 5, "kpi_value": -63.75, ...}
      │  TTL: 300s
      │
      ├─ Layer 3: UE-Beam Association
      │  Key: ue:beam:5:cell:cell_003:ue_015
      │  Value: "1"
      │  TTL: 300s
      │
      └─ Layer 4: Timeline (Sorted Set)
         Key: kpi:timeline:cell_003:beam_5
         ZADD: score=1732001445.123, member=-63.75

  Prometheus Metrics
      │
      └─ KPI_VALUES.labels(
           kpi_type="L1-RSRP.beam",
           cell_id="cell_003",
           beam_id="5"
         ).set(-63.75)

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 6: 查詢階段                                               │
└─────────────────────────────────────────────────────────────────┘

  User Query: "查詢 Beam 5 的 KPI"
      │
      ├─────────────────┬────────────────┬────────────────┐
      │                 │                │                │
      ↓                 ↓                ↓                ↓
  [CLI Tool]      [Web UI]         [REST API]     [Prometheus]
      │                 │                │                │
      │                 │                │                │
      ↓                 ↓                ↓                ↓
  ./scripts/      Browser         curl GET        Query
  query-beam.sh   fetch()         /api/...        PromQL
      │                 │                │
      │                 ↓                │
      │           proxy-server.py       │
      │                 │                │
      └─────────────────┼────────────────┘
                        │
                        ↓
              KPIMON Beam Query API
              /api/beam/5/kpi
                        │
                        ├─ Step 1: 驗證 beam_id (0-7)
                        │
                        ├─ Step 2: Redis KEYS
                        │  pattern = "kpi:beam:5:cell:*"
                        │  keys = [
                        │    "kpi:beam:5:cell:cell_001:L1-RSRP.beam",
                        │    "kpi:beam:5:cell:cell_002:L1-RSRP.beam",
                        │    "kpi:beam:5:cell:cell_003:L1-RSRP.beam",
                        │    ...
                        │  ]
                        │
                        ├─ Step 3: 批量讀取
                        │  for key in keys:
                        │      kpi_data = json.loads(redis.get(key))
                        │
                        ├─ Step 4: 聚合計算
                        │  rsrp_avg = np.mean(rsrp_values)
                        │  sinr_avg = np.mean(sinr_values)
                        │
                        └─ Step 5: 返回 JSON
                           {
                             "status": "success",
                             "beam_id": 5,
                             "data": {
                               "signal_quality": {
                                 "rsrp_avg": -79.47,
                                 "sinr_avg": 21.57
                               },
                               "cells": [...]
                             }
                           }
```

### 7.2 Timing Diagram

```
Time   │ E2 Simulator         │ Network        │ KPIMON              │ Redis
───────┼─────────────────────┼────────────────┼─────────────────────┼────────────
00:00  │ Generate beam_id=5   │                │                     │
00:01  │ Generate L1-RSRP     │                │                     │
00:02  │ Generate L1-SINR     │                │                     │
00:03  │ Assemble JSON        │                │                     │
00:04  │ HTTP POST ──────────>│                │                     │
00:05  │                      │ DNS Lookup     │                     │
00:06  │                      │ TCP Connect ──>│                     │
00:07  │                      │                │ Receive POST        │
00:08  │                      │                │ Parse JSON          │
00:09  │                      │                │ Extract beam_id=5   │
00:10  │                      │                │ SETEX ─────────────>│
00:11  │                      │                │ SETEX (beam-centric)>│
00:12  │                      │                │ SETEX (ue-beam) ───>│
00:13  │                      │                │ ZADD (timeline) ───>│
00:14  │                      │                │ Prometheus update   │
00:15  │                      │<── 200 OK ────│                     │
00:16  │ Success ✓            │                │                     │
00:17  │ Sleep 5s             │                │                     │
...    │                      │                │                     │
05:00  │ Next iteration       │                │                     │
```

---

## 8. 技術細節與設計決策

### 8.1 為什麼使用雙層 beam_id？

**問題**: 為什麼 beam_id 同時存在於 indication 頂層和 measurement 內？

**Answer**:

| 層級 | 位置 | 用途 | 範例 |
|------|------|------|------|
| **Indication Level** | `indication['beam_id']` | 整體 indication 的**預設 beam** | `{"beam_id": 5, ...}` |
| **Measurement Level** | `measurement['beam_id']` | 特定測量值的**精確 beam** | `{"name": "L1-RSRP.beam", "beam_id": 5}` |

**設計理由**:

1. **向後相容**:
   - 舊版 KPI (DRB.UEThpDl, UE.RSRP) 沒有 beam_id 欄位
   - 從 indication 頂層繼承 `beam_id`

2. **精確性**:
   - Beam-specific KPI (L1-RSRP, L1-SINR) **必須明確標記**是哪個 beam
   - 避免混淆

3. **靈活性**:
   - 未來可能有「Multi-beam KPI」（一個 indication 包含多個 beam 的測量值）
   - 每個 measurement 都有自己的 beam_id

**程式碼範例**:
```python
# KPIMON 處理邏輯
indication_beam_id = indication.get('beam_id', 'n/a')  # 預設 beam

for measurement in measurements:
    # 優先使用 measurement 自己的 beam_id，否則用 indication 的
    measurement_beam_id = measurement.get('beam_id', indication_beam_id)

    # measurement_beam_id 永遠是正確的 beam ID
```

### 8.2 為什麼需要 4 種 Redis Key 結構？

**問題**: 為什麼不用單一 key 格式，而是 4 種？

**Answer**: **不同查詢場景需要不同的索引結構**

| Key Pattern | 查詢場景 | 範例查詢 |
|-------------|---------|---------|
| **kpi:{cell}:{kpi_name}:beam_{id}** | Cell-centric 查詢 | 「Cell 003 的 Beam 5 L1-RSRP 是多少？」 |
| **kpi:beam:{id}:cell:{cell}:{kpi}** | Beam-centric 查詢 | 「Beam 5 在所有 cell 的平均 L1-RSRP？」 |
| **ue:beam:{id}:cell:{cell}:{ue}** | UE 分析 | 「Beam 5 目前服務哪些 UE？」 |
| **kpi:timeline:{cell}:beam_{id}** | 時序分析 | 「Beam 5 過去 5 分鐘的 L1-RSRP 趨勢？」 |

**如果只用單一 key 格式**:
-  [FAIL] 查詢 Beam 5 所有 KPI 需要 `KEYS kpi:*:*:beam_5` → O(N) 全掃描
-  [FAIL] 查詢 Cell 003 所有 Beam 需要 `KEYS kpi:cell_003:*` 再過濾 → 效率低
-  [FAIL] 查詢 UE-Beam 關聯需要解析所有 KPI 資料 → 浪費記憶體

**多層 key 結構的優勢**:
-  [DONE] **查詢效率高**: 每種查詢都有對應的索引
-  [DONE] **Redis 記憶體最佳化**: 只查詢需要的資料
-  [DONE] **擴展性**: 未來新增查詢場景，新增 key pattern 即可

### 8.3 TTL 設計

**問題**: 為什麼 TTL 設為 300 秒（5 分鐘）？

**Answer**:

```python
self.redis_client.setex(key, 300, json.dumps(kpi_data))
#                           ^^^ TTL = 300 seconds
```

**設計考量**:

1. **E2 Simulator 發送頻率**: 5 秒一次
   - 5 分鐘內會有 60 個 indication
   - TTL 300 秒 = 保留最近 60 個資料點

2. **查詢時效性**:
   - Beam KPI 查詢通常關注「當前狀態」
   - 5 分鐘內的資料足以代表「當前」

3. **Redis 記憶體管理**:
   - 自動清理過期資料，避免記憶體洩漏
   - 300 秒 TTL → 每個 key 佔用記憶體時間有限

4. **Timeline 資料不設 TTL**:
   ```python
   # Timeline 使用 Sorted Set，不設 TTL
   self.redis_client.zadd(f"kpi:timeline:{cell_id}:beam_{beam_id}", {timestamp: kpi_value})
   ```
   - 用於長期趨勢分析
   - 需手動清理或設定過期策略

### 8.4 Beam Quality Factor 設計

**問題**: 為什麼 Beam 0 信號最好，Beam 7 最差？

**Answer**: **模擬真實 5G NR 波束成形場景**

```python
# Line 211-212: Beam Quality Factor
beam_quality_factor = 1.0 - (beam_id * 0.05)

# Beam 0: 1.0 - (0 * 0.05) = 1.0    (100% 品質)
# Beam 1: 1.0 - (1 * 0.05) = 0.95   (95% 品質)
# Beam 2: 1.0 - (2 * 0.05) = 0.90   (90% 品質)
# ...
# Beam 7: 1.0 - (7 * 0.05) = 0.65   (65% 品質)
```

**真實 5G 場景**:
- **Beam 0**: 通常是**主波束**（Main Beam），覆蓋最佳區域
- **Beam 1-3**: 輔助波束，覆蓋次佳區域
- **Beam 4-7**: 邊緣波束，覆蓋邊緣區域（信號較弱）

**模擬效果**:
```
Beam 0: L1-RSRP = -70 dBm  (優秀)
Beam 1: L1-RSRP = -73.5 dBm
Beam 2: L1-RSRP = -77.8 dBm
Beam 3: L1-RSRP = -82.5 dBm
Beam 4: L1-RSRP = -87.5 dBm
Beam 5: L1-RSRP = -92.8 dBm
Beam 6: L1-RSRP = -98.5 dBm
Beam 7: L1-RSRP = -104.3 dBm (較差，可能觸發 anomaly)
```

### 8.5 Prometheus vs Redis 儲存

**問題**: 為什麼同時用 Prometheus 和 Redis？

**Answer**: **不同用途**

| 儲存系統 | 用途 | 保留時間 | 查詢方式 |
|---------|------|---------|---------|
| **Prometheus** | 監控告警、趨勢圖表 | 15 天（預設） | PromQL |
| **Redis** | 即時查詢、API | 300 秒（TTL） | Key-Value / Sorted Set |

**Prometheus 優勢**:
-  [DONE] 長期儲存（15 天 - 90 天）
-  [DONE] 強大的聚合查詢（rate, increase, histogram_quantile）
-  [DONE] Grafana 原生支援
-  [DONE] 告警規則（AlertManager）

**Redis 優勢**:
-  [DONE] 即時查詢（< 10ms）
-  [DONE] 彈性資料結構（JSON, Sorted Set）
-  [DONE] TTL 自動過期
-  [DONE] Beam Query API 直接讀取

**互補關係**:
```
Prometheus: "Beam 5 過去 1 小時的平均 L1-RSRP？"
            PromQL: avg_over_time(kpimon_kpi_value{beam_id="5"}[1h])

Redis:      "Beam 5 當前的 L1-RSRP？"
            Key: kpi:beam:5:cell:cell_003:L1-RSRP.beam
```

### 8.6 CORS 問題與 Proxy 解決方案

**問題**: 為什麼需要 proxy-server.py？

**Answer**: **瀏覽器 CORS 安全限制**

**CORS 錯誤場景**:
```
Web UI (http://localhost:8888)
    │
    │ fetch('http://localhost:8081/api/beam/5/kpi')
    │
    ↓
Browser 阻止請求！
Error: CORS policy: No 'Access-Control-Allow-Origin' header
```

**為什麼被阻止？**
- Origin 1: `http://localhost:8888` (Web UI)
- Origin 2: `http://localhost:8081` (KPIMON API)
- **Cross-Origin** → 瀏覽器安全策略阻止

**解決方案: Proxy Server**

```
Web UI (http://localhost:8888)
    │
    │ fetch('/api/beam/5/kpi')  ← Same Origin！
    │
    ↓
proxy-server.py (http://localhost:8888)
    │
    │ 內部轉發到 http://localhost:8081/api/beam/5/kpi
    │
    ↓
KPIMON API (http://localhost:8081)
```

**Proxy 程式碼**:
```python
# frontend-beam-query/proxy-server.py
class BeamProxyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)

        if parsed_path.path.startswith('/api/'):
            # Proxy to KPIMON API
            target_url = f"http://localhost:8081{self.path}"
            response = urllib.request.urlopen(target_url)
            content = response.read()

            # 加上 CORS header（雖然 Same Origin 不需要，但加上更安全）
            self.send_header('Access-Control-Allow-Origin', '*')
            self.wfile.write(content)
        else:
            # 提供靜態檔案 (index.html, app.js)
            super().do_GET()
```

**app.js 配置**:
```javascript
// Before: CORS error
const API_BASE_URL = 'http://localhost:8081';

// After: Same origin (no CORS)
const API_BASE_URL = '';  // Empty string = same origin
```

---

## 9. 總結

### 核心流程回顧

```
Beam ID 資料傳輸 5 階段：

1. 【生成】E2 Simulator 隨機選擇 beam_id (0-7)
2. 【傳輸】HTTP POST 到 KPIMON /e2/indication
3. 【解析】KPIMON 提取 beam_id 並組裝 kpi_data
4. 【儲存】Redis 4 層結構儲存 + Prometheus metrics
5. 【查詢】CLI / Web UI / REST API 查詢 Redis
```

### 關鍵設計亮點

-  [DONE] **動態配置**: `BEAM_IDS` 環境變數控制生成哪些 beam
-  [DONE] **雙層 beam_id**: Indication 頂層 + Measurement 內部
-  [DONE] **4 層 Redis 儲存**: 不同查詢場景的最佳化索引
-  [DONE] **向後相容**: 支援舊版無 beam_id 的資料格式
-  [DONE] **Beam Quality Degradation**: 模擬真實 5G 波束品質差異
-  [DONE] **TTL 自動過期**: 300 秒 TTL 避免 Redis 記憶體洩漏
-  [DONE] **Prometheus + Redis**: 長期監控 + 即時查詢的完美組合
-  [DONE] **CORS Proxy**: 解決前端跨域問題

### 程式碼位置速查

| 功能 | 檔案路徑 | 關鍵行數 |
|------|---------|---------|
| Beam ID 配置載入 | `simulator/e2-simulator/src/e2_simulator.py` | Line 76-148 |
| KPI Indication 生成 | `simulator/e2-simulator/src/e2_simulator.py` | Line 150-239 |
| HTTP 傳輸 | `simulator/e2-simulator/src/e2_simulator.py` | Line 300-330 |
| Flask Route 接收 | `xapps/kpimon-go-xapp/src/kpimon.py` | Line 171-195 |
| Indication 處理 | `xapps/kpimon-go-xapp/src/kpimon.py` | Line 283-362 |
| Redis 多層儲存 | `xapps/kpimon-go-xapp/src/kpimon.py` | Line 331-356 |
| Beam Query API | `xapps/kpimon-go-xapp/src/beam_query_api.py` | 整個檔案 |
| CLI 查詢工具 | `scripts/query-beam.sh` | 整個檔案 |
| Web UI 前端 | `frontend-beam-query/app.js` | 整個檔案 |
| CORS Proxy | `frontend-beam-query/proxy-server.py` | 整個檔案 |

---

**文檔完成！**  

如有任何疑問，請參考：
- [BEAM_KPI_COMPLETE_GUIDE.md](./BEAM_KPI_COMPLETE_GUIDE.md) - Beam KPI 完整使用指南
- [DATA_FLOW_EXPLANATION.md](../DATA_FLOW_EXPLANATION.md) - 資料流程總覽
- [QUICK_START_BEAM_QUERY.md](../QUICK_START_BEAM_QUERY.md) - 快速開始指南

---

**最後更新**: 2025-11-19
**版本**: 1.0.0
**作者**: 蔡秀吉 (thc1006)
