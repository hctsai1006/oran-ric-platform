# RMR 錯誤分析報告

**日期**: 2025-11-19
**系統**: O-RAN RIC Platform (J-Release)
**問題**: Traffic Steering xApp 發送 RMR 消息失敗

---

## 🔴 錯誤現象

### Traffic Steering 日誌錯誤
```json
{"ts": 1763518904426, "crit": "ERROR", "id": "traffic_steering_xapp",
 "msg": "Failed to send message type 30000"}
{"ts": 1763518904426, "crit": "ERROR", "id": "traffic_steering_xapp",
 "msg": "Failed to send message type 40000"}
```

### 發生時機
- **觸發條件**: Traffic Steering 決定觸發 UE 換手 (Handover)
- **發送對象**: 嘗試透過 RMR 發送給其他 xApps
- **錯誤頻率**: 每次 handover 決策都失敗

---

## 🔍 根本原因分析

### 1. RTMgr 配置問題 ⚠️

#### RTMgr 錯誤日誌
```json
{"ts":1763519592328, "crit":"ERROR", "id":"rtmgr",
 "msg":"Platform component not found: E2 Termination List"}
```

**問題說明**:
- RTMgr 無法獲取 E2 Termination 列表
- 導致無法為 E2Term 建立路由
- E2Term 未註冊到 RTMgr 的服務發現機制

#### RTMgr PlatformComponents 配置
```yaml
PlatformComponents:
  - name: SUBMAN
    fqdn: service-ricplt-submgr-rmr.ricplt
    port: 4560
  - name: E2MAN
    fqdn: service-ricplt-e2mgr-rmr.ricplt
    port: 3801
  - name: A1MEDIATOR
    fqdn: service-ricplt-a1mediator-rmr.ricplt
    port: 4562
```

**❌ 問題**: 缺少 E2TERM 組件定義！

**✅ 應該要有**:
```yaml
  - name: E2TERM
    fqdn: service-ricplt-e2term-rmr-alpha.ricplt
    port: 38000
```

---

### 2. 消息類型路由缺失 ⚠️

#### 已定義的消息類型
從 RTMgr 配置可以看到 **30000** 和相關消息已定義：
```yaml
messagetypes:
  - "TS_UE_LIST=30000"           # ✅ 已定義
  - "TS_QOE_PRED_REQ=30001"      # ✅ 已定義
  - "TS_QOE_PREDICTION=30002"    # ✅ 已定義
  - "TS_ANOMALY_UPDATE=30003"    # ✅ 已定義
  - "TS_ANOMALY_ACK=30004"       # ✅ 已定義
```

**問題**: 消息類型 40000 **未定義**
- 在 `messagetypes` 列表中找不到 40000
- Traffic Steering 發送了一個未註冊的消息類型

#### PlatformRoutes 配置
```yaml
PlatformRoutes:
  # 只有這些消息類型有路由規則
  - RIC_SUB_REQ (12010)
  - RIC_SUB_RESP (12011)
  - RIC_E2_SETUP_REQ (12001)
  - A1_POLICY_QUERY (20012)
  # ... 其他 E2, A1 消息
```

**❌ 問題**: **沒有 30000 系列消息的路由規則**！

**✅ 應該要有**:
```yaml
PlatformRoutes:
  # Traffic Steering 相關路由
  - messagetype: 'TS_UE_LIST'
    senderendpoint: ''
    subscriptionid: -1
    endpoint: 'TRAFFIC_STEERING'  # 或其他目標 xApp
    meid: ''
  - messagetype: 'TS_QOE_PRED_REQ'
    senderendpoint: 'TRAFFIC_STEERING'
    subscriptionid: -1
    endpoint: 'QOE_PREDICTOR'
    meid: ''
  # ... 其他路由
```

---

### 3. xApp 註冊問題 🔍

#### RTMgr 獲取 xApp 列表的配置
```yaml
XMURL: "http://service-ricplt-appmgr-http:8080/ric/v1/xapps"
```

RTMgr 會定期向 AppMgr 查詢已部署的 xApps，但從日誌看：
```
Update Routes to Endpoint: service-ricplt-submgr-rmr.ricplt:4560 successful
Update Routes to Endpoint: service-ricplt-e2mgr-rmr.ricplt:3801 successful
Update Routes to Endpoint: service-ricplt-a1mediator-rmr.ricplt:4562 successful
```

**❌ 問題**: 沒有看到任何 **xApp 的路由更新**！
- Traffic Steering 可能沒有正確註冊到 AppMgr
- 或者 AppMgr 沒有向 RTMgr 報告 xApp 列表

---

## 📊 完整錯誤鏈

```
1. Traffic Steering 決定執行 Handover
       ↓
2. 嘗試發送 RMR 消息 (type 30000, 40000)
       ↓
3. RMR 庫查詢路由表 (由 RTMgr 提供)
       ↓
4. 路由表中找不到 30000/40000 的路由
       ↓
5. 發送失敗 → ERROR: Failed to send message type 30000
```

**為什麼路由表中沒有這些路由？**
```
RTMgr 無法生成完整路由表
    ↓
原因 1: E2Term 未註冊 (PlatformComponents 缺失)
原因 2: xApps 未註冊到路由系統
原因 3: 自定義消息類型 (30000系列) 沒有配置路由規則
```

---

## 🔧 解決方案

### 方案 1: 修復 RTMgr 配置 (推薦) ✅

#### Step 1: 添加 E2Term 到 PlatformComponents

```bash
# 編輯 RTMgr ConfigMap
kubectl edit configmap configmap-ricplt-rtmgr-rtmgrcfg -n ricplt
```

在 `PlatformComponents` 部分添加：
```yaml
  - name: "E2TERM"
    fqdn: "service-ricplt-e2term-rmr-alpha.ricplt"
    port: 38000
```

#### Step 2: 添加 Traffic Steering 消息路由

在 `PlatformRoutes` 部分添加：
```yaml
  # Traffic Steering Routes
  - messagetype: 'TS_UE_LIST'
    senderendpoint: 'TRAFFIC_STEERING'
    subscriptionid: -1
    endpoint: 'QOE_PREDICTOR'  # 目標 xApp
    meid: ''

  - messagetype: 'TS_QOE_PRED_REQ'
    senderendpoint: 'TRAFFIC_STEERING'
    subscriptionid: -1
    endpoint: 'QOE_PREDICTOR'
    meid: ''

  - messagetype: 'TS_QOE_PREDICTION'
    senderendpoint: 'QOE_PREDICTOR'
    subscriptionid: -1
    endpoint: 'TRAFFIC_STEERING'
    meid: ''

  - messagetype: 'TS_ANOMALY_UPDATE'
    senderendpoint: 'TRAFFIC_STEERING'
    subscriptionid: -1
    endpoint: 'KPIMON'  # 或其他監控 xApp
    meid: ''
```

#### Step 3: 定義消息類型 40000

在 `messagetypes` 部分添加：
```yaml
  - "TS_HANDOVER_CMD=40000"  # 或其他適當的名稱
```

#### Step 4: 重啟 RTMgr

```bash
kubectl delete pod -n ricplt -l app=ricplt-rtmgr
```

RTMgr 會自動重啟並載入新配置。

---

### 方案 2: 使用 HTTP 替代 RMR (臨時方案) ⚠️

如果 RMR 配置複雜，可以暫時使用 HTTP 通訊：

```python
# traffic_steering/src/main.py

# 替代 RMR 發送
def send_handover_command(ue_id, target_cell):
    # 使用 HTTP REST API 替代 RMR
    try:
        response = requests.post(
            'http://qoe-predictor:8090/api/handover',
            json={
                'ue_id': ue_id,
                'target_cell': target_cell
            }
        )
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to send handover via HTTP: {e}")
        return False
```

**優點**: 立即可用，不需修改 RTMgr
**缺點**: 不符合 O-RAN 標準，延遲較高

---

### 方案 3: 檢查 xApp 註冊狀態 🔍

```bash
# 檢查 AppMgr 中的 xApp 列表
kubectl exec -n ricplt deployment/deployment-ricplt-appmgr -- \
  curl -s http://localhost:8080/ric/v1/xapps | jq '.'

# 預期輸出應該包含 Traffic Steering
# 如果沒有，需要通過 AppMgr 部署 xApp
```

如果 Traffic Steering 沒有在 AppMgr 中註冊：

```bash
# 方式 1: 通過 Helm 部署 (標準方式)
helm install traffic-steering ./xapps/traffic-steering/helm

# 方式 2: 通過 AppMgr API 註冊
curl -X POST http://appmgr:8080/ric/v1/xapps \
  -H "Content-Type: application/json" \
  -d '{
    "name": "traffic-steering",
    "namespace": "ricxapp",
    "rmr": {
      "data_port": 4580,
      "route_port": 4581
    }
  }'
```

---

## 🎯 驗證步驟

### 1. 驗證 RTMgr 配置

```bash
# 檢查 E2Term 是否已添加
kubectl get configmap configmap-ricplt-rtmgr-rtmgrcfg -n ricplt -o yaml | grep E2TERM

# 檢查路由規則
kubectl get configmap configmap-ricplt-rtmgr-rtmgrcfg -n ricplt -o yaml | grep TS_UE_LIST
```

### 2. 檢查 RTMgr 日誌

```bash
kubectl logs -n ricplt deployment/deployment-ricplt-rtmgr --tail=50

# 應該看到：
# ✅ "Platform component not found: E2 Termination List" 錯誤消失
# ✅ "Update Routes to Endpoint: service-ricplt-e2term-rmr-alpha" 出現
```

### 3. 測試 Traffic Steering

```bash
# 查看 Traffic Steering 日誌
kubectl logs -n ricxapp deployment/traffic-steering --tail=50

# 應該看到：
# ✅ "Failed to send message type 30000" 錯誤消失
# ✅ "Handover command sent successfully" (或類似成功消息)
```

### 4. 驗證路由表

```bash
# 從 RTMgr 獲取當前路由表
kubectl exec -n ricplt deployment/deployment-ricplt-rtmgr -- \
  cat /db/rt.json | jq '.'

# 檢查是否包含 30000 消息的路由
```

---

## 📚 相關技術背景

### RMR (RIC Message Router) 簡介

**RMR** 是 O-RAN SC 開發的高性能消息路由庫，用於 RIC Platform 內部通訊。

#### 核心概念

1. **Message Type**: 每個消息有唯一的數字 ID
   - 範圍: 通常 10000-50000
   - 例如: `RIC_INDICATION=12050`, `TS_UE_LIST=30000`

2. **Routing Table**: 由 RTMgr 動態生成和分發
   - 格式: Message Type → 目標服務 (FQDN:Port)
   - 每個組件定期從 RTMgr 獲取更新

3. **Sender Endpoint / Receiver Endpoint**:
   - Sender: 消息發送者（通常是 xApp）
   - Receiver: 消息接收者（可以是平台組件或其他 xApp）

#### RMR 工作流程

```
┌─────────────────┐
│ Traffic Steering│ (發送 msg type 30000)
└────────┬────────┘
         │ 1. 調用 rmr_send(30000)
         ↓
┌─────────────────┐
│ RMR Library     │ (查詢本地路由表)
└────────┬────────┘
         │ 2. 查找 30000 → QoE Predictor:4590
         ↓
┌─────────────────┐
│  RMR Transport  │ (TCP/UDP)
└────────┬────────┘
         │ 3. 發送到 10.42.x.x:4590
         ↓
┌─────────────────┐
│ QoE Predictor   │ (接收消息)
└─────────────────┘
         │ 4. 處理消息
         ↓
     (Optional) 回覆消息
```

#### 路由表示例

```json
{
  "routes": [
    {
      "message_type": 30000,
      "sender": "traffic-steering.ricxapp",
      "target": "qoe-predictor.ricxapp:4590"
    },
    {
      "message_type": 12050,
      "sender": "e2term-alpha.ricplt",
      "target": "kpimon.ricxapp:4560"
    }
  ]
}
```

---

## ⚠️ 當前架構的特殊性

### 混合架構 (Parallel Change)

你的系統正處於**平行變更階段**：

```
┌─────────────────────────────────┐
│   舊架構 (HTTP)                 │
│   ────────────                  │
│   E2 Sim → xApps                │
│   (HTTP POST /e2/indication)    │
└─────────────────────────────────┘
                ↕
        (同時存在)
                ↕
┌─────────────────────────────────┐
│   新架構 (RMR)                  │
│   ───────────                   │
│   E2 Sim → E2Term → RTMgr       │
│   → xApps (RMR messages)        │
└─────────────────────────────────┘
```

**這就是為什麼**:
- ✅ HTTP 通訊正常工作 (E2 Simulator → xApps)
- ⚠️ RMR 通訊失敗 (xApps 之間的 RMR 消息)

**Traffic Steering 錯誤的真正含義**:
> "我已經準備好使用 RMR 了，但 RMR 路由還沒配置好！"

---

## 📖 建議閱讀

### 相關文檔
- [RTMgr 配置指南](https://docs.o-ran-sc.org/projects/o-ran-sc-ric-plt-rtmgr/)
- [RMR 用戶手冊](https://docs.o-ran-sc.org/projects/o-ran-sc-ric-plt-lib-rmr/)
- [O-RAN E2 Interface Specification](https://www.o-ran.org/specifications)

### 類似問題
- [JIRA: RTMgr cannot discover E2Term](https://jira.o-ran-sc.org/)
- [GitHub Issue: RMR routing table not updating](https://github.com/o-ran-sc/)

---

## 🎯 總結

### RMR 錯誤的三個層次

| 層次 | 問題 | 影響 | 修復優先級 |
|------|------|------|-----------|
| **Layer 1: 消息定義** | 40000 未定義 | 無法發送該消息 | P2 (可選) |
| **Layer 2: 路由配置** | 30000 無路由規則 | 消息無法路由 | **P0 (必須)** |
| **Layer 3: 組件註冊** | E2Term 未註冊 | RTMgr 無法生成完整路由 | **P0 (必須)** |

### 快速修復 (5分鐘)

```bash
# 1. 編輯 RTMgr ConfigMap
kubectl edit configmap configmap-ricplt-rtmgr-rtmgrcfg -n ricplt

# 2. 添加 E2TERM 到 PlatformComponents (見上方方案 1)

# 3. 重啟 RTMgr
kubectl delete pod -n ricplt -l app=ricplt-rtmgr

# 4. 等待 30 秒後檢查日誌
kubectl logs -n ricplt deployment/deployment-ricplt-rtmgr --tail=20

# 5. 測試 Traffic Steering
kubectl logs -n ricxapp deployment/traffic-steering --follow
```

### 長期改進

1. ✅ 完成 xApp RMR 遷移 (移除 HTTP fallback)
2. ✅ 標準化消息類型定義 (建立 message registry)
3. ✅ 自動化 RTMgr 配置生成
4. ✅ 添加路由健康檢查和監控

---

**報告作者**: Claude Code Analysis
**最後更新**: 2025-11-19 02:35:00 UTC
**報告版本**: 1.0
