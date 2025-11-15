# RFC: O-RAN xApp MVP 修復計畫

**作者**：蔡秀吉（thc1006）
**日期**：2025-11-15
**狀態**：提案
**類型**：維護性修復

---

## 目標

基於 **MVP（最小可行產品）**、**TDD**、**Boy Scout Rule** 和 **Small CLs** 原則，修復當前 xApp 部署配置中的實際問題，避免過度設計和過早抽象。

---

## 非目標

- ❌ **不**為所有 xApp 添加 ServiceAccount（過度設計，無功能需求）
- ❌ **不**添加複雜的 RBAC 權限（當前代碼不需要 K8s API 訪問）
- ❌ **不**重構整個部署架構（過早抽象）

---

## 問題分析

### 深度分析結果

經過對所有 5 個 xApp 的代碼和配置進行深度分析，發現以下實際問題：

#### 1. 健康檢查缺失（功能性問題）✅ 必須修復

**現況**：
```
KPIMON:           ❌ 缺少健康檢查
RC:               ✅ 有健康檢查
Traffic Steering: ✅ 有健康檢查
QoE Predictor:    ✅ 有健康檢查
Federated Learning: ✅ 有健康檢查
```

**影響**：
- KPIMON Pod 無法被 Kubernetes 正確監控
- 如果 KPIMON 進程掛掉，K8s 不會自動重啟
- 影響系統可用性

**證據**：
```bash
# KPIMON deployment.yaml 第 44-58 行
# 缺少 livenessProbe 和 readinessProbe 配置
```

---

#### 2. RBAC 權限過多（安全問題）⚠️ 應該修復

**現況**：
- QoE Predictor 和 Federated Learning 有 ServiceAccount
- 但配置了**未使用的權限**

**QoE ServiceAccount 權限分析**：
```yaml
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]  # ⚠️ 未使用
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["pods"]  # ⚠️ 未使用
  verbs: ["get", "list"]
```

**代碼驗證**：
```bash
# 搜索 QoE 和 FL 源代碼
grep -r "from kubernetes" xapps/*/src/*.py  # 結果：0 個匹配
grep -r "client.CoreV1Api" xapps/*/src/*.py  # 結果：0 個匹配
```

**結論**：這些權限從未被使用，違反**最小權限原則**。

---

#### 3. 文件組織混亂（維護性問題）⚠️ 應該清理

**問題 A：重複的 config.json**
```
xapps/qoe-predictor/
├── config.json          # ⚠️ 重複
└── config/config.json   # ✅ 正確位置
```

**問題 B：舊文檔混在代碼目錄**
```
xapps/kpm-xapp/KPM xApp (For Slice) User Guide.md
xapps/traffic-steering/【G Release】 Integrate and Test TS Use Case.md
xapps/rc-xapp/RC xApp (For Slice) User Guide.md
```

**問題 C：venv 目錄被提交到 git**
```
xapps/kpimon-go-xapp/venv/  # 780MB，不應在版本控制中
```

---

## 設計原則遵循

### 1. MVP（最小可行產品）

**只修復影響功能或安全的實際問題**，不添加「可能有用」的功能。

**決策表**：

| 問題 | 影響 | 是否修復 | 理由 |
|------|------|---------|------|
| KPIMON 缺少健康檢查 | 功能 | ✅ 是 | 影響 K8s 監控和自動重啟 |
| QoE/FL 權限過多 | 安全 | ✅ 是 | 違反最小權限原則 |
| 文件組織混亂 | 維護 | ✅ 是 | 造成混淆，影響可維護性 |
| KPIMON/RC/TS 無 SA | 無 | ❌ 否 | 不影響功能，是過度設計 |

---

### 2. TDD（測試驅動開發）

**驗證策略**：先定義驗證方法，再實施修改。

#### CL #1 驗證（健康檢查）
```bash
# 1. 部署前測試（Red）
kubectl get pod -n ricxapp -l app=kpimon -o jsonpath='{.items[0].status.conditions}'
# 預期：缺少 Ready condition 的更新機制

# 2. 部署後測試（Green）
kubectl get pod -n ricxapp -l app=kpimon
# 預期：STATUS=Running, READY=1/1

kubectl logs -n ricxapp -l app=kpimon | grep "health"
# 預期：看到健康檢查日誌

curl http://<kpimon-service>:8080/health/alive
# 預期：HTTP 200 OK
```

#### CL #2 驗證（RBAC）
```bash
# 1. 修改前測試
kubectl auth can-i list configmaps --as=system:serviceaccount:ricxapp:qoe-predictor-sa -n ricxapp
# 預期：yes（過多權限）

# 2. 修改後測試
kubectl auth can-i list configmaps --as=system:serviceaccount:ricxapp:qoe-predictor-sa -n ricxapp
# 預期：no（最小權限）

# 3. 功能測試
kubectl logs -n ricxapp -l app=qoe-predictor | grep "ERROR"
# 預期：無與權限相關的錯誤
```

#### CL #3 驗證（文件清理）
```bash
# 1. 清理前
ls xapps/qoe-predictor/config.json
ls xapps/kpimon-go-xapp/venv/

# 2. 清理後
ls xapps/qoe-predictor/config.json 2>/dev/null || echo "已移除"
ls xapps/kpimon-go-xapp/venv/ 2>/dev/null || echo "已移除"

# 3. 部署測試
kubectl apply -f xapps/qoe-predictor/deploy/
# 預期：部署正常，無錯誤
```

---

### 3. Boy Scout Rule（讓代碼比發現時更好）

**每次提交都改進一點，但不重寫**。

**遵循**：
- ✅ 移除未使用的配置（QoE/FL RBAC）
- ✅ 清理重複和舊文件
- ✅ 補齊缺失的必要配置（KPIMON 健康檢查）

**不做**：
- ❌ 不為所有 xApp 添加「預防性」配置
- ❌ 不重構整個部署架構
- ❌ 不添加未來「可能需要」的功能

---

### 4. Small CLs（小的變更列表）

**每個 CL 都**：
- 獨立可審查
- 獨立可部署
- 獨立可回滾
- 有明確的單一目的

---

## 變更計畫

### CL #0: 實現 KPIMON 健康檢查端點

#### 變更範圍
- **影響文件**：2 個
  - `xapps/kpimon-go-xapp/src/kpimon.py`
  - `xapps/kpimon-go-xapp/requirements.txt`
- **代碼行數**：+25 行

#### 變更內容

**步驟 1：添加 Flask 依賴**
```txt
# requirements.txt 添加：
flask==3.0.0
```

**步驟 2：在 kpimon.py 中實現健康檢查端點**
```python
# 在 kpimon.py 頂部添加 Flask 導入（第 13 行後）：
from flask import Flask, jsonify
from threading import Thread

# 在 KPIMonitor.__init__() 中初始化 Flask app（第 83 行後）：
        # Initialize Flask app for health checks
        self.flask_app = Flask(__name__)
        self._setup_health_routes()

        logger.info(f"KPIMON xApp initialized with config: {self.config}")

# 添加健康檢查路由設置方法（第 114 行後）：
    def _setup_health_routes(self):
        """Setup Flask routes for health checks"""
        @self.flask_app.route('/health/alive', methods=['GET'])
        def health_alive():
            return jsonify({"status": "alive"}), 200

        @self.flask_app.route('/health/ready', methods=['GET'])
        def health_ready():
            is_ready = self.running and self.xapp is not None
            status_code = 200 if is_ready else 503
            return jsonify({
                "status": "ready" if is_ready else "not_ready",
                "subscriptions": len(self.subscriptions),
                "kpi_buffer_size": len(self.kpi_buffer)
            }), status_code

# 修改 start() 方法，在 Prometheus 之後啟動 Flask（第 150 行後）：
        # Start Prometheus metrics server
        start_http_server(8080)
        logger.info("Prometheus metrics server started on port 8080")

        # Start Flask health check server on port 8081
        flask_thread = Thread(target=lambda: self.flask_app.run(
            host='0.0.0.0',
            port=8081,
            debug=False,
            use_reloader=False
        ))
        flask_thread.daemon = True
        flask_thread.start()
        logger.info("Flask health check server started on port 8081")
```

**步驟 3：更新 deployment.yaml 暴露 port 8081**
```yaml
# 在 deployment.yaml 第 43 行後添加：
        - name: http-health
          containerPort: 8081
          protocol: TCP
```

#### 設計決策

**為什麼使用 port 8081 而非 8080？**
- Port 8080 已被 Prometheus metrics server 佔用
- 分離關注點：metrics（8080）vs health（8081）
- 參考其他 xApp：RC 用 8100，TS 用 8080（因為沒有 Prometheus）

**為什麼使用 Flask 而非其他框架？**
- 與其他 xApp（RC、TS、QoE、FL）保持一致
- 輕量級，僅用於健康檢查
- 團隊已熟悉

#### 驗證步驟
```bash
# 1. 安裝依賴
pip install flask==3.0.0

# 2. 本地測試
python xapps/kpimon-go-xapp/src/kpimon.py &
sleep 5

# 3. 測試健康檢查端點
curl http://localhost:8081/health/alive
# 預期：{"status":"alive"}

curl http://localhost:8081/health/ready
# 預期：{"status":"ready",...} 或 {"status":"not_ready",...}

# 4. 測試 Prometheus 仍然正常
curl http://localhost:8080/metrics
# 預期：Prometheus metrics 輸出

# 5. 停止測試
kill %1
```

#### 回滾方案
```bash
git revert <commit-hash>
pip install -r xapps/kpimon-go-xapp/requirements.txt
```

---

### CL #1: 為 KPIMON 添加健康檢查探針

#### 變更範圍
- **影響文件**：1 個
  - `xapps/kpimon-go-xapp/deploy/deployment.yaml`
- **代碼行數**：+18 行

#### 變更內容
```yaml
# 在 kpimon deployment.yaml 第 51 行後添加：
        livenessProbe:
          httpGet:
            path: /health/alive
            port: 8081  # Flask health server port
          initialDelaySeconds: 10
          periodSeconds: 15
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8081  # Flask health server port
          initialDelaySeconds: 5
          periodSeconds: 15
          timeoutSeconds: 5
          successThreshold: 1
          failureThreshold: 3
```

#### 前提條件 ⚠️

**驗證結果（2025-11-15）**：
```bash
grep -n "/health/alive\|/health/ready" xapps/kpimon-go-xapp/src/kpimon.py
# 結果：無匹配
```

**發現**：KPIMON 僅實現了 Prometheus metrics 服務器（port 8080），**未實現 Flask 健康檢查端點**。

**證據**：
- `kpimon.py:150` - `start_http_server(8080)` 是 prometheus_client，不是 Flask
- 無 `from flask import Flask` 導入
- 無 `/health/alive` 或 `/health/ready` 路由定義

**結論**：必須先執行 **CL #0**（實現健康檢查端點）才能執行 CL #1。

#### 驗證步驟
```bash
# 1. 應用配置
kubectl apply -f xapps/kpimon-go-xapp/deploy/deployment.yaml

# 2. 等待 Pod 就緒
kubectl wait --for=condition=ready pod -l app=kpimon -n ricxapp --timeout=60s

# 3. 檢查健康狀態
kubectl get pod -n ricxapp -l app=kpimon
# 預期：READY 1/1

# 4. 檢查健康檢查日誌
kubectl logs -n ricxapp -l app=kpimon | tail -20
```

#### 回滾方案
```bash
git revert <commit-hash>
kubectl apply -f xapps/kpimon-go-xapp/deploy/deployment.yaml
```

---

### CL #2: 簡化 QoE 和 FL 的 RBAC 權限

#### 變更範圍
- **影響文件**：2 個
  - `xapps/qoe-predictor/deploy/serviceaccount.yaml`
  - `xapps/federated-learning/deploy/serviceaccount.yaml`
- **代碼行數**：-12 行（移除未使用的權限）

#### 變更內容

**選項 A：完全移除 RBAC（推薦）**
```yaml
# 移除 Role 的所有 rules
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: qoe-predictor-role
  namespace: ricxapp
rules: []  # 空規則，明確表示無權限需求
```

**選項 B：保留最低限度權限（保守）**
```yaml
rules:
- apiGroups: [""]
  resources: ["configmaps"]  # 僅 ConfigMap
  verbs: ["get"]  # 僅 get
  resourceNames: ["qoe-predictor-config"]  # 限制到特定資源
```

**推薦**：選項 A（完全移除），因為代碼確實不需要任何 K8s API 訪問。

#### 驗證步驟
```bash
# 1. 應用新配置
kubectl apply -f xapps/qoe-predictor/deploy/serviceaccount.yaml
kubectl apply -f xapps/federated-learning/deploy/serviceaccount.yaml

# 2. 驗證權限已移除
kubectl auth can-i list configmaps --as=system:serviceaccount:ricxapp:qoe-predictor-sa -n ricxapp
# 預期：no

# 3. 驗證 xApp 功能正常
kubectl logs -n ricxapp -l app=qoe-predictor | grep -i "error\|permission"
# 預期：無權限相關錯誤

# 4. 測試健康檢查
curl http://<qoe-service>:8090/health/alive
# 預期：HTTP 200 OK
```

#### 回滾方案
```bash
git revert <commit-hash>
kubectl apply -f xapps/qoe-predictor/deploy/serviceaccount.yaml
kubectl apply -f xapps/federated-learning/deploy/serviceaccount.yaml
```

---

### CL #3: 清理重複和舊文檔

#### 變更範圍
- **影響文件**：5 個
  - `xapps/qoe-predictor/config.json`（重複）
  - `xapps/kpm-xapp/KPM xApp (For Slice) User Guide.md`
  - `xapps/traffic-steering/【G Release】 Integrate and Test TS Use Case.md`
  - `xapps/rc-xapp/RC xApp (For Slice) User Guide.md`
  - `xapps/kpimon-go-xapp/venv/`（整個目錄）

#### 變更內容

**步驟 1：移除重複的 config.json**
```bash
rm xapps/qoe-predictor/config.json
```

**步驟 2：移動舊文檔到參考目錄**
```bash
mkdir -p docs/references/legacy-guides

mv "xapps/kpm-xapp/KPM xApp (For Slice) User Guide.md" \
   docs/references/legacy-guides/

mv "xapps/traffic-steering/【G Release】 Integrate and Test TS Use Case.md" \
   docs/references/legacy-guides/

mv "xapps/rc-xapp/RC xApp (For Slice) User Guide.md" \
   docs/references/legacy-guides/
```

**步驟 3：移除 venv 並更新 .gitignore**
```bash
rm -rf xapps/kpimon-go-xapp/venv/

# 確保 .gitignore 包含 venv
echo "venv/" >> .gitignore
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore
```

#### 驗證步驟
```bash
# 1. 驗證文件已移除
ls xapps/qoe-predictor/config.json 2>/dev/null && echo "FAIL" || echo "PASS"
ls xapps/kpimon-go-xapp/venv/ 2>/dev/null && echo "FAIL" || echo "PASS"

# 2. 驗證舊文檔已移動
ls docs/references/legacy-guides/ | wc -l
# 預期：3 個文件

# 3. 驗證部署仍然正常
kubectl apply -f xapps/qoe-predictor/deploy/
kubectl get pods -n ricxapp -l app=qoe-predictor
# 預期：運行正常
```

#### 回滾方案
```bash
git revert <commit-hash>
```

---

## 實施順序

### Phase 1: CL #0（實現健康檢查端點）- 前置條件
**優先級**：P0（最高，阻塞 CL #1）
**影響**：為健康檢查探針提供後端支持
**風險**：中（修改核心 xApp 代碼）
**時間估計**：45 分鐘（開發 + 測試）

### Phase 2: CL #1（添加健康檢查探針）- 功能性修復
**優先級**：P0（最高）
**影響**：生產環境的監控和可用性
**風險**：低（僅添加 K8s 配置）
**依賴**：CL #0 必須先完成
**時間估計**：20 分鐘

### Phase 3: CL #2（RBAC 簡化）- 安全性改進
**優先級**：P1（高）
**影響**：安全合規
**風險**：低（移除未使用的權限）
**時間估計**：20 分鐘

### Phase 4: CL #3（文件清理）- 維護性改進
**優先級**：P2（中）
**影響**：代碼可維護性
**風險**：極低（只是移動/刪除文件）
**時間估計**：15 分鐘

**總時間估計**：2 小時

---

## 風險評估

| 變更 | 風險等級 | 潛在問題 | 緩解措施 |
|------|---------|---------|---------|
| CL #0 | 🟡 中 | Flask 與 RMR 執行緒可能衝突 | 使用 daemon thread，充分測試 |
| CL #0 | 🟡 中 | Port 8081 可能已被佔用 | 檢查 deployment 端口配置，選擇未使用端口 |
| CL #1 | 🟢 低 | 健康檢查探針配置錯誤 | 依賴 CL #0 完成，使用標準探針配置 |
| CL #2 | 🟢 低 | xApp 可能意外依賴某些權限 | 充分測試功能，觀察日誌 |
| CL #3 | 🟢 極低 | 誤刪重要文件 | 先移動到 docs/references，不立即刪除 |

---

## 成功標準

### CL #0
- ✅ KPIMON Flask 服務器成功啟動在 port 8081
- ✅ `/health/alive` 端點返回 HTTP 200
- ✅ `/health/ready` 端點根據 xApp 狀態返回 200 或 503
- ✅ Prometheus metrics 在 port 8080 仍然正常工作
- ✅ KPIMON 仍能正常處理 RMR 消息

### CL #1
- ✅ KPIMON Pod READY 狀態為 1/1
- ✅ `kubectl describe pod` 顯示健康檢查通過
- ✅ 無健康檢查相關錯誤日誌
- ✅ livenessProbe 和 readinessProbe 成功連接到 port 8081

### CL #2
- ✅ `kubectl auth can-i` 確認權限已移除
- ✅ QoE 和 FL Pod 運行正常
- ✅ 無權限相關錯誤日誌

### CL #3
- ✅ 重複和舊文件已移除/移動
- ✅ 部署仍然正常工作
- ✅ Git 歷史乾淨，無不必要的大文件

---

## 文檔更新

每個 CL 完成後更新以下文檔：

1. `docs/deployment-guide-complete.md`
   - 更新 KPIMON 部署配置示例
   - 說明健康檢查的重要性

2. `docs/QUICK-START.md`
   - 確保快速開始指南反映最新配置

3. `README.md`
   - 更新專案狀態（如果需要）

---

## 附錄 A：為什麼不添加 ServiceAccount？

### 分析結論

經過深度代碼分析，所有 5 個 xApp 都：
- ❌ **不**使用 Kubernetes API 客戶端
- ❌ **不**訪問 ConfigMap/Secret（除了通過 Volume 掛載）
- ❌ **不**列出或監控 Pod
- ✅ 完全通過 O-RAN 接口通信（RMR、Redis、HTTP）

### MVP 決策

添加 ServiceAccount 會是**過度設計**，因為：
1. 無功能需求
2. 增加配置複雜度
3. 需要額外的維護

### Boy Scout Rule 決策

當前 QoE 和 FL 已有 ServiceAccount，但：
- 權限未被使用
- 應該簡化，而非擴展到其他 xApp

**結論**：遵循「讓代碼更簡單」，而非「讓所有配置一致但複雜」。

---

## 附錄 B：Small CLs 原則

### 什麼是 Small CLs？

Small CLs（Change Lists）是 Google 工程實踐，強調：
- 每次提交應該小而專注
- 易於審查（15 分鐘內完成）
- 易於測試
- 易於回滾

### 本 RFC 的實踐

| CL | 文件數 | 行數變更 | 審查時間 | 可獨立部署 | 依賴 |
|----|--------|---------|---------|-----------|------|
| #0 | 2 個 | +25 | 15 分鐘 | ✅ 是 | 無 |
| #1 | 1 個 | +18 | 10 分鐘 | ⚠️ 依賴 #0 | CL #0 |
| #2 | 2 個 | -12 | 10 分鐘 | ✅ 是 | 無 |
| #3 | 5 個 | -大量 | 10 分鐘 | ✅ 是 | 無 |

**每個 CL 都可以獨立審查和回滾。CL #1 依賴 CL #0 先完成。**

---

## 批准與執行

### 批准者
- [ ] 蔡秀吉（thc1006）- 專案維護者

### 執行計畫
1. 審查本 RFC
2. **依序執行**：CL #0 → CL #1 → CL #2 → CL #3
   - ⚠️ **CL #0 必須在 CL #1 之前完成**（依賴關係）
   - CL #2 和 #3 可以並行執行（無依賴）
3. 每個 CL 獨立測試和提交
4. 更新相關文檔

### 完成標準
- [ ] 所有 4 個 CL 已合併
- [ ] 所有驗證測試通過
- [ ] 文檔已更新
- [ ] KPIMON 健康檢查正常工作

---

**RFC 結束**

**下一步**：等待批准後開始執行 **CL #0**（實現 KPIMON 健康檢查端點）。
