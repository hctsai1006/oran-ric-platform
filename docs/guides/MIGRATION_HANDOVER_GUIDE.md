# O-RAN RIC Platform Migration - Handover Guide

**日期**: 2025-11-18
**目標**: 完整部署標準 O-RAN RIC Platform

---

##   目錄

- [1. Quick Start](#1-quick-start)
- [2. Project Overview](#2-project-overview)
- [3. Prerequisites](#3-prerequisites)
- [4. Implementation Plan](#4-implementation-plan)
- [5. PR-by-PR Execution Guide](#5-pr-by-pr-execution-guide)
- [6. Testing Checklist](#6-testing-checklist)
- [7. Troubleshooting](#7-troubleshooting)
- [8. Success Criteria](#8-success-criteria)

---

## 1. Quick Start

### 1.1 你需要知道的事


**你的任務**: 將當前**輕量化 O-RAN RIC Platform** 遷移到**符合 O-RAN 標準的完整架構**

**當前狀態**:
-  [DONE] 5 個 xApps 運行中（KPIMON, Traffic Steering, QoE Predictor, RAN Control, Federated Learning）
-  [DONE] E2 Simulator 模擬 3 Cells + 20 UEs
-  [DONE] Prometheus + Grafana 監控正常
-  [FAIL] 使用 HTTP 通訊（**非標準**）
-  [FAIL] 缺少 15+ RIC Platform 核心組件

**目標狀態**:
-  [DONE] 部署完整 RIC Platform（E2Term, E2Mgr, SubMgr, RTMgr, AppMgr, A1Mediator 等）
-  [DONE] 使用 RMR (RIC Message Router) 通訊
-  [DONE] 支援 E2AP 協議
-  [DONE] 符合 O-RAN SC J-Release 標準
-  [DONE] **零停機遷移**

### 1.2 重要文檔（必讀）

在開始之前，請閱讀以下文檔：

| 文檔 | 路徑 | 用途 |
|------|------|------|
| **RFC** | `RIC_PLATFORM_MIGRATION_RFC.md` | 完整遷移計畫（技術細節） |
| **ADR** | `docs/ADR-001-RIC-Platform-Migration.md` | 架構決策記錄（為什麼這樣做） |
| **Current Architecture** | `CURRENT_STRATEGY_AND_ARCHITECTURE.md` | 當前架構說明 |

### 1.3 Key Principles

遷移過程中，你**必須**遵守以下原則：

 [DONE] **TDD (Test-Driven Development)**:
- 先寫測試（Red）
- 部署組件（Green）
- 優化配置（Refactor）

 [DONE] **Boy Scout Rule**:
- "Leave code better than you found it"
- 遷移時同步改善代碼質量

 [DONE] **Small CLs (Small Change Lists)**:
- 每個 PR < 400 行
- 每個 PR 只做一件事
- 每個 PR 可獨立部署

 [DONE] **Parallel Change (Expand-Contract)**:
- EXPAND: 新舊系統並存
- MIGRATE: 逐步切換流量
- CONTRACT: 移除舊代碼

---

## 2. Project Overview

### 2.1 Architecture Comparison

**Before (Current)**:
```
E2 Simulator (HTTP) → xApps (HTTP) → Prometheus/Grafana
```

**After (Target)**:
```
E2 Simulator (E2AP/SCTP)
    ↓
E2 Term (E2AP Protocol Termination)
    ↓
RMR (Message Router) ← RTMgr (Routing Manager)
    ↓
├─ E2 Manager
├─ Subscription Manager
├─ App Manager
├─ A1 Mediator
└─ xApps (RMR)
    ↓
SDL (Shared Data Layer: DBaaS + Redis)
    ↓
Prometheus/Grafana + Jaeger
```

### 2.2 Components to Deploy

| Component | Version | Priority | Estimated Time |
|-----------|---------|----------|----------------|
| Redis Cluster | 3.0.0 | P0 | 2 hours |
| DBaaS | 2.0.0 | P0 | 2 hours |
| E2 Term | 3.0.0 | P0 | 4 hours |
| E2 Manager | 3.0.0 | P0 | 4 hours |
| Subscription Manager | 3.0.0 | P0 | 3 hours |
| Routing Manager | 3.0.0 | P0 | 4 hours |
| App Manager | 3.0.0 | P1 | 3 hours |
| A1 Mediator | 3.0.0 | P1 | 3 hours |
| Jaeger Adapter | 3.0.0 | P2 | 2 hours |
| VES Manager | 3.0.0 | P2 | 2 hours |
| **Total** | - | - | **~30 hours** |

**xApps Migration** (5 xApps × 3 hours = **15 hours**):
- KPIMON
- Traffic Steering
- QoE Predictor
- RAN Control
- Federated Learning

**Grand Total**: ~45 hours (約 6 個工作天)

---

## 3. Prerequisites

### 3.1 Environment Check

在開始之前，請確認以下環境條件：

```bash
# 1. Kubernetes cluster
kubectl cluster-info
# Expected: Kubernetes control plane is running

# 2. Resources
kubectl top nodes
# Expected: At least 16GB RAM, 8 CPU cores available

# 3. Helm
helm version
# Expected: v3.10+

# 4. kubectl access
kubectl get namespaces
# Expected: ricplt, ricxapp exist

# 5. Current deployments
kubectl get pods -n ricplt
kubectl get pods -n ricxapp
# Expected: Prometheus, Grafana, 5 xApps, E2 Simulator running
```

### 3.2 Setup Workspace

建立工作目錄結構：

```bash
# 進入專案目錄
cd /home/mbwcl711_3060/thc1006/oran-ric-platform

# 建立測試目錄
mkdir -p tests/{unit,integration,e2e}

# 建立配置目錄
mkdir -p config/ric-platform

# 建立備份目錄
mkdir -p backups

# 建立 versions.yaml
cat > versions.yaml <<'EOF'
# O-RAN RIC Platform Component Versions
# Pinned on: 2025-11-18
# Release: J-Release

components:
  redis:
    chart_version: "3.0.0"
    image_tag: "7.0-alpine"

  dbaas:
    chart_version: "2.0.0"
    image_tag: "0.5.3"

  e2term:
    chart_version: "3.0.0"
    image_tag: "5.5.0"

  e2mgr:
    chart_version: "3.0.0"
    image_tag: "5.4.19"

  submgr:
    chart_version: "3.0.0"
    image_tag: "0.9.0"

  rtmgr:
    chart_version: "3.0.0"
    image_tag: "0.8.2"

  appmgr:
    chart_version: "3.0.0"
    image_tag: "0.5.4"

  a1mediator:
    chart_version: "3.0.0"
    image_tag: "2.6.0"

  jaegeradapter:
    chart_version: "3.0.0"
    image_tag: "0.7.0"
EOF

# 初始化 Git (如果還沒有)
git init
git add versions.yaml
git commit -m "chore: Add component version pinning"
```

### 3.3 Backup Current State

**非常重要**: 在開始任何變更前，備份當前狀態！

```bash
# 備份腳本
cat > scripts/backup-current-state.sh <<'EOF'
#!/bin/bash

BACKUP_DIR="backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Creating backup in $BACKUP_DIR..."

# 備份 Kubernetes 資源
kubectl get all -n ricplt -o yaml > "$BACKUP_DIR/ricplt-resources.yaml"
kubectl get all -n ricxapp -o yaml > "$BACKUP_DIR/ricxapp-resources.yaml"

# 備份 ConfigMaps and Secrets
kubectl get configmaps -n ricplt -o yaml > "$BACKUP_DIR/ricplt-configmaps.yaml"
kubectl get configmaps -n ricxapp -o yaml > "$BACKUP_DIR/ricxapp-configmaps.yaml"

# 備份 Helm releases
helm list -n ricplt -o yaml > "$BACKUP_DIR/helm-ricplt.yaml"
helm list -n ricxapp -o yaml > "$BACKUP_DIR/helm-ricxapp.yaml"

# 備份 Redis 數據（如果有）
if kubectl get pods -n ricplt | grep -q redis; then
    kubectl exec -n ricplt redis-cluster-0 -- redis-cli --rdb /data/backup.rdb || true
fi

# 備份 Prometheus 數據
kubectl exec -n ricplt -l app=prometheus,component=server -- tar czf - /data \
    > "$BACKUP_DIR/prometheus-data.tar.gz" || true

echo " [DONE] Backup completed: $BACKUP_DIR"
echo "To restore: bash scripts/restore-from-backup.sh $BACKUP_DIR"
EOF

chmod +x scripts/backup-current-state.sh

# 執行備份
bash scripts/backup-current-state.sh
```

---

## 4. Implementation Plan

### 4.1 Timeline Overview

| Week | Phase | Tasks | PRs |
|------|-------|-------|-----|
| 1-2 | **Phase 0: Preparation** | 環境準備、測試框架、文檔 | - |
| 3-4 | **Phase 1: Infrastructure** | Redis + DBaaS | PR-01, PR-02 |
| 5-6 | **Phase 2: E2 Core** | E2Term + E2Mgr + SubMgr | PR-03, PR-04, PR-05 |
| 7-8 | **Phase 3: RMR** | RTMgr + RMR setup | PR-06 |
| 9-12 | **Phase 4: xApps Migration** | 5 xApps遷移（平行變更） | PR-07 ~ PR-26 |
| 13-14 | **Phase 5: Additional** | AppMgr + A1Med + Jaeger | PR-27 ~ PR-29 |
| 15-16 | **Phase 6: Validation** | E2E 測試 + 文檔 + 優化 | - |

### 4.2 PR Dependency Graph

```
Phase 1:
  PR-01 (Redis) ──┐
                  ├─→ PR-02 (DBaaS)
                  │
Phase 2:          ↓
  PR-03 (E2Term) ←┤
  PR-04 (E2Mgr)  ←┤
                  │
                  ↓
  PR-05 (SubMgr) ←┴─ (depends on E2Term + E2Mgr)

Phase 3:
  PR-06 (RTMgr) ←── (depends on DBaaS)

Phase 4:
  PR-07 (KPIMON RMR) ←─┐
  PR-08 (KPIMON HTTP deprecate) ←┤
  PR-09 (E2Sim E2AP) ←─┤
  PR-10 (KPIMON HTTP remove) ←─┤
                               │
  PR-11 ~ PR-14 (其他 xApps) ←─┤
                               │
Phase 5:                        │
  PR-27 (AppMgr) ←──────────────┤
  PR-28 (A1Med)  ←──────────────┤
  PR-29 (Jaeger) ←──────────────┘
```

### 4.3 Rollback Points

每個階段結束後，確保可以 rollback：

| Rollback Point | Command | Verification |
|----------------|---------|--------------|
| **After Phase 1** | `helm uninstall r4-dbaas r4-redis-cluster -n ricplt` | `kubectl get pods -n ricplt` |
| **After Phase 2** | `helm uninstall r4-e2term r4-e2mgr r4-submgr -n ricplt` | `kubectl get pods -n ricplt` |
| **After Phase 3** | `helm uninstall r4-rtmgr -n ricplt` | `kubectl get pods -n ricplt` |
| **During Phase 4** | `kubectl set env deployment/kpimon ENABLE_RMR=false` | Check logs |
| **After Phase 5** | `helm uninstall r4-appmgr r4-a1mediator -n ricplt` | `kubectl get pods -n ricplt` |

---

## 5. PR-by-PR Execution Guide

### Phase 0: Preparation (Week 1-2)

#### Task 0.1: 建立測試框架

```bash
# 建立單元測試
cat > tests/unit/test_dbaas_connection.py <<'EOF'
import pytest
import redis

def test_dbaas_connection():
    """Test DBaaS can connect to Redis"""
    client = redis.Redis(
        host='dbaas-tcp.ricplt.svc.cluster.local',
        port=6379,
        socket_connect_timeout=5
    )

    # Test SET
    assert client.set('test_key', 'test_value')

    # Test GET
    assert client.get('test_key') == b'test_value'

    # Cleanup
    client.delete('test_key')

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
EOF

# 建立整合測試
cat > tests/integration/test_rmr_connectivity.sh <<'EOF'
#!/bin/bash
set -e

echo "Testing RMR connectivity..."

# Test E2Term → E2Mgr
echo "Testing E2Term → E2Mgr..."
kubectl exec -n ricplt deployment/e2term -- \
  timeout 10 nc -zv e2mgr.ricplt.svc.cluster.local 3801

echo " [DONE] E2Term → E2Mgr: OK"

# Test SubMgr → E2Term
echo "Testing SubMgr → E2Term..."
kubectl exec -n ricplt deployment/submgr -- \
  timeout 10 nc -zv e2term.ricplt.svc.cluster.local 38000

echo " [DONE] SubMgr → E2Term: OK"

echo " [DONE] All RMR connectivity tests passed"
EOF

chmod +x tests/integration/test_rmr_connectivity.sh

# 建立 E2E 測試
cat > tests/e2e/test_complete_flow.py <<'EOF'
import pytest
import requests
import time

def test_e2_to_prometheus_flow():
    """
    Test: E2 Simulator → E2Term → KPIMON → Prometheus
    """

    # Wait for E2 Simulator to send data
    time.sleep(10)

    # Check Prometheus for KPIMON metrics
    response = requests.get(
        'http://localhost:9090/api/v1/query',
        params={'query': 'kpimon_messages_received_total'}
    )

    assert response.status_code == 200
    data = response.json()['data']['result']

    assert len(data) > 0, "No KPIMON metrics found"
    assert float(data[0]['value'][1]) > 0, "No messages received"

    print(" [DONE] E2E test passed")

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
EOF

# 安裝測試依賴
pip install pytest requests redis
```

#### Task 0.2: 建立 CI/CD Pipeline

```bash
# 建立 GitHub Actions workflow
mkdir -p .github/workflows

cat > .github/workflows/ric-platform-ci.yaml <<'EOF'
name: RIC Platform CI

on:
  pull_request:
    branches: [ main ]
  push:
    branches: [ main ]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install pytest requests redis

    - name: Run unit tests
      run: |
        pytest tests/unit/ -v

  lint:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Lint shell scripts
      run: |
        sudo apt-get install shellcheck
        find . -name "*.sh" -exec shellcheck {} \;

    - name: Lint Python code
      run: |
        pip install flake8
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
EOF

git add .github/workflows/
git commit -m "ci: Add GitHub Actions workflow"
```

---

### Phase 1: Infrastructure Layer (Week 3-4)

#### PR-01: Deploy Redis Cluster

**目標**: 部署 Redis Cluster 作為 SDL backend

**TDD - Step 1: RED (寫測試，預期失敗)**

```bash
cat > tests/unit/test_redis_cluster.sh <<'EOF'
#!/bin/bash

echo "Testing Redis Cluster..."

# Test Redis cluster exists
kubectl get statefulset -n ricplt redis-cluster

# Test Redis is accessible
kubectl exec -n ricplt redis-cluster-0 -- redis-cli ping

echo " [DONE] Redis Cluster test passed"
EOF

chmod +x tests/unit/test_redis_cluster.sh

# Run test (應該失敗，因為還沒部署)
bash tests/unit/test_redis_cluster.sh
# Expected: FAIL
```

**TDD - Step 2: GREEN (部署組件，測試通過)**

```bash
# 建立 Redis 配置
cat > config/ric-platform/redis-values.yaml <<'EOF'
cluster:
  enabled: true
  nodes: 3

persistence:
  enabled: true
  storageClass: "local-path"
  size: 10Gi

resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "2Gi"
    cpu: "1000m"

redis:
  configmap: |
    maxmemory 2gb
    maxmemory-policy allkeys-lru
    save 900 1
    save 300 10
    save 60 10000
    appendonly yes
    appendfsync everysec
EOF

# 部署 Redis Cluster
helm install r4-redis-cluster \
  ./ric-dep/helm/redis-cluster \
  --namespace ricplt \
  --values config/ric-platform/redis-values.yaml \
  --wait \
  --timeout 300s

# 驗證部署
kubectl wait --for=condition=ready pod \
  -l app=redis-cluster \
  -n ricplt \
  --timeout=300s

# Run test again (應該通過)
bash tests/unit/test_redis_cluster.sh
# Expected: PASS
```

**TDD - Step 3: REFACTOR (優化)**

```bash
# Performance test
kubectl run -it --rm redis-benchmark \
  --image=redis:7-alpine \
  --restart=Never \
  -- redis-benchmark -h redis-cluster.ricplt.svc.cluster.local -p 6379 -n 100000

# Expected: > 50k requests/sec
```

**Git Commit**:

```bash
git add config/ric-platform/redis-values.yaml
git add tests/unit/test_redis_cluster.sh
git commit -m "feat: Deploy Redis Cluster for SDL

- Add Redis Cluster with 3 nodes
- Enable persistence with 10Gi storage
- Configure memory limits and eviction policy
- Add unit tests for Redis connectivity

Test: bash tests/unit/test_redis_cluster.sh
Benchmark: > 50k ops/sec

Refs: ADR-001, RIC-MIGRATION-2025-001"

git push origin feature/pr-01-redis-cluster
```

**Create PR**: 在 GitHub 上創建 PR #1

---

#### PR-02: Deploy DBaaS

**目標**: 部署 DBaaS (Database as a Service) - SDL 前端

**TDD - Step 1: RED**

```bash
cat > tests/unit/test_dbaas_deployment.sh <<'EOF'
#!/bin/bash

echo "Testing DBaaS deployment..."

# Test DBaaS service exists
kubectl get svc -n ricplt dbaas-tcp

# Test DBaaS is accessible
kubectl run -it --rm test-dbaas \
  --image=redis:7-alpine \
  --restart=Never \
  -- redis-cli -h dbaas-tcp.ricplt.svc.cluster.local -p 6379 ping

echo " [DONE] DBaaS test passed"
EOF

chmod +x tests/unit/test_dbaas_deployment.sh

# Run test (should fail)
bash tests/unit/test_dbaas_deployment.sh
# Expected: FAIL
```

**TDD - Step 2: GREEN**

```bash
# 建立 DBaaS 配置
cat > config/ric-platform/dbaas-values.yaml <<'EOF'
image:
  repository: nexus3.o-ran-sc.org:10002/o-ran-sc/ric-plt-dbaas
  tag: "0.5.3"
  pullPolicy: IfNotPresent

service:
  tcp:
    port: 6379
    type: ClusterIP

redis:
  # 連接到 Redis Cluster
  address: "redis-cluster.ricplt.svc.cluster.local:6379"
  clusterAddrList: "redis-cluster-0.redis-cluster.ricplt.svc.cluster.local:6379,redis-cluster-1.redis-cluster.ricplt.svc.cluster.local:6379,redis-cluster-2.redis-cluster.ricplt.svc.cluster.local:6379"

resources:
  requests:
    memory: "256Mi"
    cpu: "200m"
  limits:
    memory: "512Mi"
    cpu: "500m"

replicas: 2  # HA
EOF

# 部署 DBaaS
helm install r4-dbaas \
  ./ric-dep/helm/dbaas \
  --namespace ricplt \
  --values config/ric-platform/dbaas-values.yaml \
  --wait \
  --timeout 300s

# 驗證
kubectl wait --for=condition=ready pod \
  -l app=dbaas \
  -n ricplt \
  --timeout=300s

# Run test
bash tests/unit/test_dbaas_deployment.sh
# Expected: PASS
```

**Integration Test with Redis**:

```bash
# Python 整合測試
python tests/unit/test_dbaas_connection.py
# Expected: PASS
```

**Git Commit & PR**:

```bash
git add config/ric-platform/dbaas-values.yaml
git add tests/unit/test_dbaas_deployment.sh
git commit -m "feat: Deploy DBaaS for Shared Data Layer

- Add DBaaS service with 2 replicas (HA)
- Connect to Redis Cluster
- Configure resource limits
- Add unit and integration tests

Dependencies: PR-01 (Redis Cluster)
Test: bash tests/unit/test_dbaas_deployment.sh

Refs: ADR-001, RIC-MIGRATION-2025-001"

git push origin feature/pr-02-dbaas
```

**Create PR**: PR #2

---

### Phase 2: E2 Core Components (Week 5-6)

#### PR-03: Deploy E2 Term

**目標**: 部署 E2 Termination - E2AP 協議終端

**Boy Scout Rule**: 同時建立標準化的 Helm values template

**TDD - Step 1: RED**

```bash
cat > tests/unit/test_e2term_deployment.sh <<'EOF'
#!/bin/bash

echo "Testing E2 Term deployment..."

# Test E2 Term service exists
kubectl get svc -n ricplt e2term-sctp-alpha

# Test SCTP port
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
nc -zv -w 5 $NODE_IP 36422

echo " [DONE] E2 Term test passed"
EOF

chmod +x tests/unit/test_e2term_deployment.sh

bash tests/unit/test_e2term_deployment.sh
# Expected: FAIL
```

**TDD - Step 2: GREEN**

```bash
cat > config/ric-platform/e2term-values.yaml <<'EOF'
image:
  repository: nexus3.o-ran-sc.org:10002/o-ran-sc/ric-plt-e2
  tag: "5.5.0"
  pullPolicy: IfNotPresent

service:
  sctp:
    alpha:
      type: NodePort
      port: 36422
      nodePort: 36422
  rmr:
    data:
      port: 38000
    route:
      port: 4561

env:
  # RMR configuration
  - name: RMR_RTG_SVC
    value: "rtmgr.ricplt.svc.cluster.local:4561"
  - name: RMR_SEED_RT
    value: "/config/routing.txt"

  # DBaaS connection
  - name: DBAAS_SERVICE_HOST
    value: "dbaas-tcp.ricplt.svc.cluster.local"
  - name: DBAAS_SERVICE_PORT
    value: "6379"

  # E2 configuration
  - name: E2TERM_POD_NAME
    valueFrom:
      fieldRef:
        fieldPath: metadata.name

resources:
  requests:
    memory: "512Mi"
    cpu: "400m"
  limits:
    memory: "1Gi"
    cpu: "1000m"

replicas: 1

# RMR routing seed (initial)
rmrRoutingSeed: |
  newrt|start
  rte|12010|service-ricplt-e2mgr-rmr.ricplt:3801
  rte|12020|service-ricplt-submgr-rmr.ricplt:4560
  newrt|end
EOF

# 部署 E2 Term
helm install r4-e2term \
  ./ric-dep/helm/e2term \
  --namespace ricplt \
  --values config/ric-platform/e2term-values.yaml \
  --wait \
  --timeout 300s

# 驗證
kubectl wait --for=condition=ready pod \
  -l app=ricplt-e2term \
  -n ricplt \
  --timeout=300s

# Run test
bash tests/unit/test_e2term_deployment.sh
# Expected: PASS
```

**Boy Scout Rule**: 同時改善 E2 Simulator logging

```python
# simulator/e2-simulator/src/e2_simulator.py
# 添加 structured logging

import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Replace print statements with logger
# Before: print(f"Generated KPI for {cell_id}/{ue_id}")
# After:  logger.info("Generated KPI", extra={'cell_id': cell_id, 'ue_id': ue_id})
```

**Git Commit & PR**:

```bash
git add config/ric-platform/e2term-values.yaml
git add tests/unit/test_e2term_deployment.sh
git add simulator/e2-simulator/src/e2_simulator.py  # Boy Scout improvement
git commit -m "feat: Deploy E2 Termination for E2AP protocol

- Add E2 Term with SCTP NodePort (36422)
- Configure RMR routing
- Connect to DBaaS for state storage
- Add deployment tests

Boy Scout Rule:
- Improve E2 Simulator logging (structured logs)

Dependencies: PR-02 (DBaaS)
Test: bash tests/unit/test_e2term_deployment.sh

Refs: ADR-001, RIC-MIGRATION-2025-001"

git push origin feature/pr-03-e2term
```

**Create PR**: PR #3

---

#### PR-04 ~ PR-06: 其他核心組件

使用相同的模式部署：
- **PR-04**: E2 Manager (類似 PR-03)
- **PR-05**: Subscription Manager (依賴 PR-03, PR-04)
- **PR-06**: Routing Manager (依賴 PR-02)

**每個 PR 都遵循**:
1. TDD (Red → Green → Refactor)
2. Boy Scout Rule (同步改善相關代碼)
3. Small CL (< 400 lines)
4. 完整測試和文檔

---

### Phase 4: xApps Migration (Week 9-12)

這是**最關鍵**的階段，使用 **Parallel Change** 模式。

#### PR-07: KPIMON - Add RMR Support (EXPAND)

**目標**: 為 KPIMON 添加 RMR 接口，但保留 HTTP 接口

**實作步驟**:

```bash
# Step 1: 安裝 RMR library
cat > xapps/kpimon-go-xapp/requirements.txt <<'EOF'
# 現有依賴
Flask==3.0.0
prometheus-client==0.19.0
redis==5.0.1

# 新增 RMR 支援
rmr==4.9.1
ricxappframe==3.2.0
EOF

# Step 2: 建立 RMR handler
cat > xapps/kpimon-go-xapp/src/rmr_handler.py <<'EOF'
"""
RMR Handler for KPIMON
Handles E2 Indication messages via RMR
"""
import json
import logging
from ricxappframe.xapp_rmr import RMRXapp

logger = logging.getLogger(__name__)

# RMR Message Types (O-RAN E2AP)
RIC_INDICATION = 12050

class KPIMONRMRHandler:
    def __init__(self, config_file, process_callback):
        """
        Initialize RMR handler

        Args:
            config_file: Path to xApp config
            process_callback: Function to process indication
        """
        self.process_callback = process_callback

        self.xapp = RMRXapp(
            default_handler=self.default_handler,
            config_file=config_file
        )

        logger.info("RMR handler initialized")

    def default_handler(self, summary, sbuf):
        """
        Default RMR message handler

        Args:
            summary: Message summary
            sbuf: RMR message buffer
        """
        msg_type = summary['message type']

        logger.debug(f"Received RMR message: type={msg_type}")

        if msg_type == RIC_INDICATION:
            try:
                # Parse E2AP message
                payload = json.loads(sbuf.get_payload())

                # Process indication (shared logic)
                self.process_callback(payload, interface='rmr')

            except Exception as e:
                logger.exception(f"Error processing RMR indication: {e}")

        # Free RMR buffer
        self.xapp.rmr_free(sbuf)

    def run(self):
        """Start RMR listener (blocking)"""
        logger.info("Starting RMR listener...")
        self.xapp.run()
EOF

# Step 3: 修改 main.py 支援雙接口
cat > xapps/kpimon-go-xapp/src/main.py <<'EOF'
"""
KPIMON xApp - Main Entry Point

Supports both HTTP and RMR interfaces during migration.
"""
import os
import sys
import threading
import logging
from flask import Flask, request, jsonify
from prometheus_client import Counter, Histogram, generate_latest
import time

# Import RMR handler
from rmr_handler import KPIMONRMRHandler

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
messages_received = Counter(
    'kpimon_messages_received_total',
    'Total messages received',
    ['interface']  # 'http' or 'rmr'
)

processing_duration = Histogram(
    'kpimon_processing_duration_seconds',
    'Message processing duration',
    ['interface', 'status']
)

# Flask app (HTTP interface)
app = Flask(__name__)

def process_indication(data, interface='http'):
    """
    Shared processing logic for HTTP and RMR

    Args:
        data: Indication data (dict)
        interface: 'http' or 'rmr'
    """
    start_time = time.time()

    try:
        # Validate
        if not data or 'measurements' not in data:
            logger.warning(f"Invalid indication from {interface}", extra={'data': data})
            messages_received.labels(interface=interface, status='error').inc()
            return False

        # Process KPI measurements
        cell_id = data.get('cell_id', 'unknown')
        ue_id = data.get('ue_id', 'unknown')

        for measurement in data['measurements']:
            # Update Prometheus metrics
            kpi_gauge.labels(
                cell_id=cell_id,
                kpi_type=measurement['name']
            ).set(measurement['value'])

        # Success
        duration = time.time() - start_time
        processing_duration.labels(
            interface=interface,
            status='success'
        ).observe(duration)
        messages_received.labels(interface=interface).inc()

        logger.info(
            f"Processed indication from {interface}",
            extra={
                'cell_id': cell_id,
                'ue_id': ue_id,
                'duration_ms': duration * 1000
            }
        )

        return True

    except Exception as e:
        logger.exception(f"Error processing indication from {interface}: {e}")
        processing_duration.labels(
            interface=interface,
            status='error'
        ).observe(time.time() - start_time)
        messages_received.labels(interface=interface, status='error').inc()
        return False

@app.route('/e2/indication', methods=['POST'])
def handle_http_indication():
    """
    HTTP endpoint for E2 Indication (DEPRECATED)

    NOTE: This endpoint will be removed in v2.0.0
    Use RMR interface instead
    """
    data = request.json

    success = process_indication(data, interface='http')

    if success:
        return jsonify({'status': 'success'}), 200
    else:
        return jsonify({'error': 'Processing failed'}), 500

@app.route('/ric/v1/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()

def run_http_server():
    """Run Flask HTTP server"""
    logger.info("Starting HTTP server on :8080...")
    app.run(host='0.0.0.0', port=8080)

def main():
    """Main entry point"""
    logger.info("Starting KPIMON xApp...")

    # Check RMR mode
    enable_rmr = os.getenv('ENABLE_RMR', 'false').lower() == 'true'

    if enable_rmr:
        logger.info("RMR mode ENABLED (parallel with HTTP)")

        # Start HTTP in background thread
        http_thread = threading.Thread(target=run_http_server, daemon=True)
        http_thread.start()

        # Start RMR handler (blocking)
        rmr_handler = KPIMONRMRHandler(
            config_file='config/config.yaml',
            process_callback=process_indication
        )
        rmr_handler.run()

    else:
        logger.info("RMR mode DISABLED (HTTP only)")
        # HTTP only
        run_http_server()

if __name__ == '__main__':
    main()
EOF

# Step 4: 更新 Deployment
cat > xapps/kpimon-go-xapp/deploy/deployment.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kpimon
  namespace: ricxapp
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kpimon
  template:
    metadata:
      labels:
        app: kpimon
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/ric/v1/metrics"
    spec:
      containers:
      - name: kpimon
        image: localhost:5000/kpimon:latest
        ports:
        - containerPort: 8080  # HTTP (legacy)
          name: http
        - containerPort: 4560  # RMR data (new)
          name: rmr-data
        - containerPort: 4561  # RMR route (new)
          name: rmr-route
        env:
        # Feature flag: Enable RMR (parallel with HTTP)
        - name: ENABLE_RMR
          value: "true"

        # RMR configuration
        - name: RMR_RTG_SVC
          value: "rtmgr.ricplt.svc.cluster.local:4561"
        - name: RMR_SEED_RT
          value: "/config/routing.txt"

        volumeMounts:
        - name: rmr-config
          mountPath: /config

        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "512Mi"
            cpu: "500m"

      volumes:
      - name: rmr-config
        configMap:
          name: kpimon-rmr-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: kpimon-rmr-config
  namespace: ricxapp
data:
  config.yaml: |
    # xApp configuration
    name: kpimon
    version: 1.0.0
    messaging:
      ports:
        - name: rmr-data
          port: 4560
        - name: rmr-route
          port: 4561

  routing.txt: |
    newrt|start
    # RIC Indication messages
    rte|12050|service-ricplt-e2term-rmr-alpha.ricplt:38000
    newrt|end
EOF

# Step 5: 建立測試
cat > tests/integration/test_kpimon_rmr.sh <<'EOF'
#!/bin/bash

echo "Testing KPIMON RMR interface..."

# Check RMR ports are open
kubectl exec -n ricxapp deployment/kpimon -- nc -zv localhost 4560
kubectl exec -n ricxapp deployment/kpimon -- nc -zv localhost 4561

# Check logs for RMR initialization
kubectl logs -n ricxapp deployment/kpimon | grep "RMR handler initialized"

echo " [DONE] KPIMON RMR test passed"
EOF

chmod +x tests/integration/test_kpimon_rmr.sh
```

**Build & Deploy**:

```bash
# Build KPIMON image
cd xapps/kpimon-go-xapp
docker build -t localhost:5000/kpimon:latest .
docker push localhost:5000/kpimon:latest

# Deploy
kubectl apply -f deploy/deployment.yaml

# Verify
kubectl rollout status deployment/kpimon -n ricxapp

# Test
bash ../../tests/integration/test_kpimon_rmr.sh
# Expected: PASS
```

**Git Commit & PR**:

```bash
git add xapps/kpimon-go-xapp/
git add tests/integration/test_kpimon_rmr.sh
git commit -m "feat(kpimon): Add RMR support (parallel change - EXPAND)

Implement parallel change pattern for KPIMON migration:

EXPAND Phase:
- Add RMR handler alongside HTTP endpoint
- Install ricxappframe and rmr libraries
- Support both interfaces via ENABLE_RMR feature flag
- Add RMR ports (4560, 4561) to deployment
- Configure RMR routing

Shared Logic:
- Extract process_indication() for code reuse
- Metrics track both 'http' and 'rmr' interfaces

Testing:
- Integration test for RMR connectivity
- Metrics validation for dual interface

Boy Scout Rule:
- Structured logging
- Prometheus metrics labels
- Input validation
- Error handling

Dependencies: PR-06 (RTMgr)
Test: bash tests/integration/test_kpimon_rmr.sh

Next PR: PR-08 (Deprecate HTTP)


git push origin feature/pr-07-kpimon-rmr
```

**Create PR**: PR #7

---

#### PR-08: E2 Simulator - Add E2AP Support (EXPAND)

**目標**: E2 Simulator 支援 E2AP 協議，雙重發送（HTTP + E2AP）

```bash
# 使用類似模式
# 1. TDD: 先寫測試
# 2. 實作 E2AP encoder (使用 asn1c)
# 3. 添加 RMR sending
# 4. Feature flag 控制流量比例
# 5. Boy Scout: 改善代碼質量
```

---

#### PR-09 ~ PR-10: KPIMON - Canary & Contract

**PR-09**: 逐步增加 RMR traffic ratio (MIGRATE)
```bash
# Week 9: 10% RMR
kubectl set env deployment/e2-simulator RMR_TRAFFIC_RATIO=0.1

# Week 10: 50% RMR
kubectl set env deployment/e2-simulator RMR_TRAFFIC_RATIO=0.5

# Week 11: 100% RMR
kubectl set env deployment/e2-simulator RMR_TRAFFIC_RATIO=1.0
```

**PR-10**: 移除 HTTP endpoint (CONTRACT)
```python
# Remove HTTP Flask code
# Keep only RMR handler
```

---

### Phase 5-6: Final Steps (Week 13-16)

**PR-27**: App Manager
**PR-28**: A1 Mediator
**PR-29**: Jaeger Adapter

**Final Tasks**:
- Complete E2E testing
- Performance benchmarking
- Documentation update
- Team training
- Production readiness review

---

## 6. Testing Checklist

每個 PR 合併前，確保通過以下檢查：

### Unit Tests
- [ ] Component deployment test passes
- [ ] Service connectivity test passes
- [ ] Configuration validation passes

### Integration Tests
- [ ] RMR connectivity tests pass (if applicable)
- [ ] DBaaS integration tests pass
- [ ] Component interaction tests pass

### E2E Tests
- [ ] Complete data flow test passes
- [ ] Prometheus metrics visible
- [ ] Grafana dashboards updated

### Code Quality
- [ ] Boy Scout Rule applied
- [ ] Structured logging added
- [ ] Prometheus metrics added
- [ ] Error handling comprehensive

### Documentation
- [ ] README updated
- [ ] Configuration documented
- [ ] Deployment guide updated
- [ ] Rollback procedure tested

### Performance
- [ ] Resource usage acceptable
- [ ] Latency < 100ms (p95)
- [ ] Throughput meets requirements

---

## 7. Troubleshooting

### Common Issues

#### Issue 1: RMR Connection Refused

**症狀**:
```
Error: connection refused
RMR not connecting to RTMgr
```

**解決方案**:
```bash
# 1. 檢查 RTMgr 是否運行
kubectl get pods -n ricplt | grep rtmgr

# 2. 檢查 RMR_RTG_SVC 環境變數
kubectl describe pod <xapp-pod> -n ricxapp | grep RMR_RTG_SVC

# 3. 檢查 routing table
kubectl logs -n ricplt deployment/rtmgr | grep "route table"

# 4. 檢查 port binding
kubectl exec -n ricxapp <xapp-pod> -- netstat -tlnp | grep 4560
```

#### Issue 2: E2AP Encoding Failure

**症狀**:
```
ASN.1 sanity check failure
RAN_FUNC_ID check failed
```

**解決方案**:
```bash
# 添加 RAN_FUNC_ID 環境變數
kubectl set env deployment/e2-simulator RAN_FUNC_ID=1

# 驗證
kubectl logs -n ricxapp e2-simulator | grep "RAN_FUNC_ID"
```

#### Issue 3: DBaaS Performance Issues

**症狀**:
```
High latency when accessing SDL
Redis connection timeout
```

**解決方案**:
```bash
# 1. 檢查 Redis cluster 狀態
kubectl exec -n ricplt redis-cluster-0 -- redis-cli cluster info

# 2. 檢查 DBaaS logs
kubectl logs -n ricplt deployment/dbaas

# 3. 增加 Redis resources
helm upgrade r4-redis-cluster ./ric-dep/helm/redis-cluster \
  --set resources.limits.memory=4Gi
```

### Rollback Procedures

參考 [RFC Section 8: Rollback Plan](./RIC_PLATFORM_MIGRATION_RFC.md#8-rollback-plan)

---

## 8. Success Criteria

### Technical Success

遷移完成後，確保：

- [ ]  [DONE] All 15+ RIC Platform components deployed
- [ ]  [DONE] All components healthy (`kubectl get pods -n ricplt`)
- [ ]  [DONE] RMR connectivity 100% (`bash tests/integration/test_rmr_connectivity.sh`)
- [ ]  [DONE] All 5 xApps migrated to RMR
- [ ]  [DONE] E2 Simulator uses E2AP protocol
- [ ]  [DONE] SDL performance > 50k ops/sec
- [ ]  [DONE] E2E latency < 100ms (p95)
- [ ]  [DONE] Zero downtime achieved
- [ ]  [DONE] Test coverage > 80%

### Operational Success

- [ ]  [DONE] All documentation complete
- [ ]  [DONE] Grafana dashboards operational
- [ ]  [DONE] Alerting rules configured
- [ ]  [DONE] Rollback procedure tested
- [ ]  [DONE] Team training completed

### Compliance Success

- [ ]  [DONE] O-RAN SC J-Release compliant
- [ ]  [DONE] E2AP v2.0+ support
- [ ]  [DONE] A1 v1.1+ functional
- [ ]  [DONE] No critical vulnerabilities

---

## 9. Final Notes


親愛的接手者：

1. **請先閱讀所有文檔** - 特別是 RFC 和 ADR
3. **小步前進** - 每個 PR 保持小而聚焦
4. **測試先行** - 永遠使用 TDD
5. **持續改善** - 應用 Boy Scout Rule
6. **記錄一切** - 更新文檔和 Git commit messages
7. **尋求幫助** - 遇到問題查閱 Troubleshooting 或參考 O-RAN SC 文檔

### Useful Commands

```bash
# 查看所有 pods 狀態
kubectl get pods -A

# 查看特定組件日誌
kubectl logs -n ricplt deployment/<component> --tail=100 -f

# 查看 Prometheus metrics
kubectl port-forward -n ricplt svc/r4-infrastructure-prometheus-server 9090:80
# 訪問 http://localhost:9090

# 查看 Grafana
kubectl port-forward -n ricplt svc/oran-grafana 3000:80
# 訪問 http://localhost:3000

# 快速檢查所有 Helm releases
helm list -A

# 運行所有測試
bash tests/unit/*.sh
bash tests/integration/*.sh
pytest tests/e2e/ -v
```

### Emergency Contacts

- **O-RAN SC Community**: https://wiki.o-ran-sc.org/
- **O-RAN SC Gerrit**: https://gerrit.o-ran-sc.org/
- **O-RAN SC Documentation**: https://docs.o-ran-sc.org/

---

**祝你成功！ **

如果遇到任何問題，記得：
1. 檢查日誌
2. 查閱文檔
3. 運行測試
4. 如果真的卡住了，rollback 並重新開始

這是一個大型遷移項目，需要耐心和細心。相信自己，一步一步來！

---

**Handover Complete**  [DONE]

**Date**: 2025-11-18
**Prepared by**: 蔡秀吉 (thc1006)
**Status**: Ready for Handover

---

## Appendix: Quick Reference

### File Structure
```
oran-ric-platform/
├── RIC_PLATFORM_MIGRATION_RFC.md       # 完整 RFC
├── MIGRATION_HANDOVER_GUIDE.md         # 本文件
├── docs/
│   └── ADR-001-RIC-Platform-Migration.md  # ADR
├── config/
│   └── ric-platform/                   # Helm values
├── tests/
│   ├── unit/                           # 單元測試
│   ├── integration/                    # 整合測試
│   └── e2e/                            # E2E 測試
├── ric-dep/
│   └── helm/                           # Helm charts
├── xapps/                              # xApps source
└── versions.yaml                       # 版本固定
```

### Key Environment Variables
```bash
# RMR Configuration
RMR_RTG_SVC=rtmgr.ricplt.svc.cluster.local:4561
RMR_SEED_RT=/config/routing.txt

# Feature Flags
ENABLE_RMR=true
RMR_TRAFFIC_RATIO=0.5

# E2 Configuration
RAN_FUNC_ID=1
E2TERM_POD_NAME=<pod-name>

# DBaaS
DBAAS_SERVICE_HOST=dbaas-tcp.ricplt.svc.cluster.local
DBAAS_SERVICE_PORT=6379
```

### Prometheus Queries
```promql
# KPIMON message rate
rate(kpimon_messages_received_total[5m])

# RMR vs HTTP traffic
sum(rate(kpimon_messages_received_total{interface="rmr"}[5m]))
sum(rate(kpimon_messages_received_total{interface="http"}[5m]))

# Processing latency (p95)
histogram_quantile(0.95, rate(kpimon_processing_duration_seconds_bucket[5m]))

# Error rate
rate(kpimon_messages_received_total{status="error"}[5m])
```
