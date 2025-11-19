# O-RAN RIC Platform 完整部署指南

**日期**: 2025-11-19
**系統版本**: O-RAN SC J-Release
**部署時間**: ~2-3 小時

---

##   目錄

- [1. 系統概述](#1-系統概述)
- [2. 部署前準備](#2-部署前準備)
- [3. 完整部署步驟](#3-完整部署步驟)
- [4. 驗證與測試](#4-驗證與測試)
- [5. 常見問題](#5-常見問題)

---

## 1. 系統概述

### 1.1 已部署組件清單

我們成功部署了 **17 個 O-RAN RIC Platform 組件**：

#### 基礎設施層 (Infrastructure Layer)
```
 [DONE] Prometheus (監控數據收集)
 [DONE] Grafana (監控視覺化)
 [DONE] Redis Cluster (3 節點，SDL Backend)
 [DONE] DBaaS (Database as a Service，SDL Frontend)
```

#### E2 接口層 (E2 Interface Layer)
```
 [DONE] E2 Term (E2AP 協議終止點)
 [DONE] E2 Manager (E2 連接管理)
 [DONE] Subscription Manager (E2 訂閱管理)
```

#### RMR 路由層 (RMR Routing Layer)
```
 [DONE] Routing Manager (動態路由管理)
```

#### xApp 管理層 (xApp Management)
```
 [DONE] App Manager (xApp 生命週期管理)
 [DONE] Resource Status Manager (資源狀態管理)
```

#### North-Bound 接口 (A1 Interface)
```
 [DONE] A1 Mediator (Non-RT RIC 接口)
```

#### 支援組件 (Supporting Components)
```
 [DONE] O1 Mediator (OAM 接口)
 [DONE] Alarm Manager (告警管理)
 [DONE] Jaeger Adapter (分散式追蹤)
 [DONE] VES Manager (VES 事件管理)
```

#### xApps (5 個)
```
 [DONE] KPIMON (KPI 監控)
 [DONE] Traffic Steering (流量控制)
 [DONE] QoE Predictor (QoE 預測)
 [DONE] RAN Control (RAN 控制)
 [DONE] Federated Learning (聯邦學習)
```

#### E2 Simulator
```
 [DONE] E2 Simulator (模擬 gNodeB)
```

---

## 2. 部署前準備

### 2.1 環境需求

#### 硬體需求
```
CPU: 最少 8 cores (建議 16 cores)
Memory: 最少 16GB RAM (建議 32GB)
Storage: 最少 100GB 可用空間
```

#### 軟體需求
```
OS: Ubuntu 20.04/22.04 或 CentOS 7/8
Kubernetes: v1.24+
Helm: v3.10+
Docker: v20.10+
```

### 2.2 Kubernetes 集群準備

```bash
# 檢查 Kubernetes 版本
kubectl version --short

# 檢查節點狀態
kubectl get nodes

# 檢查可用資源
kubectl top nodes

# 創建命名空間
kubectl create namespace ricplt
kubectl create namespace ricxapp
```

### 2.3 克隆 RIC Platform 代碼

```bash
# 方式 1: 從 O-RAN SC Gerrit (官方)
git clone "https://gerrit.o-ran-sc.org/r/ric-plt/ric-dep"

# 方式 2: 從你的倉庫
git clone https://github.com/hctsai1006/oran-ric-platform.git
cd oran-ric-platform
```

---

## 3. 完整部署步驟

### 部署時間線

我們的實際部署時間線（參考用）：
```
06:07 → Prometheus & Grafana    (監控基礎)
06:14 → Redis Cluster            (SDL backend)
06:19 → DBaaS                    (SDL frontend)
06:41 → E2Term & E2Mgr           (E2 核心)
06:52 → AppMgr                   (xApp 管理)
06:54 → A1 Mediator              (A1 接口)
07:11 → O1, Jaeger, VES          (支援組件)
07:12 → Alarm Manager
07:29 → SubMgr                   (訂閱管理)
07:30 → RTMgr                    (RMR 路由)
07:53 → RSM                      (資源狀態)
```

總時長：約 **1 小時 46 分鐘**

---

### Phase 0: 準備工作

```bash
# 進入 ric-dep 目錄
cd oran-ric-platform/ric-dep

# 設定環境變數
export NAMESPACE_PLT=ricplt
export NAMESPACE_XAPP=ricxapp
export RELEASE_PREFIX=r4
```

---

### Phase 1: 基礎設施部署 (Infrastructure)

#### Step 1.1: 部署 Prometheus

```bash
# 使用 Helm 安裝 Prometheus
helm install ${RELEASE_PREFIX}-infrastructure-prometheus \
  prometheus-community/prometheus \
  --namespace ${NAMESPACE_PLT} \
  --set server.persistentVolume.enabled=true \
  --set server.persistentVolume.size=10Gi \
  --set alertmanager.enabled=true \
  --wait

# 驗證
kubectl get pods -n ${NAMESPACE_PLT} | grep prometheus
# 預期: r4-infrastructure-prometheus-server-xxx Running
```

**部署時間**: ~3-5 分鐘

---

#### Step 1.2: 部署 Grafana

```bash
# 安裝 Grafana
helm install oran-grafana \
  grafana/grafana \
  --namespace ${NAMESPACE_PLT} \
  --set persistence.enabled=true \
  --set persistence.size=5Gi \
  --set adminPassword='admin' \
  --wait

# 獲取 admin 密碼
kubectl get secret -n ${NAMESPACE_PLT} oran-grafana \
  -o jsonpath="{.data.admin-password}" | base64 --decode
```

**部署時間**: ~2-3 分鐘

---

#### Step 1.3: 部署 Redis Cluster

```bash
# 部署 Redis Cluster
helm install ${RELEASE_PREFIX}-redis-cluster \
  ./helm/redis-cluster \
  --namespace ${NAMESPACE_PLT} \
  --wait

# 驗證
kubectl get pods -n ${NAMESPACE_PLT} | grep redis
# 預期: 3 個 redis-cluster pods Running
```

**部署時間**: ~3-5 分鐘

---

#### Step 1.4: 部署 DBaaS

```bash
# 部署 DBaaS (Shared Data Layer)
helm install ${RELEASE_PREFIX}-dbaas \
  ./helm/dbaas \
  --namespace ${NAMESPACE_PLT} \
  --wait

# 驗證
kubectl get svc -n ${NAMESPACE_PLT} | grep dbaas
# 預期: dbaas-tcp service
```

**部署時間**: ~2-3 分鐘

---

### Phase 2: E2 核心組件 (E2 Interface Layer)

#### Step 2.1: 部署 E2 Term

```bash
# 部署 E2 Termination
helm install ${RELEASE_PREFIX}-e2term \
  ./helm/e2term \
  --namespace ${NAMESPACE_PLT} \
  --wait

# 驗證
kubectl get pods -n ${NAMESPACE_PLT} | grep e2term
kubectl get svc -n ${NAMESPACE_PLT} | grep e2term

# 預期服務:
# - service-ricplt-e2term-sctp-alpha (NodePort 32222:36422/SCTP)
# - service-ricplt-e2term-rmr-alpha (ClusterIP, ports 4561, 38000)
```

**部署時間**: ~3-5 分鐘

---

#### Step 2.2: 部署 E2 Manager

```bash
# 部署 E2 Manager
helm install ${RELEASE_PREFIX}-e2mgr \
  ./helm/e2mgr \
  --namespace ${NAMESPACE_PLT} \
  --wait

# 驗證
kubectl get pods -n ${NAMESPACE_PLT} | grep e2mgr
kubectl get svc -n ${NAMESPACE_PLT} | grep e2mgr

# 預期服務:
# - service-ricplt-e2mgr-http (port 3800)
# - service-ricplt-e2mgr-rmr (ports 4561, 3801)
```

**部署時間**: ~2-3 分鐘

---

#### Step 2.3: 部署 Subscription Manager

```bash
# 部署 Subscription Manager
helm install ${RELEASE_PREFIX}-submgr \
  ./helm/submgr \
  --namespace ${NAMESPACE_PLT} \
  --wait

# 驗證
kubectl get pods -n ${NAMESPACE_PLT} | grep submgr
```

**部署時間**: ~2-3 分鐘

---

### Phase 3: RMR 路由層 (RMR Routing)

#### Step 3.1: 部署 Routing Manager

```bash
# 部署 Routing Manager
helm install ${RELEASE_PREFIX}-rtmgr \
  ./helm/rtmgr \
  --namespace ${NAMESPACE_PLT} \
  --wait

# 驗證
kubectl get pods -n ${NAMESPACE_PLT} | grep rtmgr
kubectl logs -n ${NAMESPACE_PLT} deployment/deployment-ricplt-rtmgr --tail=20

# 檢查路由更新
# 預期看到: "Update Routes to Endpoint: ... successful"
```

**部署時間**: ~2-3 分鐘

 [WARN] **重要**: RTMgr 部署後需要配置 E2Term (見 RMR_ERROR_ANALYSIS.md)

---

### Phase 4: xApp 管理層 (xApp Management)

#### Step 4.1: 部署 App Manager

```bash
# 部署 App Manager
helm install ${RELEASE_PREFIX}-appmgr \
  ./helm/appmgr \
  --namespace ${NAMESPACE_PLT} \
  --wait

# 驗證
kubectl get pods -n ${NAMESPACE_PLT} | grep appmgr
curl http://service-ricplt-appmgr-http.${NAMESPACE_PLT}:8080/ric/v1/health/alive
```

**部署時間**: ~2-3 分鐘

---

#### Step 4.2: 部署 Resource Status Manager

```bash
# 部署 RSM
helm install ${RELEASE_PREFIX}-rsm \
  ./helm/rsm \
  --namespace ${NAMESPACE_PLT} \
  --wait
```

**部署時間**: ~2-3 分鐘

---

### Phase 5: North-Bound 接口 (A1 Interface)

#### Step 5.1: 部署 A1 Mediator

```bash
# 部署 A1 Mediator
helm install ${RELEASE_PREFIX}-a1mediator \
  ./helm/a1mediator \
  --namespace ${NAMESPACE_PLT} \
  --wait

# 驗證
kubectl get pods -n ${NAMESPACE_PLT} | grep a1mediator
kubectl get svc -n ${NAMESPACE_PLT} | grep a1mediator

# 健康檢查
curl http://service-ricplt-a1mediator-http.${NAMESPACE_PLT}:10000/a1-p/healthcheck
```

**部署時間**: ~2-3 分鐘

---

### Phase 6: 支援組件 (Supporting Components)

#### Step 6.1: 部署 O1 Mediator

```bash
# 部署 O1 Mediator
helm install ${RELEASE_PREFIX}-o1mediator \
  ./helm/o1mediator \
  --namespace ${NAMESPACE_PLT} \
  --wait
```

**部署時間**: ~2-3 分鐘

**注意**: 可能遇到 ImagePullBackOff (需要配置 image pull secret)

---

#### Step 6.2: 部署 Alarm Manager

```bash
# 部署 Alarm Manager
helm install ${RELEASE_PREFIX}-alarmmanager \
  ./helm/alarmmanager \
  --namespace ${NAMESPACE_PLT} \
  --wait
```

**部署時間**: ~2-3 分鐘

---

#### Step 6.3: 部署 Jaeger Adapter (可選)

```bash
# 部署 Jaeger (分散式追蹤)
helm install ${RELEASE_PREFIX}-jaegeradapter \
  ./helm/jaegeradapter \
  --namespace ${NAMESPACE_PLT} \
  --wait
```

**部署時間**: ~2-3 分鐘

---

#### Step 6.4: 部署 VES Manager (可選)

```bash
# 部署 VES Manager
helm install ${RELEASE_PREFIX}-vespamgr \
  ./helm/vespamgr \
  --namespace ${NAMESPACE_PLT} \
  --wait
```

**部署時間**: ~2-3 分鐘

---

### Phase 7: 部署 xApps

#### Step 7.1: 部署 KPIMON

```bash
# 進入 xApps 目錄
cd ../../xapps/kpimon-go-xapp

# 構建 Docker image
docker build -t localhost:5000/kpimon:latest .
docker push localhost:5000/kpimon:latest

# 部署到 Kubernetes
kubectl apply -f deploy/deployment.yaml

# 驗證
kubectl get pods -n ricxapp | grep kpimon
kubectl logs -n ricxapp deployment/kpimon --tail=50
```

**部署時間**: ~5-10 分鐘

---

#### Step 7.2: 部署其他 xApps

重複相同步驟部署：
- Traffic Steering
- QoE Predictor
- RAN Control
- Federated Learning

```bash
# 範例: Traffic Steering
cd ../traffic-steering
docker build -t localhost:5000/traffic-steering:latest .
docker push localhost:5000/traffic-steering:latest
kubectl apply -f deploy/deployment.yaml
```

**總部署時間**: ~30-40 分鐘 (5 個 xApps)

---

### Phase 8: 部署 E2 Simulator

```bash
cd ../../simulator/e2-simulator

# 構建 image
docker build -t localhost:5000/e2-simulator:latest .
docker push localhost:5000/e2-simulator:latest

# 部署
kubectl apply -f deploy/deployment.yaml

# 驗證
kubectl logs -n ricxapp deployment/e2-simulator --tail=50
# 預期看到: KPI generation logs
```

**部署時間**: ~5 分鐘

---

## 4. 驗證與測試

### 4.1 檢查所有 Pods

```bash
# 檢查 ricplt namespace
kubectl get pods -n ricplt

# 預期: 20 個 pods, 至少 18 個 Running

# 檢查 ricxapp namespace
kubectl get pods -n ricxapp

# 預期: 8 個 pods, 全部 Running
```

### 4.2 檢查服務

```bash
# 列出所有服務
kubectl get svc -n ricplt
kubectl get svc -n ricxapp

# 檢查 E2Term SCTP port
kubectl get svc -n ricplt service-ricplt-e2term-sctp-alpha
# 預期: NodePort 32222:36422/SCTP
```

### 4.3 健康檢查

```bash
# Prometheus
kubectl port-forward -n ricplt svc/r4-infrastructure-prometheus-server 9090:80 &
curl http://localhost:9090/-/healthy

# Grafana
kubectl port-forward -n ricplt svc/oran-grafana 3000:80 &
curl http://localhost:3000/api/health

# E2 Manager
kubectl exec -n ricplt deployment/deployment-ricplt-e2mgr -- \
  curl -s http://localhost:3800/v1/health

# KPIMON (xApp)
kubectl port-forward -n ricxapp svc/kpimon 8080:8080 &
curl http://localhost:8080/ric/v1/health/alive
```

### 4.4 測試數據流

```bash
# 1. 檢查 E2 Simulator 是否發送數據
kubectl logs -n ricxapp deployment/e2-simulator --tail=20

# 2. 檢查 KPIMON 是否接收數據
kubectl logs -n ricxapp deployment/kpimon --tail=20
# 預期看到: "Received E2 indication" 消息

# 3. 檢查 Prometheus 是否收集到 metrics
curl http://localhost:9090/api/v1/query?query=kpimon_messages_received_total
```

### 4.5 測試 Beam Query 功能

```bash
# 方式 1: CLI 工具
./scripts/query-beam.sh 5

# 方式 2: REST API
curl "http://localhost:8081/api/beam/5/kpi" | jq '.'

# 方式 3: Web UI
cd frontend-beam-query
python3 proxy-server.py
# 訪問 http://localhost:8888/
```

---

## 5. 常見問題

### 5.1 ImagePullBackOff 問題

**症狀**:
```
deployment-ricplt-o1mediator-xxx   0/1   ImagePullBackOff
```

**原因**: 缺少 Docker registry 憑證

**解決方案**:
```bash
# 方式 1: 創建 imagePullSecret
kubectl create secret docker-registry secret-nexus3-o-ran-sc-org-10002-o-ran-sc \
  --docker-server=nexus3.o-ran-sc.org:10002 \
  --docker-username=<your-username> \
  --docker-password=<your-password> \
  -n ricplt

# 方式 2: 禁用該組件
helm upgrade ${RELEASE_PREFIX}-o1mediator ./helm/o1mediator \
  --set enabled=false
```

---

### 5.2 RTMgr 無法找到 E2Term

**症狀**:
```
ERROR: Platform component not found: E2 Termination List
```

**解決方案**: 參見 `RMR_ERROR_ANALYSIS.md` 完整修復步驟

---

### 5.3 xApp 無法連接 DBaaS

**症狀**:
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**解決方案**:
```bash
# 檢查 DBaaS 服務
kubectl get svc -n ricplt | grep dbaas

# 檢查 Redis 集群狀態
kubectl exec -n ricplt redis-cluster-0 -- redis-cli cluster info

# 測試連接
kubectl run -it --rm test-redis --image=redis:7-alpine -- \
  redis-cli -h dbaas-tcp.ricplt.svc.cluster.local -p 6379 ping
```

---

### 5.4 Port Forwarding 問題

**症狀**: 無法訪問 Prometheus/Grafana Web UI

**解決方案**:
```bash
# 使用後台模式
kubectl port-forward -n ricplt svc/r4-infrastructure-prometheus-server 9090:80 &
kubectl port-forward -n ricplt svc/oran-grafana 3000:80 &

# 或使用腳本
./scripts/start-monitoring-ports.sh
```

---

## 6. 部署檢查清單

### 基礎設施層
- [ ] Prometheus 部署並運行
- [ ] Grafana 可訪問 (http://localhost:3000)
- [ ] Redis Cluster 3 個節點全部運行
- [ ] DBaaS 服務可訪問

### E2 接口層
- [ ] E2 Term 部署並運行
- [ ] E2 Manager HTTP API 可訪問
- [ ] Subscription Manager 部署並運行
- [ ] E2Term SCTP port 正確配置 (36422)

### RMR 路由層
- [ ] RTMgr 部署並運行
- [ ] RTMgr 日誌無嚴重錯誤
- [ ] 路由表成功分發到各組件

### xApp 管理層
- [ ] AppMgr 部署並運行
- [ ] RSM 部署並運行

### North-Bound 接口
- [ ] A1 Mediator 部署並運行
- [ ] A1 healthcheck API 可訪問

### xApps
- [ ] KPIMON 運行並接收數據
- [ ] Traffic Steering 運行
- [ ] QoE Predictor 運行
- [ ] RAN Control 運行
- [ ] Federated Learning 運行 (2 replicas)

### E2 Simulator
- [ ] E2 Simulator 運行並生成 KPI
- [ ] 數據成功發送到 xApps

### 數據流驗證
- [ ] E2 Sim → KPIMON 數據流正常
- [ ] KPIMON → Prometheus metrics 正常
- [ ] Prometheus → Grafana 查詢正常
- [ ] Beam Query API 正常工作

---

## 7. 後續步驟

### 7.1 配置監控面板

```bash
# 導入 Grafana dashboard
kubectl port-forward -n ricplt svc/oran-grafana 3000:80

# 訪問 http://localhost:3000
# 導入預設的 RIC Platform dashboards
```

### 7.2 配置告警規則

編輯 Prometheus 告警規則：
```bash
kubectl edit configmap -n ricplt prometheus-server

# 添加自定義告警規則
```

### 7.3 啟用 RMR 通訊

參見 `RMR_ERROR_ANALYSIS.md` 完成 RMR 配置。

---

## 8. 參考資料

### 官方文檔
- [O-RAN SC 官網](https://o-ran-sc.org/)
- [RIC Platform 文檔](https://docs.o-ran-sc.org/)
- [O-RAN 規範](https://www.o-ran.org/specifications)

### 相關指南
- `SYSTEM_HEALTH_REPORT.md` - 系統健康狀態報告
- `RMR_ERROR_ANALYSIS.md` - RMR 錯誤分析
- `QUICK_START_BEAM_QUERY.md` - Beam KPI 查詢快速指南

---

**部署完成！ **

如有任何問題，請參考：
- 系統健康報告: `SYSTEM_HEALTH_REPORT.md`
- RMR 問題: `RMR_ERROR_ANALYSIS.md`
- Beam 查詢: `QUICK_START_BEAM_QUERY.md`

**最後更新**: 2025-11-19
**版本**: 1.0
