#!/usr/bin/env bash
set -Eeuo pipefail

NAMESPACE="${NAMESPACE:-ricplt}"

echo "[INFO] Basic Near-RT RIC diagnostic for namespace: ${NAMESPACE}"
echo

echo "=== Pods (with status) ==="
kubectl get pods -n "${NAMESPACE}" -o wide || true
echo

echo "=== Recent events ==="
kubectl get events -n "${NAMESPACE}" --sort-by='.lastTimestamp' | tail -n 50 || true
echo

echo "=== Top pods (if metrics-server is installed) ==="
kubectl top pods -n "${NAMESPACE}" 2>/dev/null || echo "[INFO] kubectl top pods not available (metrics-server missing?)"

echo
echo "[INFO] Use mcp-kubernetes-server tools for deeper analysis:"
echo "       - k8s_logs"
echo "       - k8s_describe"
echo "       - k8s_events"
