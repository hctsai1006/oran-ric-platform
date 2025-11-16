# 故障排除：Helm "connection refused" 錯誤

**作者**: 蔡秀吉 (thc1006)
**日期**: 2025-11-16
**問題**: Helm 無法連接 Kubernetes 集群

## 錯誤訊息

```
Error: INSTALLATION FAILED: Kubernetes cluster unreachable:
Get "http://localhost:8080/version": dial tcp [::1]:8080: connect: connection refused
```

## 問題分析

### 根本原因

**KUBECONFIG 環境變量未正確設置**

k3s 將 kubeconfig 文件放在：
- **實際位置**: `/etc/rancher/k3s/k3s.yaml`
- **預期位置**: `~/.kube/config`（kubectl/Helm 默認查找）

當 KUBECONFIG 未設置時，Helm 會嘗試連接到 `localhost:8080`（Kubernetes 舊版默認端口），導致連接失敗。

### 為何 kubectl 能用但 Helm 不能？

可能的原因：
1. kubectl 使用了 `sudo`（讀取 root 的配置）
2. kubectl 臨時使用了 `--kubeconfig` 參數
3. 在不同的終端 session 執行命令

## 症狀識別

### 正常狀態：
```bash
$ kubectl get nodes
NAME      STATUS   ROLES    AGE   VERSION
thc1006   Ready    master   1h    v1.28.5+k3s1

$ helm version
version.BuildInfo{Version:"v3.x.x", ...}
```

### 異常狀態：
```bash
$ kubectl get nodes
# 正常輸出（可能使用 sudo 或其他方式）

$ helm install xxx
Error: Kubernetes cluster unreachable: Get "http://localhost:8080/version"
```

## 解決方案

### 方案 1：快速修復（推薦）

```bash
# 設置 KUBECONFIG 環境變量
export KUBECONFIG=$HOME/.kube/config
echo "export KUBECONFIG=$HOME/.kube/config" >> ~/.bashrc
source ~/.bashrc

# 驗證修復
helm version
kubectl cluster-info
```

### 方案 2：從零設置 kubeconfig

```bash
# 創建 .kube 目錄
mkdir -p $HOME/.kube

# 複製 k3s 配置文件
sudo cp /etc/rancher/k3s/k3s.yaml $HOME/.kube/config

# 設置正確的權限
sudo chown $USER:$USER $HOME/.kube/config

# 設置環境變量
export KUBECONFIG=$HOME/.kube/config
echo "export KUBECONFIG=$HOME/.kube/config" >> ~/.bashrc
source ~/.bashrc

# 驗證
kubectl get nodes
helm version
```

### 方案 3：臨時使用（測試用）

```bash
# 每次使用前執行
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# 或者直接指定
helm install xxx --kubeconfig /etc/rancher/k3s/k3s.yaml
```

## 驗證步驟

### 1. 檢查 KUBECONFIG 是否設置

```bash
echo $KUBECONFIG
# 應該輸出: /home/your-user/.kube/config
```

### 2. 檢查配置文件是否存在

```bash
ls -la $HOME/.kube/config
# 應該顯示文件存在且有正確權限
```

### 3. 測試 kubectl

```bash
kubectl cluster-info
# 應該顯示 Kubernetes 控制平面資訊
```

### 4. 測試 Helm

```bash
helm version
# 應該顯示版本資訊，無錯誤
```

### 5. 測試 Helm 連接

```bash
helm list -A
# 應該列出所有 releases（可能為空）
```

## 預防措施

### 在 README 部署步驟中

確保執行：
```bash
sudo bash scripts/deployment/setup-k3s.sh
source ~/.bashrc  # 這一步很重要！
```

### 在新的終端窗口中

如果開啟新的終端，確保：
```bash
source ~/.bashrc
# 或重新設置
export KUBECONFIG=$HOME/.kube/config
```

### 使用別名（可選）

```bash
# 添加到 ~/.bashrc
alias fix-kube='export KUBECONFIG=$HOME/.kube/config && source ~/.bashrc'

# 使用
fix-kube
```

## 相關問題

### Q: 為什麼 setup-k3s.sh 執行後還是有問題？

**A**: 可能原因：
1. 腳本執行被中斷
2. 沒有執行 `source ~/.bashrc`
3. 在不同的 shell session 執行
4. 使用了 `sudo bash` 而不是 `bash`

### Q: 每次重啟終端都要重新設置？

**A**: 如果每次都要重新設置，檢查：
```bash
cat ~/.bashrc | grep KUBECONFIG
# 應該看到: export KUBECONFIG=$HOME/.kube/config
```

如果沒有，手動添加：
```bash
echo "export KUBECONFIG=$HOME/.kube/config" >> ~/.bashrc
```

### Q: 我用的是 zsh，怎麼辦？

**A**: 使用 `~/.zshrc` 替代 `~/.bashrc`：
```bash
echo "export KUBECONFIG=$HOME/.kube/config" >> ~/.zshrc
source ~/.zshrc
```

## 測試案例

### 完整測試流程

```bash
# 1. 清除環境變量
unset KUBECONFIG

# 2. 驗證會出錯
helm version
# 應該出現 "connection refused"

# 3. 設置環境變量
export KUBECONFIG=$HOME/.kube/config

# 4. 驗證修復成功
helm version
# 應該正常顯示版本

# 5. 持久化設置
echo "export KUBECONFIG=$HOME/.kube/config" >> ~/.bashrc
source ~/.bashrc
```

## 參考資料

- [k3s 官方文檔 - Cluster Access](https://docs.k3s.io/cluster-access)
- [Kubernetes 配置和認證](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/)
- [Helm 配置](https://helm.sh/docs/helm/helm/)

## 相關文件

- `/home/thc1006/oran-ric-platform/scripts/deployment/setup-k3s.sh` (第 83-89 行)
- `/home/thc1006/oran-ric-platform/README.md` (Quick Start)
- `/home/thc1006/oran-ric-platform/docs/deployment/WORKING_DEPLOYMENT_GUIDE.md`

---

**維護者**: 蔡秀吉 (thc1006)
**最後更新**: 2025-11-16
**狀態**: ✅ 已驗證並測試
