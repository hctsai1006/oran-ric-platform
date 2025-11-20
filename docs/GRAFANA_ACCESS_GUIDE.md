# Grafana Dashboard 訪問指南

**O-RAN RIC Platform - Grafana 訪問方式**

---

## 📊 Grafana 服務資訊

根據您的 Kubernetes 集群配置：

- **服務名稱**: `oran-grafana`
- **命名空間**: `ricplt`
- **服務類型**: `ClusterIP` (集群內部訪問)
- **集群 IP**: `10.43.105.76`
- **端口**: `80`
- **默認帳號**: `admin` / `oran-ric-admin`

---

## 🚀 訪問方式

### 方式 1：Port-Forward（推薦用於開發/測試）

最簡單的訪問方式，直接將 Grafana 端口映射到本地：

```bash
# 啟動 port-forward（保持運行）
kubectl port-forward -n ricplt svc/oran-grafana 3000:80

# 然後在瀏覽器打開
# http://localhost:3000
```

**訪問 URL**: `http://localhost:3000`

**Dashboard URL**: `http://localhost:3000/d/oran-dual-path`

**使用我們的設置腳本（自動 port-forward）**:
```bash
# 腳本會自動建立 port-forward 並導入 Dashboard
./scripts/setup-grafana-dashboard.sh
```

---

### 方式 2：集群內部訪問

如果您在集群內的 Pod 中訪問：

```bash
# 完整 DNS 名稱
http://oran-grafana.ricplt.svc.cluster.local

# 簡短形式（同 namespace）
http://oran-grafana.ricplt

# 或直接用 Cluster IP
http://10.43.105.76
```

---

### 方式 3：NodePort（用於外部訪問）

如果需要從集群外部訪問，可以改用 NodePort：

#### 創建 NodePort 服務

```bash
# 創建 NodePort 配置
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: oran-grafana-nodeport
  namespace: ricplt
spec:
  type: NodePort
  ports:
  - port: 80
    targetPort: 3000
    nodePort: 30300  # 可以改為 30000-32767 範圍內的任意端口
  selector:
    app.kubernetes.io/instance: oran-grafana
    app.kubernetes.io/name: grafana
EOF
```

#### 訪問方式

```bash
# 獲取 Node IP
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')

# 訪問 URL
echo "http://${NODE_IP}:30300"
```

**訪問 URL**: `http://<NODE_IP>:30300`

---

### 方式 4：Ingress（用於生產環境）

如果您有 Ingress Controller（如 nginx-ingress），可以配置域名訪問：

#### 創建 Ingress

```bash
# 創建 Ingress 配置
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: oran-grafana-ingress
  namespace: ricplt
  annotations:
    kubernetes.io/ingress.class: nginx
    # 如果使用 HTTPS
    # cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  rules:
  - host: grafana.oran-ric.local  # 改為您的域名
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: oran-grafana
            port:
              number: 80
  # 如果使用 HTTPS
  # tls:
  # - hosts:
  #   - grafana.oran-ric.local
  #   secretName: grafana-tls
EOF
```

#### 配置 DNS 或 hosts

```bash
# 方式 A：修改 /etc/hosts（測試用）
echo "<INGRESS_IP> grafana.oran-ric.local" | sudo tee -a /etc/hosts

# 方式 B：配置 DNS 記錄（生產環境）
# 在您的 DNS 服務器添加 A 記錄：
# grafana.oran-ric.local -> <INGRESS_IP>
```

**訪問 URL**: `http://grafana.oran-ric.local`

---

## 🔐 登錄資訊

### 默認帳號

根據 `config/grafana-values.yaml` 配置：

- **用戶名**: `admin`
- **密碼**: `oran-ric-admin`

### 修改密碼

首次登錄後建議修改密碼：

1. 登錄 Grafana
2. 點擊左下角頭像 → **Preferences**
3. 選擇 **Change Password**

或通過 kubectl 修改：

```bash
# 獲取當前密碼
kubectl get secret -n ricplt oran-grafana \
  -o jsonpath="{.data.admin-password}" | base64 --decode

# 重置密碼
kubectl patch secret -n ricplt oran-grafana \
  -p "{\"data\":{\"admin-password\":\"$(echo -n 'new-password' | base64)\"}}"

# 重啟 Grafana
kubectl rollout restart deployment -n ricplt oran-grafana
```

---

## 📍 Dashboard 位置

### 自動導入後的位置

使用我們的設置腳本後，Dashboard 位於：

1. **通過菜單訪問**:
   - 首頁 → **Dashboards** → **Browse**
   - 搜索：`O-RAN RIC - Dual-Path Communication`

2. **直接 URL**:
   ```
   http://localhost:3000/d/oran-dual-path
   ```
   (將 localhost:3000 替換為實際訪問地址)

3. **UID**: `oran-dual-path`

---

## 🚀 快速訪問命令

### 一鍵訪問（推薦）

創建一個快捷腳本：

```bash
# 創建訪問腳本
cat > scripts/access-grafana.sh <<'EOF'
#!/bin/bash
echo "=========================================="
echo "Opening Grafana Dashboard"
echo "=========================================="
echo ""
echo "Setting up port-forward to Grafana..."
kubectl port-forward -n ricplt svc/oran-grafana 3000:80 > /dev/null 2>&1 &
PID=$!
echo "Port-forward started (PID: $PID)"
sleep 2

echo ""
echo "Grafana is now accessible at:"
echo "  → http://localhost:3000"
echo ""
echo "Dashboard URL:"
echo "  → http://localhost:3000/d/oran-dual-path"
echo ""
echo "Login credentials:"
echo "  Username: admin"
echo "  Password: oran-ric-admin"
echo ""
echo "Press Ctrl+C to stop port-forward and exit"
echo "=========================================="
echo ""

# 可選：自動打開瀏覽器
if command -v xdg-open > /dev/null; then
    xdg-open http://localhost:3000/d/oran-dual-path
elif command -v open > /dev/null; then
    open http://localhost:3000/d/oran-dual-path
fi

# 等待中斷
trap "kill $PID 2>/dev/null; echo 'Port-forward stopped'; exit 0" INT
wait $PID
EOF

chmod +x scripts/access-grafana.sh
```

然後直接運行：

```bash
./scripts/access-grafana.sh
```

---

## 🔧 配置 Prometheus 數據源

Dashboard 需要 Prometheus 數據源。

### 檢查數據源

```bash
# Port-forward 到 Grafana
kubectl port-forward -n ricplt svc/oran-grafana 3000:80 &

# 檢查數據源（需要 jq）
curl -s -u admin:oran-ric-admin \
  http://localhost:3000/api/datasources | \
  jq '.[] | select(.type=="prometheus")'
```

### 自動配置（已在 Helm values 中）

`config/grafana-values.yaml` 已配置：

```yaml
datasources:
  datasources.yaml:
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      url: http://r4-infrastructure-prometheus-server.ricplt:80
      access: proxy
      isDefault: true
```

如果未自動創建，手動添加：

1. 登錄 Grafana
2. **Configuration** → **Data Sources** → **Add data source**
3. 選擇 **Prometheus**
4. 配置：
   - **URL**: `http://r4-infrastructure-prometheus-server.ricplt:80`
   - 點擊 **Save & Test**

---

## 📊 驗證 Dashboard

### 檢查 Dashboard 是否正常工作

```bash
# 1. Port-forward
kubectl port-forward -n ricplt svc/oran-grafana 3000:80 &

# 2. 檢查 Dashboard 是否存在
curl -s -u admin:oran-ric-admin \
  http://localhost:3000/api/dashboards/uid/oran-dual-path | \
  jq '.dashboard.title'

# 輸出應該是：
# "O-RAN RIC - Dual-Path Communication"
```

### 檢查指標數據

```bash
# Port-forward 到 Prometheus
kubectl port-forward -n ricplt svc/r4-infrastructure-prometheus-server 9090:80 &

# 查詢雙路徑指標
curl -s 'http://localhost:9090/api/v1/query?query=dual_path_active_path' | \
  jq '.data.result'
```

---

## 🐛 故障排除

### 問題 1：無法連接 Grafana

```bash
# 檢查 Grafana Pod 狀態
kubectl get pod -n ricplt -l app.kubernetes.io/name=grafana

# 查看日誌
kubectl logs -n ricplt -l app.kubernetes.io/name=grafana --tail=50

# 重啟 Grafana
kubectl rollout restart deployment -n ricplt oran-grafana
```

### 問題 2：port-forward 失敗

```bash
# 確認服務存在
kubectl get svc -n ricplt oran-grafana

# 檢查端口是否被占用
lsof -i :3000 || netstat -tuln | grep 3000

# 使用不同端口
kubectl port-forward -n ricplt svc/oran-grafana 8080:80
# 訪問：http://localhost:8080
```

### 問題 3：Dashboard 顯示 "No Data"

```bash
# 1. 檢查 Prometheus 數據源
curl -u admin:oran-ric-admin http://localhost:3000/api/datasources

# 2. 檢查 xApp 是否在運行
kubectl get pod -n ricxapp

# 3. 檢查 xApp 指標
kubectl exec -n ricxapp deploy/traffic-steering -- curl localhost:8080/metrics

# 4. 檢查 Prometheus 是否抓取到指標
kubectl port-forward -n ricplt svc/r4-infrastructure-prometheus-server 9090:80 &
curl 'http://localhost:9090/api/v1/query?query=dual_path_active_path'
```

---

## 📱 移動設備訪問

如果需要在移動設備上訪問：

### 方式 1：使用 NodePort

```bash
# 創建 NodePort 服務
kubectl apply -f - <<EOF
apiVersion: v1
kind: Service
metadata:
  name: oran-grafana-nodeport
  namespace: ricplt
spec:
  type: NodePort
  ports:
  - port: 80
    targetPort: 3000
    nodePort: 30300
  selector:
    app.kubernetes.io/instance: oran-grafana
    app.kubernetes.io/name: grafana
EOF

# 獲取訪問地址
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
echo "訪問地址: http://${NODE_IP}:30300"
```

### 方式 2：使用 SSH 隧道

```bash
# 在您的電腦上
ssh -L 3000:localhost:3000 user@k8s-node-ip

# 在 K8s 節點上
kubectl port-forward -n ricplt svc/oran-grafana 3000:80

# 然後在移動設備瀏覽器訪問
# http://<您的電腦IP>:3000
```

---

## 🔒 安全建議

### 生產環境配置

1. **啟用 HTTPS**:
   ```yaml
   # 在 Ingress 中配置 TLS
   tls:
   - hosts:
     - grafana.oran-ric.example.com
     secretName: grafana-tls-cert
   ```

2. **修改默認密碼**:
   - 首次登錄後立即修改

3. **配置 OAuth/LDAP**:
   - 集成企業身份認證系統

4. **限制訪問**:
   ```yaml
   # 在 Ingress 中添加 IP 白名單
   annotations:
     nginx.ingress.kubernetes.io/whitelist-source-range: "10.0.0.0/8,192.168.0.0/16"
   ```

---

## 📚 相關文檔

- Dashboard 設置指南: `docs/GRAFANA_DASHBOARD_SETUP.md`
- 監控系統說明: `monitoring/README.md`
- 自動設置腳本: `scripts/setup-grafana-dashboard.sh`

---

## 📞 快速參考

### 常用 URL

| 用途 | URL |
|------|-----|
| Grafana 首頁 | `http://localhost:3000` |
| 雙路徑 Dashboard | `http://localhost:3000/d/oran-dual-path` |
| Prometheus | `http://localhost:9090` |
| 數據源配置 | `http://localhost:3000/datasources` |

### 常用命令

```bash
# 訪問 Grafana
kubectl port-forward -n ricplt svc/oran-grafana 3000:80

# 訪問 Prometheus
kubectl port-forward -n ricplt svc/r4-infrastructure-prometheus-server 9090:80

# 重啟 Grafana
kubectl rollout restart deployment -n ricplt oran-grafana

# 查看 Grafana 日誌
kubectl logs -n ricplt -l app.kubernetes.io/name=grafana -f

# 導入 Dashboard
./scripts/setup-grafana-dashboard.sh
```

---

**現在您可以訪問 Grafana Dashboard 了！** 📊
