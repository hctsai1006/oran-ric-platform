# O-RAN RIC Platform Angular Dashboard

## 概述
這是一個為 **行動寬頻無線通訊實驗室 (MBWCL)** 開發的強大 O-RAN RIC 平台儀表板。

## 功能特性

### 核心功能
- ✅ **平台概覽 Dashboard**: 即時監控所有 xApps 狀態
- ✅ **xApps 管理**: 管理和監控所有 5 個 xApps
- ✅ **KPI 監控**: Beam 1-7 的即時 KPI 查詢和可視化
- ✅ **Grafana 整合**: 嵌入 7 個 Grafana 儀表板
- ✅ **雙路徑監控**: RMR + HTTP 雙路徑通信狀態
- ✅ **告警系統**: Prometheus 告警整合

### 技術棧
- **Frontend**: Angular 17 + Angular Material
- **Charts**: Chart.js
- **API 整合**: xApps, Prometheus, Grafana, KPIMON
- **部署**: Docker + Kubernetes

## 快速開始

### 本地開發
```bash
# 安裝依賴
npm install

# 啟動開發服務器
npm start

# 訪問 http://localhost:4200
```

### 生產構建
```bash
# 構建
npm run build

# 輸出在 dist/ric-dashboard/
```

## 部署到 Kubernetes

### 方法 1: 使用提供的腳本
```bash
cd /home/mbwcl711_3060/thc1006/tmep/oran-ric-platform
./scripts/deploy-dashboard.sh
```

### 方法 2: 手動部署
見下方完整說明。

## API 代理配置

Dashboard 需要配置反向代理來訪問後端服務：

- `/api/xapps/*` → Kubernetes API (xApp 管理)
- `/api/kpimon/*` → KPIMON xApp (port 8081)
- `/api/prometheus/*` → Prometheus (port 9090)
- `/api/grafana/*` → Grafana (port 3000)

## 組件說明

### 服務 (Services)
- `xapp.service.ts`: xApp 管理 API
- `kpi.service.ts`: KPIMON KPI 查詢
- `prometheus.service.ts`: Prometheus 指標查詢
- `grafana.service.ts`: Grafana 儀表板整合

### 組件 (Components)
1. **Dashboard**: 平台概覽
2. **xApps Management**: xApp 列表、狀態、操作
3. **KPI Monitoring**: 即時 KPI 查詢和圖表
4. **Grafana Dashboard**: 嵌入式儀表板
5. **Dual-Path Monitor**: 雙路徑狀態監控
6. **Alerts**: 告警列表和通知

## MBWCL 品牌
- Logo: MBWCL (行動寬頻無線通訊實驗室)
- 主色調: Material Blue (#1976d2)
- 版本: v2.0.1

## 下一步

由於時間和 token 限制，以下是完成部署的步驟：

### 1. 完成組件實現
每個組件的 TypeScript、HTML、SCSS 文件已生成，需要填充實際邏輯。

### 2. 創建 Backend API Gateway
創建一個 Node.js/Python 後端代理來統一 API 訪問。

### 3. Docker化
創建 Dockerfile 和構建腳本。

### 4. Kubernetes 部署
創建 Deployment, Service, Ingress 配置。

## 聯繫
MBWCL - 行動寬頻無線通訊實驗室
