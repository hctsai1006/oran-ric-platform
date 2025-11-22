# 選項 A：ns-3 UAV 模擬驗證計畫

**文件版本**: 1.0
**建立日期**: 2025-11-21
**狀態**: 待審核

---

## 目錄

1. [系統架構概覽](#系統架構概覽)
2. [Phase 1: 環境驗證與準備](#phase-1-環境驗證與準備)
3. [Phase 2: 網路拓撲設計](#phase-2-網路拓撲設計)
4. [Phase 3: UAV 移動性模型](#phase-3-uav-移動性模型)
5. [Phase 4: E2 介面整合](#phase-4-e2-介面整合)
6. [Phase 5: xApp 適配](#phase-5-xapp-適配)
7. [Phase 6: 基線測試](#phase-6-基線測試-無-xapp)
8. [Phase 7: xApp 控制測試](#phase-7-xapp-控制測試)
9. [Phase 8: 結果分析與報告](#phase-8-結果分析與報告)
10. [風險與備選方案](#風險與備選方案)
11. [決策事項](#決策事項)

---

## 系統架構概覽

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ns-3 模擬環境                                   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                      │
│  │   eNB #1    │    │   eNB #2    │    │   eNB #3    │   (蜂窩基地台)       │
│  │  Cell 001   │    │  Cell 002   │    │  Cell 003   │                      │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                      │
│         │                  │                  │                              │
│         └──────────────────┼──────────────────┘                              │
│                            │                                                 │
│  ┌─────────────────────────┴─────────────────────────┐                      │
│  │                    UAV (UE)                        │                      │
│  │        WaypointMobilityModel (飛行路徑)           │                      │
│  │        速度: 15 m/s, 高度: 100m                   │                      │
│  └────────────────────────────────────────────────────┘                      │
│                            │                                                 │
│  ┌─────────────────────────┴─────────────────────────┐                      │
│  │              E2 Termination (e2sim)               │                      │
│  │    - KPM Indication (RSRP, SINR, PRB)            │                      │
│  │    - RIC Control Message (Handover, PRB)          │                      │
│  └────────────────────────────────────────────────────┘                      │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ SCTP (E2AP Protocol)
                                  │ Port 36422
┌─────────────────────────────────┴───────────────────────────────────────────┐
│                           near-RT RIC                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      UAV Policy xApp                                    │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │ │
│  │  │ E2 Receiver  │─►│Policy Engine │─►│E2 Controller │                  │ │
│  │  │ (E2SM-KPM)   │  │ (決策邏輯)   │  │(E2SM-RC)     │                  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 資料流

1. **E2 Setup**: e2sim 向 RIC 註冊 E2 Node
2. **KPM Subscription**: RIC 訂閱 KPM 指標
3. **KPM Indication**: e2sim 定期報告 UAV 的 RSRP、SINR、PRB 等
4. **RIC Control**: xApp 根據指標發送切換/資源分配命令
5. **Control Execution**: ns-3 執行控制命令

---

## Phase 1: 環境驗證與準備

### 1.1 目標

確認 ns-O-RAN 與 e2sim 整合正常運作

### 1.2 任務清單

| 編號 | 任務 | 驗證方法 | 狀態 |
|------|------|----------|------|
| 1.1.1 | 確認 ns-O-RAN ORAN 模組已構建 | `ls /opt/ns-oran/build/lib/*oran*` | 待執行 |
| 1.1.2 | 確認 e2sim 函式庫存在 | `ls /usr/local/lib/libe2sim.a` | 待執行 |
| 1.1.3 | 執行 e2sim-integration-example | 無 segfault，SCTP 連接建立 | 待執行 |
| 1.1.4 | 確認 LTE 模組可用 | 執行 lena-simple-epc 範例 | 待執行 |

### 1.3 已確認資源

```
ns-O-RAN 函式庫:  /opt/ns-oran/build/lib/libns3.38.rc1-oran-default.so (6.0M)
e2sim 函式庫:     /usr/local/lib/libe2sim.a
LTE 範例:         /opt/ns-oran/src/lte/examples/lena-simple-epc.cc
ORAN 範例:        /opt/ns-oran/contrib/oran/examples/
```

### 1.4 預期輸出

- 確認所有依賴就緒
- 記錄版本資訊
- 驗證基本 E2 通訊

---

## Phase 2: 網路拓撲設計

### 2.1 場景描述

模擬城市環境中 UAV 送貨場景，UAV 從起點飛行至終點，途中經過多個蜂窩覆蓋區域

### 2.2 網路佈局

```
┌─────────────────────────────────────────────────────┐
│                    模擬區域 (1000m x 1000m)          │
│                                                     │
│     eNB#1 (200,200)      eNB#2 (500,500)           │
│         ●                    ●                      │
│        /                      \                     │
│       /   UAV 飛行路徑 ────►   \                   │
│      /                          \                   │
│    起點                        終點                 │
│   (100,100)                  (900,900)              │
│                    ●                                │
│               eNB#3 (800,200)                       │
└─────────────────────────────────────────────────────┘
```

### 2.3 eNB 配置

| 參數 | 值 | 說明 |
|------|-----|------|
| 數量 | 3 | 三個宏基站 |
| 發射功率 | 46 dBm | 標準宏站配置 |
| 頻段 | Band 7 (2600 MHz) | LTE FDD |
| 頻寬 | 20 MHz | 100 PRBs |
| 天線高度 | 30 m | 宏站標準 |
| 傳播模型 | 3GPP Urban Macro | 城市環境 |

### 2.4 eNB 位置

| eNB ID | 位置 (x, y, z) | 覆蓋半徑 |
|--------|----------------|----------|
| eNB#1 | (200, 200, 30) | ~500m |
| eNB#2 | (500, 500, 30) | ~500m |
| eNB#3 | (800, 200, 30) | ~500m |

### 2.5 UAV 配置

| 參數 | 值 | 說明 |
|------|-----|------|
| 飛行高度 | 100 m | 低空 UAV |
| 飛行速度 | 15 m/s | ~54 km/h |
| 飛行距離 | ~1131 m | 對角線 (100,100) → (900,900) |
| 模擬時長 | 100 s | 包含起飛、飛行、降落 |
| 流量類型 | 4K 視頻上傳 | 25 Mbps UL |

---

## Phase 3: UAV 移動性模型

### 3.1 移動性模型選擇

使用 **WaypointMobilityModel** - 最適合預定義飛行路徑

### 3.2 航點定義

```cpp
// C++ 實現虛擬碼
Ptr<WaypointMobilityModel> uavMobility = CreateObject<WaypointMobilityModel>();

// 航點 1: 起點 (t=0s)
uavMobility->AddWaypoint(Waypoint(Seconds(0), Vector(100, 100, 100)));

// 航點 2: 經過 eNB#1 覆蓋區 (t=20s)
uavMobility->AddWaypoint(Waypoint(Seconds(20), Vector(300, 300, 100)));

// 航點 3: 經過 eNB#2 覆蓋區中心 (t=40s)
uavMobility->AddWaypoint(Waypoint(Seconds(40), Vector(500, 500, 100)));

// 航點 4: 離開 eNB#2，接近 eNB#3 邊緣 (t=60s)
uavMobility->AddWaypoint(Waypoint(Seconds(60), Vector(700, 700, 100)));

// 航點 5: 終點 (t=75s)
uavMobility->AddWaypoint(Waypoint(Seconds(75), Vector(900, 900, 100)));
```

### 3.3 空對地通道模型

UAV 通訊有其特殊性，需要考慮：

| 特性 | 地面 UE | UAV UE |
|------|---------|--------|
| LOS 概率 | 低 (~30%) | 高 (~80%) |
| 多路徑 | 嚴重 | 較少 |
| 路徑損耗 | 較高 | 較低 |
| 干擾 | 限於本地 | 可能干擾多cell |

**實現選項**:
- A) 使用 `ThreeGppUmaChannelModel` + 調整 LOS 概率
- B) 自定義 Air-to-Ground 模型 (參考 3GPP TR 36.777)

### 3.4 預期切換點

根據飛行路徑，預期切換：
- t≈25s: eNB#1 → eNB#2 (進入 eNB#2 覆蓋)
- t≈55s: eNB#2 → eNB#3 或保持 eNB#2 (視訊號強度)

---

## Phase 4: E2 介面整合

### 4.1 架構選項比較

| 選項 | 描述 | 優點 | 缺點 | 建議 |
|------|------|------|------|------|
| A | 完整 E2AP | O-RAN 標準合規 | 實現複雜 | 正式研究 |
| B | HTTP 橋接 | 快速實現 | 非標準 | 快速驗證 |
| C | 檔案交換 | 最簡單 | 非即時 | 原型測試 |

### 4.2 E2SM-KPM 指標定義

需要從 ns-3 收集並通過 E2 報告的指標：

| KPM 指標 | O-RAN 名稱 | 說明 | 用途 |
|----------|-----------|------|------|
| RSRP Serving | RRCMeasurement.rsrp | 服務小區信號強度 (dBm) | 切換決策 |
| RSRP Neighbors | RRCMeasurement.rsrp | 鄰區信號強度 (dBm) | 目標選擇 |
| SINR | RRCMeasurement.sinr | 信噪比 (dB) | 鏈路品質 |
| PRB Utilization | DRB.PrbUsageDl | PRB 使用率 (%) | 負載評估 |
| DL Throughput | DRB.IPThpDl | 下行吞吐量 (Mbps) | QoS 監控 |
| UL Throughput | DRB.IPThpUl | 上行吞吐量 (Mbps) | QoS 監控 |
| UE Position | (custom) | UAV 位置 (x,y,z) | 預測切換 |

### 4.3 E2SM-RC 控制動作

xApp 可以發送的控制命令：

| 控制動作 | 參數 | 效果 | 對應 ns-3 API |
|----------|------|------|---------------|
| Handover | Target Cell ID | 觸發切換 | `lteHelper->HandoverRequest()` |
| PRB Allocation | PRB Count | 調整資源 | Scheduler configuration |
| QoS Modification | QCI, GBR | 調整 QoS | Bearer modification |

### 4.4 E2 通訊流程

```
時間軸:
t=0s    [ns-3] ──── E2 Setup Request ────► [xApp/RIC]
t=0s    [ns-3] ◄─── E2 Setup Response ──── [xApp/RIC]
t=0s    [ns-3] ◄─── RIC Subscription ───── [xApp/RIC]
t=0.1s  [ns-3] ──── KPM Indication ───────► [xApp/RIC]  (每100ms)
t=0.1s  [ns-3] ◄─── RIC Control (如需要) ── [xApp/RIC]
...
t=100s  [ns-3] ──── E2 Node Disconnect ──► [xApp/RIC]
```

---

## Phase 5: xApp 適配

### 5.1 當前 xApp 介面

```python
# 現有 HTTP 介面 (位置: uav-policy/src/uav_policy/server.py)
POST /e2/indication  # 接收 E2 Indication (JSON)
GET /decisions       # 查詢決策歷史
GET /health          # 健康檢查
GET /stats           # 統計資訊
```

### 5.2 需要新增的功能

```python
# 新增 E2AP 處理能力 (如選擇選項 A)
class E2APHandler:
    def __init__(self, host='0.0.0.0', port=36422):
        """初始化 SCTP 監聽器"""

    def handle_e2_setup_request(self, msg) -> E2SetupResponse:
        """
        處理 E2 Setup Request
        - 解析 gNB ID, PLMN
        - 註冊 RAN Functions (KPM, RC)
        - 回應 E2 Setup Response
        """

    def handle_ric_indication(self, msg) -> Optional[RICControl]:
        """
        處理 RIC Indication (KPM 數據)
        - 解析 RSRP, SINR, PRB 等指標
        - 調用 PolicyEngine 做決策
        - 如需要，返回 RIC Control
        """

    def send_ric_control(self, target_cell: str, action: str, params: dict):
        """
        發送 RIC Control Message
        - 編碼 E2SM-RC Control Message
        - 通過 SCTP 發送
        """
```

### 5.3 決策邏輯增強

```python
class UAVPolicyEngine:
    def make_decision(self, indication: dict) -> dict:
        """
        根據 KPM 數據做出決策

        決策規則:

        規則 1: RSRP 切換
        IF RSRP_serving < -100 dBm
           AND RSRP_neighbor > RSRP_serving + 3 dB
        THEN 觸發切換到最佳鄰區

        規則 2: 負載均衡
        IF PRB_utilization > 80%
           AND 存在 PRB_utilization < 50% 的鄰區
           AND RSRP_neighbor > -110 dBm
        THEN 觸發負載均衡切換

        規則 3: 預測切換 (基於飛行路徑)
        IF UAV 位置接近 cell 邊界 (根據飛行方向)
           AND 下一個 cell 已知
        THEN 提前觸發切換準備

        規則 4: QoS 保障
        IF throughput < target_bitrate * 0.8
           AND PRB_utilization < 70%
        THEN 請求更多 PRB 資源
        """

        decision = {
            'action': 'none',  # 'handover', 'prb_adjust', 'none'
            'target_cell': None,
            'prb_quota': None,
            'reason': ''
        }

        # 實現決策邏輯...

        return decision
```

---

## Phase 6: 基線測試 (無 xApp)

### 6.1 測試目標

建立性能基準，使用 ns-3 預設的 A3 事件觸發切換

### 6.2 測試配置

```yaml
simulation:
  duration: 100s
  seed: 1  # 可重複

network:
  enb_count: 3
  bandwidth: 20MHz
  scheduler: PfFfMacScheduler

uav:
  count: 1
  mobility: WaypointMobilityModel
  height: 100m
  speed: 15m/s

traffic:
  type: UDP
  direction: uplink
  bitrate: 25Mbps
  packet_size: 1400bytes

handover:
  algorithm: A3Rsrp
  hysteresis: 3dB
  time_to_trigger: 256ms
```

### 6.3 收集指標

| 指標 | 收集方法 | 輸出檔案 |
|------|----------|----------|
| 吞吐量 (時間序列) | RLC Tx/Rx trace | `baseline_throughput.csv` |
| 延遲 (時間序列) | RLC PDU delay | `baseline_latency.csv` |
| 切換事件 | LteHelper Handover trace | `baseline_handover.csv` |
| SINR (時間序列) | PHY SINR trace | `baseline_sinr.csv` |
| RSRP (時間序列) | RRC measurement | `baseline_rsrp.csv` |
| PRB 使用率 | MAC scheduler trace | `baseline_prb.csv` |

### 6.4 執行命令

```bash
cd /opt/ns-oran
./build/contrib/oran/examples/ns3.38.rc1-uav-baseline-default \
  --simTime=100 \
  --numberOfEnbs=3 \
  --uavSpeed=15 \
  --enableTraces=true \
  --outputDir=/home/thc1006/dev/uav-policy-results/baseline/
```

---

## Phase 7: xApp 控制測試

### 7.1 測試目標

使用 xApp 進行智能切換控制，比較與基線的性能差異

### 7.2 測試配置

與 Phase 6 相同，但:
- 啟用 E2 介面
- xApp 接收 KPM Indication (每 100ms)
- xApp 根據決策發送 RIC Control

### 7.3 xApp 決策策略

| 條件 | 動作 | 預期效果 |
|------|------|----------|
| RSRP < -100 dBm + 更好鄰區 | 主動切換 | 減少信號差的時間 |
| PRB > 80% + 低負載鄰區 | 負載均衡 | 提高吞吐量 |
| 預測將離開覆蓋 | 預防性切換 | 減少中斷時間 |

### 7.4 執行步驟

```bash
# 終端 1: 啟動 xApp
cd /home/thc1006/dev/uav-rc-xapp-with-algorithms/xapps/uav-policy
PYTHONPATH="src:$PYTHONPATH" python3 -m uav_policy.main --e2-mode

# 終端 2: 執行 ns-3 模擬
cd /opt/ns-oran
./build/contrib/oran/examples/ns3.38.rc1-uav-xapp-controlled-default \
  --simTime=100 \
  --ricAddress=127.0.0.1 \
  --ricPort=36422 \
  --enableE2=true \
  --outputDir=/home/thc1006/dev/uav-policy-results/xapp-controlled/
```

---

## Phase 8: 結果分析與報告

### 8.1 比較指標表

| 指標 | 基線 | xApp 控制 | 改善 |
|------|------|-----------|------|
| 平均吞吐量 (Mbps) | TBD | TBD | TBD% |
| 99% 延遲 (ms) | TBD | TBD | TBD% |
| 切換次數 | TBD | TBD | TBD |
| 切換失敗率 (%) | TBD | TBD | TBD% |
| 中斷時間 (ms) | TBD | TBD | TBD% |
| 平均 SINR (dB) | TBD | TBD | TBD |

### 8.2 圖表輸出

1. **吞吐量 vs 時間** - 曲線圖，基線 vs xApp
2. **SINR vs UAV 位置** - 熱力圖
3. **切換時序圖** - 顯示每次切換的時間點和目標
4. **延遲 CDF** - 累積分佈函數
5. **PRB 使用率 vs 時間** - 各 cell 的資源使用

### 8.3 分析腳本

```python
# analyze_results.py
import pandas as pd
import matplotlib.pyplot as plt

def compare_throughput(baseline_file, xapp_file):
    """比較吞吐量"""

def compare_latency(baseline_file, xapp_file):
    """比較延遲分佈"""

def analyze_handovers(baseline_ho, xapp_ho):
    """分析切換行為"""

def generate_report(results_dir):
    """生成完整報告"""
```

---

## 檔案結構

```
/home/thc1006/dev/oran-ric-platform/
├── ns3-uav-simulation/
│   ├── uav-baseline.cc             # 基線模擬腳本
│   ├── uav-xapp-controlled.cc      # xApp 控制模擬腳本
│   ├── uav-mobility-helper.h       # UAV 移動性輔助類
│   ├── uav-channel-model.cc        # 空對地通道模型 (可選)
│   └── CMakeLists.txt              # 構建配置
│
├── xapp-e2-adapter/
│   ├── e2ap_handler.py             # E2AP 協議處理
│   ├── e2sm_kpm.py                 # E2SM-KPM 編解碼
│   ├── e2sm_rc.py                  # E2SM-RC 編解碼
│   ├── ric_simulator.py            # RIC 模擬器 (選項 B)
│   └── requirements.txt
│
├── results/
│   ├── baseline/                   # 基線測試結果
│   │   ├── baseline_throughput.csv
│   │   ├── baseline_latency.csv
│   │   ├── baseline_handover.csv
│   │   └── baseline_sinr.csv
│   ├── xapp-controlled/            # xApp 控制結果
│   │   └── ...
│   └── analysis/                   # 分析報告
│       ├── comparison_report.md
│       └── figures/
│
├── scripts/
│   ├── run_baseline.sh             # 執行基線測試
│   ├── run_xapp.sh                 # 執行 xApp 測試
│   ├── analyze_results.py          # 分析腳本
│   └── plot_figures.py             # 繪圖腳本
│
└── NS3-UAV-SIMULATION-PLAN.md      # 本文件
```

---

## 風險與備選方案

### 風險 1: E2AP 實現複雜度高

**問題**: 完整實現 E2AP SCTP 通訊和 ASN.1 編解碼需要大量工作

**備選方案 B - HTTP 橋接**:
```
ns-3 ──(寫檔)──► bridge.py ──(HTTP)──► xApp
ns-3 ◄──(讀檔)── bridge.py ◄──(HTTP)── xApp
```

**備選方案 C - 檔案交換**:
```
ns-3: 每 100ms 將 KPM 寫入 /tmp/kpm_indication.json
xApp: 監視檔案，讀取處理，寫入 /tmp/ric_control.json
ns-3: 讀取控制命令並執行
```

### 風險 2: 模擬效能不足

**問題**: 即時 E2 通訊可能導致模擬速度過慢

**備選方案 - 離線回放模式**:
1. 先完整執行 ns-3 模擬，收集所有 trace
2. 將 trace 回放給 xApp（模擬 E2 Indication）
3. 記錄 xApp 決策
4. 分析「如果執行這些控制會有什麼效果」

### 風險 3: 空對地通道模型不準確

**問題**: ns-3 預設 LTE 通道模型為地面場景設計

**備選方案**:
- 參考 3GPP TR 36.777 (UAV 通道模型)
- 手動調整 LOS/NLOS 概率參數
- 使用簡化的自由空間損耗 + 隨機衰落

---

## 預估工作量

| Phase | 任務 | 複雜度 | 預估 |
|-------|------|--------|------|
| 1 | 環境驗證 | 簡單 | 低 |
| 2 | 網路拓撲 | 中等 | 中 |
| 3 | UAV 移動性 | 中等 | 中 |
| 4 | E2 介面整合 | **高** | **高** |
| 5 | xApp 適配 | 中等 | 中 |
| 6 | 基線測試 | 簡單 | 低 |
| 7 | xApp 測試 | 中等 | 中 |
| 8 | 分析報告 | 中等 | 中 |

**最複雜的部分**: Phase 4 (E2 介面整合)

---

## 決策事項

在開始執行前，需要確定以下事項：

### 決策 1: E2 介面模式

| 選項 | 描述 | 適用場景 |
|------|------|----------|
| A | 完整 E2AP (SCTP + ASN.1) | 正式研究論文 |
| B | HTTP 橋接 | 快速原型驗證 |
| C | 檔案交換 (離線) | 概念驗證 |

**建議**: 先用選項 B 或 C 快速驗證，再根據需要升級到選項 A

### 決策 2: 模擬規模

| 選項 | 描述 |
|------|------|
| A | 單 UAV + 3 eNB (基本驗證) |
| B | 3-5 UAV + 5 eNB (壓力測試) |

**建議**: 先完成選項 A，成功後再擴展

### 決策 3: 優先順序

| 選項 | 描述 |
|------|------|
| A | Phase 1-6 (基線) → Phase 4-5 (E2) → Phase 7-8 |
| B | Phase 1-4 (E2) → Phase 5 → Phase 6-8 |

**建議**: 選項 A - 先建立基線，確保模擬正確後再整合 xApp

### 決策 4: 通道模型

| 選項 | 描述 |
|------|------|
| A | 使用 ns-3 預設 Urban Macro |
| B | 實現自定義 Air-to-Ground 模型 |

**建議**: 先用選項 A，在報告中說明限制

---

## 附錄 A: 參考資料

1. **ns-3 LTE 文檔**: https://www.nsnam.org/docs/models/html/lte.html
2. **O-RAN E2 規範**: O-RAN.WG3.E2AP-v02.00
3. **E2SM-KPM 規範**: O-RAN.WG3.E2SM-KPM-v02.00
4. **3GPP TR 36.777**: Study on enhanced LTE support for aerial vehicles
5. **ns-O-RAN**: https://github.com/o-ran-sc/sim-ns3-o-ran-e2

---

## 附錄 B: 現有程式碼參考

### ns-O-RAN E2 範例

位置: `/opt/ns-oran/contrib/oran/examples/oran-interface-example.cc`

關鍵函數:
- `BuildAndSendReportMessage()`: 建構 KPM Indication
- `KpmSubscriptionCallback()`: 處理 RIC Subscription
- `RicControlMessageCallback()`: 處理 RIC Control

### LTE EPC 範例

位置: `/opt/ns-oran/src/lte/examples/lena-simple-epc.cc`

關鍵組件:
- `LteHelper`: LTE 網路建立
- `PointToPointEpcHelper`: EPC 核心網
- `MobilityHelper`: 移動性配置

---

**文件結束**

*待審核後開始執行*
