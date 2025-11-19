#!/bin/bash
# Quick Platform Health Check
# Updated: 2025-11-19 - Fixed label selectors and added comprehensive checks

echo "=========================================="
echo "O-RAN RIC Platform Quick Health Check"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ricplt namespace
echo "📊 RIC Platform (ricplt) Namespace:"
RICPLT_TOTAL=$(kubectl get pods -n ricplt --no-headers 2>/dev/null | wc -l)
RICPLT_RUNNING=$(kubectl get pods -n ricplt --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l)
echo "   Total Pods: $RICPLT_TOTAL"
echo "   Running: $RICPLT_RUNNING"
if [ "$RICPLT_RUNNING" -eq "$RICPLT_TOTAL" ]; then
    echo -e "   Status: ${GREEN}✅ ALL RUNNING${NC}"
else
    echo -e "   Status: ${YELLOW}⚠️  Some pods not running${NC}"
    kubectl get pods -n ricplt | grep -v Running | tail -n +2
fi
echo ""

# ricxapp namespace
echo "🚀 xApps (ricxapp) Namespace:"
RICXAPP_TOTAL=$(kubectl get pods -n ricxapp --no-headers 2>/dev/null | wc -l)
RICXAPP_RUNNING=$(kubectl get pods -n ricxapp --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l)
echo "   Total Pods: $RICXAPP_TOTAL"
echo "   Running: $RICXAPP_RUNNING"
if [ "$RICXAPP_RUNNING" -eq "$RICXAPP_TOTAL" ]; then
    echo -e "   Status: ${GREEN}✅ ALL RUNNING${NC}"
else
    echo -e "   Status: ${YELLOW}⚠️  Some pods not running${NC}"
    kubectl get pods -n ricxapp | grep -v Running | tail -n +2
fi
echo ""

# Services
echo "🌐 Services:"
RICPLT_SVC=$(kubectl get svc -n ricplt --no-headers 2>/dev/null | wc -l)
RICXAPP_SVC=$(kubectl get svc -n ricxapp --no-headers 2>/dev/null | wc -l)
echo "   ricplt services: $RICPLT_SVC"
echo "   ricxapp services: $RICXAPP_SVC"
echo ""

# Key components status - using correct label selectors
echo "🔧 Key Platform Components:"

# Platform components with correct labels
declare -A platform_components=(
    ["e2term-alpha"]="app=ricplt-e2term-alpha"
    ["e2mgr"]="app=ricplt-e2mgr"
    ["submgr"]="app=ricplt-submgr"
    ["rtmgr"]="app=ricplt-rtmgr"
    ["appmgr"]="app=ricplt-appmgr"
    ["a1mediator"]="app=ricplt-a1mediator"
    ["rsm"]="app=ricplt-rsm"
    ["dbaas"]="app=ricplt-dbaas"
    ["redis-cluster"]="app.kubernetes.io/name=redis-cluster"
)

for comp in "${!platform_components[@]}"; do
    label="${platform_components[$comp]}"
    status=$(kubectl get pods -n ricplt -l "$label" -o jsonpath='{.items[0].status.phase}' 2>/dev/null)
    if [ "$status" == "Running" ]; then
        echo -e "   ${GREEN}✅${NC} $comp"
    elif [ -z "$status" ]; then
        echo -e "   ${RED}❌${NC} $comp - Not found"
    else
        echo -e "   ${YELLOW}⚠️${NC}  $comp - $status"
    fi
done

echo ""
echo "🎯 Deployed xApps:"

# xApps with correct labels
declare -A xapps=(
    ["kpimon"]="app=kpimon"
    ["traffic-steering"]="app=traffic-steering"
    ["ran-control"]="app=ran-control"
    ["qoe-predictor"]="app=qoe-predictor"
    ["federated-learning"]="app=federated-learning"
    ["federated-learning-gpu"]="version=v1.0.0-gpu"
    ["hw-go"]="app=hw-go"
    ["e2-simulator"]="app=e2-simulator"
)

for xapp in "${!xapps[@]}"; do
    label="${xapps[$xapp]}"
    status=$(kubectl get pods -n ricxapp -l "$label" -o jsonpath='{.items[0].status.phase}' 2>/dev/null)
    if [ "$status" == "Running" ]; then
        echo -e "   ${GREEN}✅${NC} $xapp"
    elif [ -z "$status" ]; then
        echo -e "   ${YELLOW}⚠️${NC}  $xapp - Not deployed"
    else
        echo -e "   ${YELLOW}⚠️${NC}  $xapp - $status"
    fi
done

echo ""
echo "🔌 E2E Data Flow Check:"

# Check if E2 Simulator is sending data
E2SIM_POD=$(kubectl get pods -n ricxapp -l app=e2-simulator -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ ! -z "$E2SIM_POD" ]; then
    RECENT_ITERATIONS=$(kubectl logs -n ricxapp "$E2SIM_POD" --tail=10 2>/dev/null | grep -c "Simulation Iteration" || echo "0")
    if [ "$RECENT_ITERATIONS" -gt 0 ]; then
        echo -e "   ${GREEN}✅${NC} E2 Simulator generating data"
    else
        echo -e "   ${YELLOW}⚠️${NC}  E2 Simulator may not be generating data"
    fi
fi

# Check if KPIMON is receiving indications
KPIMON_POD=$(kubectl get pods -n ricxapp -l app=kpimon -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ ! -z "$KPIMON_POD" ]; then
    RECENT_INDICATIONS=$(kubectl logs -n ricxapp "$KPIMON_POD" --tail=20 2>/dev/null | grep -c "POST /e2/indication" || echo "0")
    if [ "$RECENT_INDICATIONS" -gt 0 ]; then
        echo -e "   ${GREEN}✅${NC} KPIMON receiving E2 indications"
    else
        echo -e "   ${YELLOW}⚠️${NC}  KPIMON not receiving E2 indications"
    fi
fi

# Check if Traffic Steering is processing data
TS_POD=$(kubectl get pods -n ricxapp -l app=traffic-steering -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ ! -z "$TS_POD" ]; then
    TS_ACTIVE=$(kubectl logs -n ricxapp "$TS_POD" --tail=20 2>/dev/null | grep -c "Active UEs" || echo "0")
    if [ "$TS_ACTIVE" -gt 0 ]; then
        echo -e "   ${GREEN}✅${NC} Traffic Steering processing UE data"
    else
        echo -e "   ${YELLOW}⚠️${NC}  Traffic Steering may not be processing data"
    fi
fi

echo ""
echo "=========================================="
echo "Health check complete"
echo "=========================================="
