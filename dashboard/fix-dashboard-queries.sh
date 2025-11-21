#!/bin/bash
# Fix dashboard queries to only count pods with value=1

sed -i 's/count(kube_pod_status_phase{namespace="ricplt",phase="Running"})/count(kube_pod_status_phase{namespace="ricplt",phase="Running"}==1)/g' /home/thc1006/dev/oran-ric-platform/dashboard/oran-ric-dashboard-v2.json

sed -i 's/count(kube_pod_status_phase{namespace="ricxapp",phase="Running"})/count(kube_pod_status_phase{namespace="ricxapp",phase="Running"}==1)/g' /home/thc1006/dev/oran-ric-platform/dashboard/oran-ric-dashboard-v2.json

sed -i 's/count(kube_pod_status_phase{namespace="ricplt",phase="Pending"})/count(kube_pod_status_phase{namespace="ricplt",phase="Pending"}==1)/g' /home/thc1006/dev/oran-ric-platform/dashboard/oran-ric-dashboard-v2.json

sed -i 's/count(kube_pod_status_phase{namespace="ricxapp",phase="Pending"})/count(kube_pod_status_phase{namespace="ricxapp",phase="Pending"}==1)/g' /home/thc1006/dev/oran-ric-platform/dashboard/oran-ric-dashboard-v2.json

sed -i 's/count(kube_pod_status_phase{namespace="ricplt",phase="Failed"})/count(kube_pod_status_phase{namespace="ricplt",phase="Failed"}==1)/g' /home/thc1006/dev/oran-ric-platform/dashboard/oran-ric-dashboard-v2.json

sed -i 's/count(kube_pod_status_phase{namespace="ricxapp",phase="Failed"})/count(kube_pod_status_phase{namespace="ricxapp",phase="Failed"}==1)/g' /home/thc1006/dev/oran-ric-platform/dashboard/oran-ric-dashboard-v2.json

echo "Dashboard queries fixed"
