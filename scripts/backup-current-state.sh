#!/bin/bash
# O-RAN RIC Platform Backup Script

set -e

BACKUP_DIR="backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "=========================================="
echo "O-RAN RIC Platform Backup"
echo "=========================================="
echo "Creating backup in $BACKUP_DIR..."
echo ""

# 備份 Kubernetes 資源
echo "[1/6] Backing up ricplt namespace resources..."
kubectl get all -n ricplt -o yaml > "$BACKUP_DIR/ricplt-resources.yaml" 2>/dev/null || echo "  Warning: ricplt namespace may be empty"

echo "[2/6] Backing up ricxapp namespace resources..."
kubectl get all -n ricxapp -o yaml > "$BACKUP_DIR/ricxapp-resources.yaml" 2>/dev/null || echo "  Warning: ricxapp namespace may be empty"

# 備份 ConfigMaps and Secrets
echo "[3/6] Backing up ConfigMaps..."
kubectl get configmaps -n ricplt -o yaml > "$BACKUP_DIR/ricplt-configmaps.yaml" 2>/dev/null || true
kubectl get configmaps -n ricxapp -o yaml > "$BACKUP_DIR/ricxapp-configmaps.yaml" 2>/dev/null || true

# 備份 Helm releases
echo "[4/6] Backing up Helm releases..."
helm list -n ricplt -o yaml > "$BACKUP_DIR/helm-ricplt.yaml" 2>/dev/null || echo "  No Helm releases in ricplt"
helm list -n ricxapp -o yaml > "$BACKUP_DIR/helm-ricxapp.yaml" 2>/dev/null || echo "  No Helm releases in ricxapp"

# 備份 Prometheus 數據
echo "[5/6] Backing up Prometheus data..."
PROMETHEUS_POD=$(kubectl get pods -n ricplt -l app=prometheus,component=server -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [ -n "$PROMETHEUS_POD" ]; then
    kubectl exec -n ricplt "$PROMETHEUS_POD" -- tar czf - /data 2>/dev/null > "$BACKUP_DIR/prometheus-data.tar.gz" || echo "  Warning: Failed to backup Prometheus data"
else
    echo "  Prometheus pod not found, skipping data backup"
fi

# 保存當前 Git 狀態
echo "[6/6] Saving Git status..."
git status > "$BACKUP_DIR/git-status.txt" 2>/dev/null || echo "Not a git repository" > "$BACKUP_DIR/git-status.txt"
git log -5 --oneline > "$BACKUP_DIR/git-log.txt" 2>/dev/null || true

# 創建備份元數據
cat > "$BACKUP_DIR/backup-metadata.yaml" <<EOF
backup_date: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
kubernetes_version: $(kubectl version --short 2>/dev/null | grep Server || echo "Unknown")
helm_version: $(helm version --short 2>/dev/null || echo "Unknown")
backup_location: $BACKUP_DIR
components_backed_up:
  - ricplt namespace
  - ricxapp namespace
  - ConfigMaps
  - Helm releases
  - Prometheus data
  - Git status
EOF

echo ""
echo "=========================================="
echo "✅ Backup completed successfully!"
echo "=========================================="
echo "Backup location: $BACKUP_DIR"
echo ""
echo "To restore from this backup:"
echo "  bash scripts/restore-from-backup.sh $BACKUP_DIR"
echo ""
