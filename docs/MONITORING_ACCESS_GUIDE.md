# O-RAN RIC 監控服務存取指南

>   **適用場景**: 透過 SSH 連線到遠端機器，使用 VS Code IDE，想要在本地瀏覽器存取 Grafana、Prometheus 等監控服務

**最後更新**: 2025-11-19
**狀態**:  [DONE] 已測試驗證

---

##   Quick Start (3 分鐘)

### 步驟 1: 啟動 Port Forwarding

在 VS Code Terminal 執行:
```bash
cd /home/mbwcl711_3060/thc1006/tmep/oran-ric-platform
./scripts/start-monitoring-ports.sh
```

看到這個訊息表示成功:
```
 [DONE] Port Forwards Started Successfully

Services available on localhost:
    Grafana:           http://localhost:3000
  📈 Prometheus:        http://localhost:9090
  📡 KPIMON Metrics:    http://localhost:8080/metrics
    Beam API:          http://localhost:8081/api/beam/5/kpi
```

### 步驟 2: 開啟 PORTS 面板

在 VS Code 底部，找到並點擊 **PORTS** 標籤:

```
┌────────────────────────────────────────────┐
│  ┌──────┬──────┬──────────┬───────┬──────┐│
│  │TERMINAL│OUTPUT│ PROBLEMS │ PORTS │DEBUG ││
│  └──────┴──────┴──────────┴───────┴──────┘│
│                              ↑             │
│                        點擊這個標籤         │
└────────────────────────────────────────────┘
```

你會看到所有轉送的 ports:
```
PORTS
───────────────────────────────────────────
 Port    Local Address    Running Process
───────────────────────────────────────────
 3000    localhost:3000   kubectl          [ ]
 8080    localhost:8080   kubectl          [ ]
 8081    localhost:8081   kubectl          [ ]
 9090    localhost:9090   kubectl          [ ]
───────────────────────────────────────────
```

### 步驟 3: 開啟監控服務

點擊 port 右側的 **  圖示**，VS Code 會在本地瀏覽器開啟服務！

或直接在瀏覽器輸入:
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **KPIMON Metrics**: http://localhost:8080/metrics
- **Beam API**: http://localhost:8081/api/beam/5/kpi

---

## 📖 完整說明

### Port Forwarding 是什麼?

Port Forwarding 讓你可以在**本地電腦瀏覽器**存取**遠端 Kubernetes 叢集**的服務，無需連線到實驗室區網。

#### 運作原理

```
┌─────────────┐         SSH Tunnel        ┌──────────────┐         kubectl        ┌─────────────┐
│ 你的本地電腦 │ ◄────────────────────────► │ 遠端實驗室機器 │ ◄───────────────────► │ Kubernetes  │
│             │                             │              │                        │   叢集      │
│  瀏覽器      │                             │ port-forward │                        │             │
│localhost:3000│                             │    :3000     │                        │ Grafana:80  │
└─────────────┘                             └──────────────┘                        └─────────────┘
      ↑                                                                                    ↑
      └────────────────────── VS Code 自動建立 SSH Tunnel ────────────────────────────────┘
```

**流程:**
1. 遠端機器執行 `kubectl port-forward` → Grafana port 80 轉發到遠端 localhost:3000
2. VS Code 偵測到遠端 localhost:3000 有服務
3. VS Code 自動建立 SSH tunnel → 將遠端 localhost:3000 轉發到本地 localhost:3000
4. 你在本地瀏覽器開啟 `http://localhost:3000` → 透過 SSH tunnel 連到遠端 → 連到 Kubernetes Grafana

**結果**: 不需要連到實驗室區網，就可以看到所有監控畫面！ [DONE]

### 如何啟動 Port Forwarding

#### 自動啟動 (推薦)

使用提供的腳本:
```bash
./scripts/start-monitoring-ports.sh
```

這個腳本會:
1. 停止舊的 port-forward processes
2. 啟動 4 個服務的 port forwarding
3. 在背景持續運行
4. 輸出 process IDs 和 log 檔案位置

#### 手動啟動

如果需要手動控制:
```bash
# Grafana
kubectl port-forward -n ricplt svc/oran-grafana 3000:80 &

# Prometheus
kubectl port-forward -n ricplt svc/r4-infrastructure-prometheus-server 9090:80 &

# KPIMON Metrics
kubectl port-forward -n ricxapp svc/kpimon 8080:8080 &

# Beam API
kubectl port-forward -n ricxapp svc/kpimon 8081:8081 &
```

#### 使用 tmux 保持在背景

如果關閉 Terminal 後 port forwards 會停止，使用 tmux:
```bash
# 建立 tmux session
tmux new -s monitoring

# 在 tmux 中執行
./scripts/start-monitoring-ports.sh

# 按 Ctrl+B 然後按 D 離開 (port forwards 繼續執行)

# 稍後回到 tmux
tmux attach -t monitoring
```

### VS Code PORTS 面板使用

#### 手動新增 Port

如果 PORTS 面板沒有自動偵測:
1. 在 PORTS 面板點擊 **"+"** (新增 port)
2. 輸入: `3000`
3. 按 Enter
4. VS Code 會自動建立 SSH tunnel

#### Port 狀態指示

- **  綠色**: Port forwarding 正常運行
- ** [WARN] 黃色**: Port 有問題（例如 port already in use）
- **  紅色**: Port forwarding 失敗

#### 停止 Port Forwarding

**方法 1**: 在 PORTS 面板右鍵點擊 port → 選擇 "Stop Port Forwarding"

**方法 2**: 在 Terminal 執行:
```bash
# 停止所有 kubectl port-forward
pkill -f "kubectl port-forward"

# 或停止特定 PID
kill <PID>
```

---

##   服務詳細分析

### 1. Grafana (Port 3000)  

**服務類型**: Web 視覺化監控平台

**存取方式**: http://localhost:3000

**登入資訊**:
- Username: `admin`
- Password: 查詢方式
  ```bash
  kubectl get secret -n ricplt oran-grafana -o jsonpath='{.data.admin-password}' | base64 -d && echo ""
  ```
  或直接嘗試: `admin`

**你會看到什麼**:
- 🎨 登入頁面: Username/Password 輸入框
-   Dashboard 列表: 所有已建立的監控 dashboard
- 📈 即時圖表: KPIMON、E2 Simulator、xApps 的即時資料
-   查詢介面: 可以自訂 Prometheus 查詢

**Dashboard 內容**:
- CPU/Memory 使用率圖表
- RSRP/RSRQ/SINR 訊號品質趨勢
- Throughput (上下行吞吐量) 圖表
- E2 訊息統計 (成功/失敗數量)
- xApps 健康狀態
- Pod 重啟次數

**如何使用**:
1. 開啟 http://localhost:3000
2. 登入 (admin/admin 或查詢到的密碼)
3. 左側選單 → Dashboards → 搜尋 "KPIMON"
4. 即時查看監控圖表

**技術細節**:
- Frontend: React/Angular (JavaScript)
- Backend: Go
- 資料來源: Prometheus, InfluxDB
- 圖表庫: D3.js, Plotly

---

### 2. Prometheus (Port 9090) 📈

**服務類型**: Metrics 資料庫 + 查詢引擎 + 視覺化介面

**存取方式**: http://localhost:9090

**你會看到什麼**:
-   查詢介面: 輸入 PromQL 查詢語句
-   即時圖表: 將查詢結果視覺化
-   Targets 頁面: 所有被監控的目標 (KPIMON, E2Term, etc.)
-  [WARN] Alerts 頁面: 告警規則與狀態
-   Configuration: Prometheus 設定檔

**儲存的 Metrics 範例**:
```promql
# KPIMON 相關
kpimon_e2_messages_received_total{app="kpimon"}
kpimon_rsrp_dbm{cell_id="cell_001", beam_id="5"}
kpimon_throughput_mbps{direction="downlink"}

# Pod 資源使用
container_cpu_usage_seconds_total{namespace="ricxapp"}
container_memory_working_set_bytes{pod="kpimon-xxx"}

# Kubernetes 系統
kubelet_running_pods{node="worker-1"}
apiserver_request_duration_seconds_bucket
```

**如何查詢**:
1. 開啟 http://localhost:9090
2. 在 "Expression" 欄位輸入: `kpimon_rsrp_dbm`
3. 點擊 "Execute"
4. 切換到 "Graph" 標籤查看趨勢圖

**常用查詢範例**:
```promql
# 查詢 Beam 5 的平均 RSRP (最近 5 分鐘)
avg_over_time(kpimon_rsrp_dbm{beam_id="5"}[5m])

# 查詢所有 beam 的 throughput 總和
sum(kpimon_throughput_mbps) by (beam_id)

# 查詢 KPIMON pod 的 CPU 使用率
rate(container_cpu_usage_seconds_total{pod=~"kpimon.*"}[1m])

# 查詢 E2 訊息接收總數
kpimon_e2_messages_received_total
```

---

### 3. KPIMON Metrics (Port 8080) 📡

**服務類型**: Prometheus Exporter (原始 metrics 端點)

**存取方式**: http://localhost:8080/metrics

**你會看到什麼**:
-   純文字格式: Prometheus metrics 格式
- 🔢 即時數值: 所有 KPIMON 收集的 KPI 數值

**實際內容範例**:
```prometheus
# HELP kpimon_e2_messages_received_total Total E2 messages received
# TYPE kpimon_e2_messages_received_total counter
kpimon_e2_messages_received_total{message_type="indication"} 1543.0

# HELP kpimon_rsrp_dbm RSRP signal strength in dBm
# TYPE kpimon_rsrp_dbm gauge
kpimon_rsrp_dbm{cell_id="cell_001",ue_id="ue_005",beam_id="5"} -86.72
kpimon_rsrp_dbm{cell_id="cell_002",ue_id="ue_012",beam_id="2"} -102.40

# HELP kpimon_throughput_mbps Throughput in Mbps
# TYPE kpimon_throughput_mbps gauge
kpimon_throughput_mbps{direction="downlink",cell_id="cell_001"} 75.01
kpimon_throughput_mbps{direction="uplink",cell_id="cell_001"} 15.28

# HELP python_gc_objects_collected_total Objects collected during gc
# TYPE python_gc_objects_collected_total counter
python_gc_objects_collected_total{generation="0"} 2160.0
```

**如何使用**:
1. 開啟 http://localhost:8080/metrics
2. 瀏覽器會顯示純文字 metrics
3. 可以搜尋特定 metric (Ctrl+F)
4. Prometheus 會定期抓取這個端點的資料

**這個端點的作用**:
- Prometheus 每 15 秒抓取一次
- 提供即時的 KPI 數值
- 用於檢查 KPIMON 是否正常運作
- Debug 時查看原始 metrics

---

### 4. Beam API (Port 8081)  

**服務類型**: RESTful API (Flask Web Server)

**存取方式**: http://localhost:8081/api/beam/{beam_id}/kpi

**API 端點**:

1. **Health Check**
   ```
   GET http://localhost:8081/health/alive

   Response:
   {"status": "alive"}
   ```

2. **查詢 Beam KPI** 
   ```
   GET http://localhost:8081/api/beam/{beam_id}/kpi?kpi_type={type}

   範例:
   http://localhost:8081/api/beam/5/kpi?kpi_type=all
   ```

3. **Time Series 資料**
   ```
   GET http://localhost:8081/api/beam/{beam_id}/kpi/timeseries

   範例:
   http://localhost:8081/api/beam/5/kpi/timeseries?kpi_type=rsrp&interval=30s&limit=10
   ```

**支援的 KPI 類型**:
- `all` - 所有 KPI
- `rsrp` - Reference Signal Received Power (參考訊號接收功率)
- `rsrq` - Reference Signal Received Quality (參考訊號接收品質)
- `sinr` - Signal-to-Interference-plus-Noise Ratio (訊號干擾雜訊比)
- `throughput` - 上下行吞吐量
- `packet_loss` - 封包遺失率
- `resource_util` - 資源使用率

**如何使用**:

方法 1: 瀏覽器直接輸入
```
http://localhost:8081/api/beam/5/kpi?kpi_type=all
```

方法 2: curl 命令
```bash
curl -s "http://localhost:8081/api/beam/5/kpi?kpi_type=all" | python3 -m json.tool
```

**詳細使用說明請參考**: [Beam KPI 查詢完整指南](BEAM_KPI_COMPLETE_GUIDE.md)

---

##   完整數據流向

```
┌─────────────────────────────────────────────────────────────────┐
│ 本地電腦 (你的瀏覽器)                                            │
│                                                                  │
│  http://localhost:3000  ← Grafana 監控儀表板                    │
│  http://localhost:9090  ← Prometheus 查詢介面                   │
│  http://localhost:8080  ← KPIMON Metrics (原始數據)             │
│  http://localhost:8081  ← Beam API (輸入 Beam ID 查詢)        │
│                                                                  │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   │ SSH Tunnel (由 VS Code 建立)
                   │ 加密連線，安全傳輸
                   ↓
┌─────────────────────────────────────────────────────────────────┐
│ 遠端實驗室機器 (SSH 連線目標)                                    │
│                                                                  │
│  localhost:3000 ← kubectl port-forward (Grafana)                │
│  localhost:9090 ← kubectl port-forward (Prometheus)             │
│  localhost:8080 ← kubectl port-forward (KPIMON Metrics)         │
│  localhost:8081 ← kubectl port-forward (Beam API)               │
│                                                                  │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   │ Kubernetes Network (ClusterIP)
                   │ 叢集內部網路
                   ↓
┌─────────────────────────────────────────────────────────────────┐
│ Kubernetes Cluster (O-RAN RIC Platform)                         │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ ricplt namespace                                         │  │
│  │                                                           │  │
│  │  [Grafana Pod:3000] ← Dashboard 視覺化                   │  │
│  │       ↓ 查詢                                              │  │
│  │  [Prometheus Pod:9090] ← Metrics 儲存/查詢               │  │
│  │       ↓ 抓取                                              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ ricxapp namespace                                        │  │
│  │                                                           │  │
│  │  [KPIMON Pod]                                            │  │
│  │    ├─ Port 8080: /metrics ← Prometheus 格式 metrics      │  │
│  │    └─ Port 8081: Beam API ← 處理 Beam ID 查詢         │  │
│  │         ↓ 讀取                                            │  │
│  │  [Redis] ← 儲存 beam-indexed KPI 資料                    │  │
│  │         ↑ 寫入                                            │  │
│  │  [E2 Simulator] ← 產生 beam_id 的 KPI 資料              │  │
│  │                                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

##   故障排除

###  [FAIL] 瀏覽器顯示 "無法連線"

**檢查 port forwards 是否在執行:**
```bash
ps aux | grep "kubectl port-forward"
```

**應該看到 4 個 process:**
```
kubectl port-forward -n ricplt svc/oran-grafana 3000:80
kubectl port-forward -n ricplt svc/r4-infrastructure-prometheus-server 9090:80
kubectl port-forward -n ricxapp svc/kpimon 8080:8080
kubectl port-forward -n ricxapp svc/kpimon 8081:8081
```

**如果沒有，重新執行:**
```bash
./scripts/start-monitoring-ports.sh
```

---

###  [FAIL] Port already in use

**錯誤訊息:**
```
Error listen tcp4 127.0.0.1:3000: bind: address already in use
```

**解決方案:**
```bash
# 方法 1: 停止所有 port forwards 再重啟
pkill -f "kubectl port-forward"
sleep 2
./scripts/start-monitoring-ports.sh

# 方法 2: 找出佔用 port 的 process
lsof -i :3000
kill <PID>
```

---

###  [FAIL] VS Code PORTS 面板沒有顯示 ports

**解決方案 1: 手動新增**
1. 在 PORTS 面板點擊 **"+"** (新增 port)
2. 輸入: `3000`
3. 按 Enter
4. 在瀏覽器開啟 http://localhost:3000

**解決方案 2: 重新整理 PORTS 面板**
1. 右鍵點擊 PORTS 面板
2. 選擇 "Refresh"

**解決方案 3: 重啟 VS Code**
關閉並重新開啟 VS Code，port forwards 會自動重新偵測

---

###  [FAIL] Grafana 無法登入

**常見問題:**
- Username/Password 錯誤
- Grafana pod 未就緒

**解決方案:**
```bash
# 檢查 Grafana pod 狀態
kubectl get pods -n ricplt -l app.kubernetes.io/name=grafana

# 查詢正確的密碼
kubectl get secret -n ricplt oran-grafana -o jsonpath='{.data.admin-password}' | base64 -d && echo ""

# 如果 pod 未就緒，查看 logs
kubectl logs -n ricplt $(kubectl get pods -n ricplt -l app.kubernetes.io/name=grafana -o jsonpath='{.items[0].metadata.name}')
```

---

###  [FAIL] Prometheus 查詢沒有資料

**常見問題:**
- KPIMON 還沒開始收集資料
- Prometheus 還沒抓取到 metrics

**解決方案:**
```bash
# 檢查 KPIMON pod 狀態
kubectl get pods -n ricxapp -l app=kpimon

# 檢查 KPIMON metrics endpoint
curl http://localhost:8080/metrics | grep kpimon

# 在 Prometheus UI 查看 Targets 狀態
# http://localhost:9090/targets
# 確認 KPIMON target 為 UP 狀態
```

---

###  [FAIL] 關閉 Terminal 後 port forwards 停止

**解決方案: 使用 tmux**
```bash
# 安裝 tmux (如果沒有)
sudo apt-get install tmux

# 建立 tmux session
tmux new -s monitoring

# 在 tmux 中執行
./scripts/start-monitoring-ports.sh

# 離開 tmux (port forwards 繼續執行)
# 按 Ctrl+B 然後按 D

# 稍後回到 tmux
tmux attach -t monitoring

# 列出所有 tmux sessions
tmux ls

# 結束 tmux session
tmux kill-session -t monitoring
```

---

##   相關文件

- **Beam KPI 查詢指南**: [BEAM_KPI_COMPLETE_GUIDE.md](BEAM_KPI_COMPLETE_GUIDE.md)
- **Port Forward 腳本**: `/scripts/start-monitoring-ports.sh`
- **Grafana/Prometheus 設定**: `GRAFANA_PROMETHEUS_SETUP_GUIDE.md`

---

##  [DONE] 驗證檢查清單

完成設定後，確認以下項目:

- [ ] `./scripts/start-monitoring-ports.sh` 執行成功
- [ ] VS Code PORTS 面板顯示 4 個 ports (3000, 8080, 8081, 9090)
- [ ] http://localhost:3000 開啟 Grafana 登入頁面
- [ ] http://localhost:9090 開啟 Prometheus 查詢介面
- [ ] http://localhost:8080/metrics 顯示 metrics 資料
- [ ] http://localhost:8081/health/alive 回應 `{"status":"alive"}`
- [ ] Grafana 可以成功登入
- [ ] Prometheus 可以查詢到 `kpimon_rsrp_dbm` metrics
- [ ] 不需要連線到實驗室區網即可存取所有服務

---

**建立日期**: 2025-11-19
**最後測試**: 2025-11-19
**狀態**:  [DONE] 已驗證運行正常
**適用版本**: O-RAN RIC Platform v1.0.2-beam
