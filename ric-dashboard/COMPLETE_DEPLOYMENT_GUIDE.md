# O-RAN RIC Platform Angular Dashboard - 完整部署指南

## 🎯 專案概述

這是為 **行動寬頻無線通訊實驗室 (MBWCL)** 開發的 O-RAN RIC Platform 統一管理儀表板。

### 核心功能

- ✅ **平台概覽**: 即時監控所有 xApps 狀態、資源使用情況
- ✅ **xApps 管理**: 完整的 xApp 生命週期管理（啟動、停止、重啟、擴縮容）
- ✅ **KPI 監控**: Beam 1-7 的即時 KPI 查詢和可視化
- ✅ **Grafana 整合**: 無縫嵌入 7 個 Grafana 儀表板
- ✅ **雙路徑監控**: RMR + HTTP 雙路徑通信狀態實時監控
- ✅ **告警系統**: Prometheus 告警整合和通知

### 技術架構

```
┌─────────────────────────────────────────────────────────────┐
│                    用戶瀏覽器 (Browser)                        │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/HTTPS
                     │
┌────────────────────▼────────────────────────────────────────┐
│              Nginx (Port 80)                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Angular Frontend (Static Files)                    │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Reverse Proxy (/api/* → Flask Backend)            │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│         Flask API Gateway (Port 5000)                        │
│  ┌──────────────┬──────────────┬──────────────┬─────────┐  │
│  │ K8s API      │ KPIMON API   │ Prometheus   │ Grafana │  │
│  │ (xApp Mgmt)  │ (KPI Query)  │ (Metrics)    │ (Dash)  │  │
│  └──────────────┴──────────────┴──────────────┴─────────┘  │
└─────────────────────────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬──────────────┐
        │            │            │              │
┌───────▼──────┐ ┌──▼─────┐ ┌───▼──────┐ ┌────▼─────┐
│ Kubernetes   │ │ KPIMON │ │Prometheus│ │ Grafana  │
│ API Server   │ │ xApp   │ │ Server   │ │ Server   │
└──────────────┘ └────────┘ └──────────┘ └──────────┘
```

## 📋 前置需求

### 必要條件

1. **Kubernetes 集群**
   - k3s 或 k8s (v1.28+)
   - KUBECONFIG 已配置

2. **Docker**
   - Docker Engine 20.10+
   - 本地 Registry (localhost:5000)

3. **Node.js 和 npm**
   - Node.js v20+
   - npm v10+

4. **已部署的 RIC 平台組件**
   - KPIMON xApp (ricxapp namespace)
   - Prometheus (ricplt namespace)
   - Grafana (ricplt namespace)

### 檢查前置條件

```bash
# 檢查 Kubernetes
kubectl version --client
kubectl get nodes

# 檢查 Docker
docker --version
docker ps

# 檢查 Node.js
node --version
npm --version

# 檢查 RIC 組件
kubectl get pods -n ricxapp
kubectl get pods -n ricplt
```

## 🚀 快速部署

### 方法 1: 一鍵部署 (推薦)

```bash
cd /home/mbwcl711_3060/thc1006/tmep/oran-ric-platform/ric-dashboard

# 執行部署腳本
./build-and-deploy.sh
```

部署腳本將自動執行以下步驟：
1. 構建 Docker 鏡像（Angular + Flask + Nginx）
2. 推送到本地 Registry
3. 創建 Kubernetes 資源
4. 等待 Pod 就緒
5. 顯示訪問方式

### 方法 2: 手動部署

#### 步驟 1: 構建 Angular 應用

```bash
cd /home/mbwcl711_3060/thc1006/tmep/oran-ric-platform/ric-dashboard

# 安裝依賴
npm install

# 本地開發（可選）
npm start
# 訪問 http://localhost:4200

# 生產構建
npm run build
```

#### 步驟 2: 構建 Docker 鏡像

```bash
# 構建鏡像
docker build -t localhost:5000/ric-dashboard:latest .

# 推送到本地 Registry
docker push localhost:5000/ric-dashboard:latest

# 驗證鏡像
docker images | grep ric-dashboard
```

#### 步驟 3: 部署到 Kubernetes

```bash
# 創建命名空間
kubectl create namespace ricplt --dry-run=client -o yaml | kubectl apply -f -

# 部署應用
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/ingress.yaml

# 檢查部署狀態
kubectl get pods -n ricplt -l app=ric-dashboard
kubectl get svc -n ricplt -l app=ric-dashboard
```

#### 步驟 4: 等待部署完成

```bash
# 等待 Pod 就緒
kubectl wait --for=condition=available --timeout=300s deployment/ric-dashboard -n ricplt

# 查看日誌
kubectl logs -n ricplt -l app=ric-dashboard -f
```

## 🌐 訪問 Dashboard

### 方法 1: Port Forward (開發環境推薦)

```bash
# 轉發到本地端口
kubectl port-forward -n ricplt svc/ric-dashboard 8080:80

# 在瀏覽器中打開
http://localhost:8080
```

### 方法 2: NodePort (直接訪問)

```bash
# 獲取 Node IP
kubectl get nodes -o wide

# 訪問
http://<node-ip>:30080
```

### 方法 3: Ingress (生產環境推薦)

```bash
# 添加 hosts 條目
echo "127.0.0.1 ric-dashboard.local" | sudo tee -a /etc/hosts

# 訪問
http://ric-dashboard.local
```

## 🧪 驗證部署

### 1. 檢查 Pod 狀態

```bash
kubectl get pods -n ricplt -l app=ric-dashboard

# 預期輸出：
# NAME                             READY   STATUS    RESTARTS   AGE
# ric-dashboard-xxxxx-xxxxx        1/1     Running   0          2m
# ric-dashboard-xxxxx-xxxxx        1/1     Running   0          2m
```

### 2. 檢查 API Gateway 健康狀態

```bash
# Port forward
kubectl port-forward -n ricplt svc/ric-dashboard 8080:80

# 檢查健康端點
curl http://localhost:8080/health

# 預期輸出：
# {"status":"healthy","service":"RIC Dashboard API Gateway"}
```

### 3. 測試 xApp 管理 API

```bash
# 獲取所有 xApps
curl http://localhost:8080/api/xapps

# 獲取特定 xApp
curl http://localhost:8080/api/xapps/kpimon-xapp

# 獲取 xApp 日誌
curl http://localhost:8080/api/xapps/kpimon-xapp/logs?lines=10
```

### 4. 測試 KPI 查詢 API

```bash
# 查詢 Beam 1 的 KPI
curl "http://localhost:8080/api/kpimon/beam/1/kpi?kpi_type=all&time_range=current"
```

### 5. 測試 Prometheus 代理

```bash
# 查詢 Prometheus 指標
curl "http://localhost:8080/api/prometheus/api/v1/query?query=up"
```

## 🔧 故障排除

### 問題 1: Pod 無法啟動

```bash
# 查看 Pod 詳情
kubectl describe pod -n ricplt -l app=ric-dashboard

# 查看日誌
kubectl logs -n ricplt -l app=ric-dashboard

# 常見原因：
# - 鏡像拉取失敗 → 檢查 Registry
# - 資源不足 → 增加節點資源
# - 權限問題 → 檢查 ServiceAccount 和 RBAC
```

### 問題 2: API 請求失敗

```bash
# 進入 Pod
kubectl exec -it -n ricplt deployment/ric-dashboard -- /bin/bash

# 測試服務連接
curl http://kpimon-xapp.ricxapp.svc.cluster.local:8081/ric/v1/health/alive
curl http://r4-infrastructure-prometheus-server.ricplt.svc.cluster.local:80/api/v1/query?query=up

# 檢查環境變量
kubectl exec -it -n ricplt deployment/ric-dashboard -- env | grep SERVICE
```

### 問題 3: Nginx 配置錯誤

```bash
# 檢查 Nginx 配置
kubectl exec -it -n ricplt deployment/ric-dashboard -- nginx -t

# 重新加載配置
kubectl exec -it -n ricplt deployment/ric-dashboard -- nginx -s reload
```

### 問題 4: RBAC 權限不足

```bash
# 檢查 ServiceAccount
kubectl get sa ric-dashboard -n ricplt

# 檢查 ClusterRole 和 ClusterRoleBinding
kubectl get clusterrole ric-dashboard
kubectl get clusterrolebinding ric-dashboard

# 重新應用 RBAC
kubectl apply -f k8s/deployment.yaml
```

## 📊 Dashboard 功能說明

### 1. 平台概覽 (Platform Overview)

- 顯示所有 xApps 的健康狀態
- 實時資源使用情況（CPU、Memory）
- E2 連接狀態
- 活躍告警數量
- 系統版本信息

### 2. xApps 管理 (xApps Management)

功能：
- 查看所有 xApps 列表
- 查看詳細狀態和指標
- 啟動/停止 xApps
- 重啟 xApps
- 擴縮容（修改副本數）
- 查看日誌

操作示例：
- 重啟 xApp: 點擊操作菜單 → 選擇 "Restart"
- 擴縮容: 點擊操作菜單 → 選擇 "Scale" → 輸入副本數

### 3. KPI 監控 (KPI Monitoring)

功能：
- 選擇 Beam (1-7)
- 選擇 KPI 類型（信號質量、吞吐量、資源、延遲、錯誤）
- 選擇時間範圍（當前、最近5分鐘、最近1小時）
- 圖表可視化
- 數據導出

### 4. Grafana 儀表板 (Grafana Dashboards)

嵌入的儀表板：
1. Platform Overview - 平台總覽
2. KPIMON Dashboard - KPIMON 指標
3. Traffic Steering - 流量調度
4. QoE Predictor - QoE 預測
5. RAN Control - RAN 控制
6. Federated Learning - 聯邦學習
7. Dual-Path Communication - 雙路徑通信

### 5. 雙路徑監控 (Dual-Path Monitor)

顯示：
- 當前活躍路徑（RMR 或 HTTP）
- 每條路徑的健康狀態
- 切換歷史
- 延遲對比
- 成功率統計

### 6. 告警通知 (Alerts & Notifications)

功能：
- 查看活躍告警
- 告警歷史
- 告警詳情
- 告警靜音
- 通知設置

## 🔄 更新和維護

### 更新 Angular 代碼

```bash
cd /home/mbwcl711_3060/thc1006/tmep/oran-ric-platform/ric-dashboard

# 修改代碼
# ...

# 重新構建和部署
./build-and-deploy.sh
```

### 更新 API Gateway

```bash
# 修改 api-gateway/app.py
# ...

# 重新構建和部署
./build-and-deploy.sh
```

### 滾動更新

```bash
# 設置新鏡像
kubectl set image deployment/ric-dashboard ric-dashboard=localhost:5000/ric-dashboard:v2.0.0 -n ricplt

# 查看滾動更新狀態
kubectl rollout status deployment/ric-dashboard -n ricplt

# 回滾（如果需要）
kubectl rollout undo deployment/ric-dashboard -n ricplt
```

### 擴縮容

```bash
# 增加副本數
kubectl scale deployment/ric-dashboard --replicas=3 -n ricplt

# 自動擴縮容（HPA）
kubectl autoscale deployment/ric-dashboard --cpu-percent=70 --min=2 --max=10 -n ricplt
```

## 📝 開發指南

### 本地開發

```bash
# 啟動 Angular 開發服務器
npm start

# 訪問 http://localhost:4200

# API 請求將被代理到 Kubernetes 服務
# 確保 kubectl port-forward 正在運行
```

### 添加新組件

```bash
# 生成新組件
npx ng generate component components/my-component

# 添加到路由
# 編輯 src/app/app-routing.module.ts
```

### 添加新服務

```bash
# 生成新服務
npx ng generate service services/my-service

# 實現 API 調用
# 編輯 src/app/services/my-service.service.ts
```

### 代碼規範

- 使用 TypeScript strict mode
- 遵循 Angular 官方風格指南
- 組件應該是單一職責的
- 所有 API 調用應通過服務層
- 使用 RxJS Observable 進行異步操作

## 🎨 自定義品牌

### 更改 Logo

編輯 `src/app/components/navigation/navigation.component.html`:

```html
<div class="logo-container">
  <h1 class="logo-text">您的Logo</h1>
  <span class="logo-subtitle">您的副標題</span>
</div>
```

### 更改主題顏色

編輯 `src/app/components/navigation/navigation.component.scss`:

```scss
.header-toolbar {
  background: linear-gradient(135deg, #YOUR_COLOR 0%, #YOUR_COLOR_DARK 100%);
}
```

### 更改平台信息

編輯 `src/app/components/navigation/navigation.component.ts`:

```typescript
platformInfo = {
  name: '您的平台名稱',
  version: 'v1.0.0',
  lab: '您的實驗室名稱'
};
```

## 📚 參考資料

- [Angular Documentation](https://angular.dev)
- [Angular Material](https://material.angular.io)
- [Kubernetes Documentation](https://kubernetes.io/docs)
- [Flask Documentation](https://flask.palletsprojects.com)
- [O-RAN Alliance](https://www.o-ran.org)

## 👥 貢獻

MBWCL - 行動寬頻無線通訊實驗室

## 📄 授權

Apache License 2.0

---

**© 2024 MBWCL - 行動寬頻無線通訊實驗室**
