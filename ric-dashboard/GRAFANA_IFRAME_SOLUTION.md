# Grafana iframe 嵌入解決方案

## 問題說明

Grafana 默認設置 `X-Frame-Options: DENY`，這會阻止 iframe 嵌入。

## 解決方案

### 方案 1: 修改 Grafana 配置（推薦）

編輯 Grafana 的 ConfigMap 或 values.yaml：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-config
  namespace: ricplt
data:
  grafana.ini: |
    [security]
    allow_embedding = true
    cookie_samesite = none
    cookie_secure = true

    [auth.anonymous]
    enabled = true
    org_role = Viewer
```

應用配置：

```bash
# 更新 ConfigMap
kubectl apply -f grafana-config.yaml

# 重啟 Grafana
kubectl rollout restart deployment/oran-grafana -n ricplt
```

### 方案 2: 通過 Nginx 代理移除 Header

更新我們的 `nginx.conf`：

```nginx
# 添加到 Grafana 代理配置
location /api/grafana/ {
    proxy_pass http://127.0.0.1:5000;

    # 移除 X-Frame-Options
    proxy_hide_header X-Frame-Options;

    # 添加允許 iframe 的 header
    add_header X-Frame-Options "SAMEORIGIN";

    # 其他代理設置...
}
```

### 方案 3: 使用 Grafana 的 Public Dashboard

在 Grafana 中設置公共儀表板：

1. 打開儀表板設置
2. 選擇 "Share" -> "Snapshot"
3. 選擇 "Publish to snapshot.raintank.io"
4. 使用公共 URL

### 方案 4: 完整的 Flask 代理方案（已實現）

更新 `api-gateway/app.py` 的 Grafana 代理：

```python
@app.route('/api/grafana/<path:path>', methods=['GET'])
def proxy_grafana(path):
    """Proxy requests to Grafana with header modifications"""
    try:
        url = f'http://{GRAFANA_SERVICE}/{path}'

        headers = {}
        if 'Authorization' in request.headers:
            headers['Authorization'] = request.headers['Authorization']

        response = requests.get(url, params=request.args, headers=headers, timeout=10)

        # 創建新的 Response 對象，移除 X-Frame-Options
        resp = Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'application/json')
        )

        # 移除阻擋 iframe 的 headers
        resp.headers.pop('X-Frame-Options', None)
        resp.headers.pop('Content-Security-Policy', None)

        # 允許 iframe 嵌入
        resp.headers['X-Frame-Options'] = 'SAMEORIGIN'

        return resp
    except Exception as e:
        logger.error(f"Error proxying to Grafana: {str(e)}")
        return jsonify({'error': f'Grafana service unavailable: {str(e)}'}), 503
```

## 推薦實施步驟

### 步驟 1: 配置 Grafana（一次性設置）

創建 Grafana 配置文件：

```bash
cat > /tmp/grafana-config.yaml << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: oran-grafana
  namespace: ricplt
data:
  grafana.ini: |
    [server]
    protocol = http
    http_port = 3000
    domain = localhost
    root_url = %(protocol)s://%(domain)s:%(http_port)s/

    [security]
    allow_embedding = true
    cookie_samesite = none
    cookie_secure = false

    [auth.anonymous]
    enabled = true
    org_name = Main Org.
    org_role = Viewer

    [auth]
    disable_login_form = false
    disable_signout_menu = false
EOF

# 應用配置
kubectl apply -f /tmp/grafana-config.yaml

# 重啟 Grafana
kubectl delete pod -n ricplt -l app.kubernetes.io/name=grafana
```

### 步驟 2: 更新 API Gateway

```bash
cd /home/mbwcl711_3060/thc1006/tmep/oran-ric-platform/ric-dashboard/api-gateway

# 更新 app.py 的 Grafana 代理函數
# （已在上面提供代碼）
```

### 步驟 3: 在 Angular 中使用

```typescript
// src/app/components/grafana-dashboard/grafana-dashboard.component.ts
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

export class GrafanaDashboardComponent {
  dashboardUrl: SafeResourceUrl;

  constructor(
    private grafanaService: GrafanaService,
    private sanitizer: DomSanitizer
  ) {}

  loadDashboard(uid: string): void {
    // 使用我們的代理 URL
    const url = `/api/grafana/d/${uid}?theme=dark&kiosk=tv&refresh=5s`;
    this.dashboardUrl = this.sanitizer.bypassSecurityTrustResourceUrl(url);
  }
}
```

```html
<!-- src/app/components/grafana-dashboard/grafana-dashboard.component.html -->
<div class="dashboard-container">
  <iframe
    [src]="dashboardUrl"
    frameborder="0"
    width="100%"
    height="800px"
    sandbox="allow-same-origin allow-scripts allow-forms">
  </iframe>
</div>
```

## 驗證步驟

### 1. 檢查 Grafana 配置

```bash
# 檢查 ConfigMap
kubectl get configmap oran-grafana -n ricplt -o yaml

# 檢查 Grafana 日誌
kubectl logs -n ricplt -l app.kubernetes.io/name=grafana
```

### 2. 測試 iframe 嵌入

```bash
# Port forward
kubectl port-forward -n ricplt svc/oran-grafana 3000:80

# 在瀏覽器控制台測試
// 打開 http://localhost:3000
// 查看 Response Headers，確認沒有 X-Frame-Options: DENY
```

### 3. 測試通過代理訪問

```bash
# 通過 Dashboard 訪問
kubectl port-forward -n ricplt svc/ric-dashboard 8080:80

# 訪問
http://localhost:8080/api/grafana/api/search
```

## 完整的解決方案代碼

### 更新後的 API Gateway

```python
# api-gateway/app.py

from flask import Response

@app.route('/api/grafana/render/<path:path>', methods=['GET'])
@app.route('/api/grafana/d/<uid>/<slug>', methods=['GET'])
@app.route('/api/grafana/<path:path>', methods=['GET', 'POST'])
def proxy_grafana(path='', uid=None, slug=None):
    """
    Proxy requests to Grafana with iframe embedding support
    Removes X-Frame-Options to allow embedding
    """
    try:
        # 構建 URL
        if uid:
            url = f'http://{GRAFANA_SERVICE}/d/{uid}/{slug or ""}'
        else:
            url = f'http://{GRAFANA_SERVICE}/{path}'

        logger.info(f"Proxying to Grafana: {url}")

        # 準備 headers
        headers = {}
        # 轉發 Authorization header（如果有）
        if 'Authorization' in request.headers:
            headers['Authorization'] = request.headers['Authorization']

        # 發送請求
        if request.method == 'GET':
            resp = requests.get(url, params=request.args, headers=headers, timeout=10, allow_redirects=True)
        else:
            resp = requests.post(url, json=request.get_json(), headers=headers, timeout=10)

        # 創建 Flask Response
        flask_response = Response(
            resp.content,
            status=resp.status_code
        )

        # 複製必要的 headers，但跳過阻擋 iframe 的
        excluded_headers = ['x-frame-options', 'content-security-policy', 'transfer-encoding', 'connection']
        for key, value in resp.headers.items():
            if key.lower() not in excluded_headers:
                flask_response.headers[key] = value

        # 允許 iframe 嵌入
        flask_response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        flask_response.headers['Access-Control-Allow-Origin'] = '*'

        return flask_response

    except requests.exceptions.RequestException as e:
        logger.error(f"Error proxying to Grafana: {str(e)}")
        return jsonify({'error': f'Grafana service unavailable: {str(e)}'}), 503
```

### Angular 組件實現

```typescript
// src/app/components/grafana-dashboard/grafana-dashboard.component.ts
import { Component, OnInit } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { GrafanaService } from '../../services/grafana.service';

@Component({
  selector: 'app-grafana-dashboard',
  templateUrl: './grafana-dashboard.component.html',
  styleUrls: ['./grafana-dashboard.component.scss']
})
export class GrafanaDashboardComponent implements OnInit {
  dashboards = [
    { name: 'Platform Overview', uid: 'oran-ric-overview' },
    { name: 'KPIMON', uid: 'kpimon-dashboard' },
    { name: 'Traffic Steering', uid: 'traffic-steering-dashboard' },
    { name: 'QoE Predictor', uid: 'qoe-predictor-dashboard' },
    { name: 'RAN Control', uid: 'rc-xapp-dashboard' },
    { name: 'Federated Learning', uid: 'federated-learning-dashboard' },
    { name: 'Dual-Path', uid: 'oran-dual-path' }
  ];

  selectedDashboard: any = null;
  dashboardUrl: SafeResourceUrl | null = null;

  constructor(
    private grafanaService: GrafanaService,
    private sanitizer: DomSanitizer
  ) {}

  ngOnInit(): void {
    // 默認加載第一個儀表板
    if (this.dashboards.length > 0) {
      this.selectDashboard(this.dashboards[0]);
    }
  }

  selectDashboard(dashboard: any): void {
    this.selectedDashboard = dashboard;

    // 使用我們的代理 URL，避免 CORS 和 X-Frame-Options 問題
    const url = `/api/grafana/d/${dashboard.uid}?theme=dark&kiosk=tv&refresh=5s`;

    // 繞過 Angular 的安全檢查
    this.dashboardUrl = this.sanitizer.bypassSecurityTrustResourceUrl(url);
  }
}
```

```html
<!-- src/app/components/grafana-dashboard/grafana-dashboard.component.html -->
<div class="grafana-container">
  <div class="dashboard-selector">
    <h2>Grafana Dashboards</h2>
    <mat-chip-listbox [(ngModel)]="selectedDashboard">
      <mat-chip-option
        *ngFor="let dashboard of dashboards"
        [value]="dashboard"
        (click)="selectDashboard(dashboard)">
        {{ dashboard.name }}
      </mat-chip-option>
    </mat-chip-listbox>
  </div>

  <mat-card *ngIf="dashboardUrl" class="dashboard-frame">
    <iframe
      [src]="dashboardUrl"
      frameborder="0"
      width="100%"
      height="800px"
      sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
      allowfullscreen>
    </iframe>
  </mat-card>
</div>
```

## 總結

解決 Grafana iframe 嵌入問題的關鍵：

1. **Grafana 配置**: 啟用 `allow_embedding = true`
2. **代理移除 Headers**: 通過 Flask 代理移除 `X-Frame-Options`
3. **Angular 安全繞過**: 使用 `DomSanitizer.bypassSecurityTrustResourceUrl()`
4. **使用 Kiosk 模式**: URL 參數 `?kiosk=tv` 提供更好的嵌入體驗

這個解決方案已經整合到我們的架構中，無需額外配置即可使用。
