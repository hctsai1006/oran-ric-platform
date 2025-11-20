# O-RAN SC Release J - 雙路徑通訊實現指南

## 概述

本文檔描述了為 O-RAN RIC Platform 實現的雙路徑冗餘通訊機制（RMR + HTTP）。

### 設計原則

根據 **O-RAN SC Release J** 最佳實踐，實現以下功能：

1. **RMR 作為主要通訊路徑**：用於 RIC 平台內部所有組件通訊
   - E2 Term ↔ xApp
   - xApp ↔ xApp
   - xApp ↔ Platform Components (A1 Mediator, SubMgr, etc.)

2. **HTTP 作為備用通訊路徑**：
   - 當 RMR 斷線時自動切換
   - 用於對外服務（如數據庫、監控系統）
   - 保持健康檢查端點可用

3. **智能故障切換機制**：
   - 基於連續失敗次數的故障檢測
   - 帶有遲滯（hysteresis）的故障恢復
   - 全面的日誌記錄和監控

---

## 架構組件

### 1. DualPathMessenger 核心類

位置：`/xapps/common/dual_path_messenger.py`

#### 關鍵功能

- **雙路徑管理**：統一管理 RMR 和 HTTP 通訊
- **健康監控**：持續檢查兩條路徑的健康狀態
- **自動故障切換**：檢測到故障時自動切換到備用路徑
- **路徑恢復**：主要路徑恢復後自動切換回去
- **Prometheus 監控**：提供詳細的指標數據

#### 配置參數

```json
{
  "dual_path": {
    "health_check_interval": 10,     // 健康檢查間隔（秒）
    "rmr_ready_timeout": 5,          // RMR 初始化超時（秒）
    "http_timeout": 5,               // HTTP 請求超時（秒）
    "failover_threshold": 3,         // 觸發故障切換的連續失敗次數
    "recovery_threshold": 5,         // 恢復主要路徑的連續成功次數
    "max_retry_attempts": 2,         // 最大重試次數
    "retry_delay": 0.5               // 重試延遲（秒）
  }
}
```

---

## 實現步驟

### 步驟 1：添加依賴

在 xApp 的 Python 文件中添加：

```python
import sys
import os

# Add common library path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../common'))

from dual_path_messenger import DualPathMessenger, EndpointConfig, CommunicationPath
```

### 步驟 2：初始化 DualPathMessenger

替換原有的 RMRXapp 初始化：

```python
# 原有方式（僅 RMR）
self.xapp = RMRXapp(
    self._handle_message,
    rmr_port=4560,
    use_fake_sdl=False
)

# 新方式（雙路徑）
self.messenger = DualPathMessenger(
    xapp_name="your-xapp-name",
    rmr_port=self.config.get('rmr_port', 4560),
    message_handler=self._handle_message_internal,
    config=self.config.get('dual_path', {})
)
```

### 步驟 3：註冊 HTTP Fallback 端點

為其他 xApp 和平台組件註冊 HTTP 端點：

```python
def _register_endpoints(self):
    """Register HTTP fallback endpoints"""
    # Register peer xApp
    self.messenger.register_endpoint(EndpointConfig(
        service_name="target-xapp",
        namespace="ricxapp",
        http_port=8080,
        rmr_port=4560
    ))

    # Register E2 Term
    self.messenger.register_endpoint(EndpointConfig(
        service_name="service-ricplt-e2term-rmr-alpha",
        namespace="ricplt",
        http_port=38000,
        rmr_port=38000
    ))
```

### 步驟 4：更新消息處理器

修改消息處理器簽名以兼容 DualPathMessenger：

```python
def _handle_message_internal(self, xapp, summary: dict, sbuf):
    """Internal message handler for DualPathMessenger"""
    mtype = summary.get(rmr.RMR_MS_MSG_TYPE, summary.get('message type', 0))

    # Extract payload
    if sbuf:
        payload_bytes = rmr.get_payload(sbuf)
        payload = json.loads(payload_bytes.decode('utf-8'))
    else:
        payload = json.loads(summary.get('payload', '{}'))

    # Process message based on type
    if mtype == RIC_INDICATION:
        self._handle_indication(payload)
    # ... other message types
```

### 步驟 5：使用雙路徑發送消息

更新所有消息發送邏輯：

```python
# 原有方式
self.xapp.rmr_send(payload.encode(), msg_type)

# 新方式（自動故障切換）
self.messenger.send_message(
    msg_type=msg_type,
    payload=payload,
    destination="target-service-name"  # 用於 HTTP fallback
)
```

### 步驟 6：更新健康檢查端點

添加路徑健康狀態到 readiness 檢查：

```python
@app.route('/ric/v1/health/ready', methods=['GET'])
def health_ready():
    health_summary = self.messenger.get_health_summary()
    rmr_healthy = health_summary['rmr']['status'] == 'healthy'
    http_available = health_summary['http']['status'] in ['healthy', 'degraded']

    ready = rmr_healthy or http_available

    return jsonify({
        "status": "ready" if ready else "not_ready",
        "communication_health": health_summary
    }), 200 if ready else 503

@app.route('/ric/v1/health/paths', methods=['GET'])
def health_paths():
    """Detailed communication path health status"""
    return jsonify(self.messenger.get_health_summary()), 200
```

### 步驟 7：更新啟動流程

修改 xApp 啟動邏輯：

```python
def start(self):
    """Start xApp with dual-path communication"""
    logger.info("Starting xApp (Release J - Dual-Path)")
    self.running = True

    # Start Flask API
    flask_thread = Thread(
        target=lambda: self.app.run(host='0.0.0.0', port=http_port)
    )
    flask_thread.daemon = True
    flask_thread.start()

    # Initialize RMR through DualPathMessenger
    rmr_initialized = self.messenger.initialize_rmr(use_fake_sdl=False)

    if not rmr_initialized:
        logger.warning("RMR initialization failed, using HTTP fallback")

    # Start dual-path messenger
    self.messenger.start()

    # Start RMR message loop if available
    if self.messenger.rmr_xapp:
        logger.info("Starting RMR message loop")
        self.messenger.rmr_xapp.run()
    else:
        logger.info("Running in HTTP-only mode")
        while self.running:
            time.sleep(1)
```

---

## 監控和日誌

### Prometheus 指標

DualPathMessenger 提供以下 Prometheus 指標：

```
# 消息發送統計
dual_path_messages_sent_rmr_total{message_type, destination}
dual_path_messages_sent_http_total{message_type, destination}
dual_path_messages_failed_total{message_type, path_type}

# 健康狀態
dual_path_rmr_health_status        # 1=健康, 0=不健康
dual_path_http_health_status       # 1=健康, 0=不健康
dual_path_active_path              # 1=RMR, 0=HTTP

# 故障切換事件
dual_path_failover_events_total{from_path, to_path}

# 消息延遲
dual_path_message_latency_seconds{path_type}
```

### 日誌記錄

所有關鍵事件都會記錄日誌：

- **INFO**：正常操作（消息發送、路徑切換、健康檢查）
- **WARNING**：路徑降級、故障切換觸發
- **ERROR**：消息發送失敗、兩條路徑都不可用

示例日誌輸出：

```
[INFO] DualPathMessenger initialized for xApp: traffic-steering
[INFO] RMR initialized successfully
[INFO] Registered HTTP fallback endpoints
[WARNING] RMR path marked as DOWN
[WARNING] FAILOVER: Switching from RMR to HTTP
[INFO] HTTP path recovered to HEALTHY
[INFO] RMR path fully recovered, switching back to RMR
```

---

## 測試

### 單元測試

測試雙路徑功能：

```python
# Test RMR send
messenger.send_message(
    msg_type=12050,
    payload={"test": "data"},
    force_path=CommunicationPath.RMR
)

# Test HTTP fallback
messenger.send_message(
    msg_type=12050,
    payload={"test": "data"},
    destination="target-service",
    force_path=CommunicationPath.HTTP
)

# Check health
health = messenger.get_health_summary()
assert health['active_path'] in ['rmr', 'http']
```

### 故障切換測試

1. **模擬 RMR 故障**：
   ```bash
   # 停止 RTMgr 服務
   kubectl scale deployment service-ricplt-rtmgr --replicas=0 -n ricplt

   # 觀察日誌
   kubectl logs -f deployment/traffic-steering -n ricxapp | grep FAILOVER
   ```

2. **檢查 Prometheus 指標**：
   ```bash
   curl http://traffic-steering:8081/ric/v1/metrics | grep dual_path
   ```

3. **檢查健康端點**：
   ```bash
   curl http://traffic-steering:8081/ric/v1/health/paths
   ```

---

## 已實現 xApp

### ✅ Traffic Steering xApp

- **位置**：`/xapps/traffic-steering/src/traffic_steering.py`
- **狀態**：完全整合雙路徑通訊
- **功能**：
  - RMR 主要路徑用於 E2 消息和 xApp 間通訊
  - HTTP 備用路徑用於故障恢復
  - 自動故障切換和恢復
  - 完整的健康檢查和監控

### 待實現 xApp

1. **QoE Predictor** (`/xapps/qoe-predictor/src/qoe_predictor.py`)
   - 當前狀態：有基本 RMR 實現
   - 需要：整合 DualPathMessenger

2. **RC-xApp** (`/xapps/rc-xapp/src/ran_control.py`)
   - 當前狀態：有完整 RMR 實現
   - 需要：整合 DualPathMessenger 增強穩定性

3. **KPIMON** (`/xapps/kpimon-go-xapp/src/kpimon.py`)
   - 當前狀態：有完整 RMR 實現
   - 需要：整合 DualPathMessenger 增強穩定性

4. **Federated Learning** (`/xapps/federated-learning/src/federated_learning.py`)
   - 當前狀態：需要檢查
   - 需要：整合 DualPathMessenger

---

## E2 Simulator 更新

E2 Simulator 也需要支持雙路徑發送：

```python
# 添加 RMR 發送功能
def send_via_rmr(self, msg_type, payload):
    """Send indication via RMR"""
    # 實現 RMR 發送邏輯
    pass

# 保留原有的 HTTP 發送
def send_via_http(self, xapp_name, payload):
    """Send indication via HTTP"""
    # 現有的 HTTP POST 邏輯
    pass
```

---

## 最佳實踐

### 1. 消息類型路由

- **RIC 內部消息**（12xxx, 20xxx）：優先使用 RMR
- **外部 API 調用**：使用 HTTP
- **數據庫操作**：使用 HTTP
- **監控指標**：使用 HTTP

### 2. 錯誤處理

```python
success = self.messenger.send_message(
    msg_type=msg_type,
    payload=payload,
    destination="target"
)

if not success:
    logger.error("Message delivery failed via both paths")
    # 實現降級邏輯
    # 例如：緩存消息，稍後重試
```

### 3. 配置管理

在 xApp 配置文件中添加：

```json
{
  "xapp_name": "my-xapp",
  "rmr_port": 4560,
  "http_port": 8080,
  "dual_path": {
    "health_check_interval": 10,
    "failover_threshold": 3,
    "recovery_threshold": 5
  }
}
```

---

## 故障排查

### RMR 無法初始化

**症狀**：
```
[ERROR] Failed to initialize RMR: ...
[WARNING] RMR initialization failed, will rely on HTTP fallback path
```

**解決方法**：
1. 檢查 RMR 路由表：`RMR_SEED_RT` 環境變量
2. 驗證 RTMgr 服務：`kubectl get pods -n ricplt | grep rtmgr`
3. 檢查端口配置：確保 RMR 端口未被占用

### HTTP Fallback 不工作

**症狀**：
```
[ERROR] No endpoint registered for {destination}
```

**解決方法**：
1. 確保已調用 `_register_endpoints()`
2. 檢查 Kubernetes 服務名稱和命名空間
3. 驗證 HTTP 端口配置

### 頻繁故障切換

**症狀**：
```
[WARNING] FAILOVER: Switching from RMR to HTTP
[INFO] RMR path fully recovered, switching back to RMR
(重複出現)
```

**解決方法**：
1. 增加 `failover_threshold` 和 `recovery_threshold`
2. 檢查網絡穩定性
3. 調整健康檢查間隔

---

## 參考文檔

- [O-RAN SC Release J Documentation](https://docs.o-ran-sc.org/en/j-release/)
- [RMR User Guide](https://docs.o-ran-sc.org/projects/o-ran-sc-ric-plt-lib-rmr/en/latest/user-guide.html)
- [xApp Framework Developer Guide](https://docs.o-ran-sc.org/projects/o-ran-sc-ric-plt-xapp-frame-py/en/stable/developer-guide.html)

---

## 版本歷史

- **v1.0.0** (2025-11-20)
  - 初始實現 DualPathMessenger
  - Traffic Steering xApp 完全整合
  - 完整的監控和日誌支持
