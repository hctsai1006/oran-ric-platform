# E2-Simulator UAV Integration - Deployment Verification Checklist

## Pre-Deployment Verification

### Code Quality Checks
- [x] All Python files pass syntax validation (`python3 -m py_compile`)
- [x] No import errors
- [x] All dependencies listed in requirements.txt
- [x] Dockerfile syntax is valid
- [x] Kubernetes manifests are valid YAML

### File Verification
```bash
# Verify E2-simulator modifications
ls -l /home/thc1006/dev/oran-ric-platform/simulator/e2-simulator/src/e2_simulator.py
ls -l /home/thc1006/dev/oran-ric-platform/simulator/e2-simulator/requirements.txt
ls -l /home/thc1006/dev/oran-ric-platform/simulator/e2-simulator/deploy/deployment.yaml

# Verify ns-O-RAN bridge files
ls -l /home/thc1006/dev/oran-ric-platform/simulator/ns-oran-bridge/src/ns_oran_bridge.py
ls -l /home/thc1006/dev/oran-ric-platform/simulator/ns-oran-bridge/Dockerfile
ls -l /home/thc1006/dev/oran-ric-platform/simulator/ns-oran-bridge/deploy/deployment.yaml

# Verify test files
ls -l /home/thc1006/dev/oran-ric-platform/simulator/e2-simulator/test_uav_integration.py
ls -l /home/thc1006/dev/oran-ric-platform/simulator/ns-oran-bridge/test_bridge.py
```

## Build Verification

### Build E2-Simulator Docker Image
```bash
cd /home/thc1006/dev/oran-ric-platform/simulator/e2-simulator
docker build -t localhost:5000/e2-simulator:uav-enabled .

# Verify image
docker images | grep e2-simulator
docker inspect localhost:5000/e2-simulator:uav-enabled
```

Expected output:
- Image built successfully
- Size should be ~500-600MB (Python 3.11 slim base)
- Entry point: `python -u e2_simulator.py`

### Build ns-O-RAN Bridge Docker Image
```bash
cd /home/thc1006/dev/oran-ric-platform/simulator/ns-oran-bridge
docker build -t localhost:5000/ns-oran-bridge:1.0.0 .

# Verify image
docker images | grep ns-oran-bridge
```

Expected output:
- Image built successfully
- Size should be ~500-600MB

### Push Images (if using registry)
```bash
docker push localhost:5000/e2-simulator:uav-enabled
docker push localhost:5000/ns-oran-bridge:1.0.0

# Verify images are in registry
curl http://localhost:5000/v2/_catalog
```

## Local Testing (Before Kubernetes)

### Test 1: E2-Simulator Standalone
```bash
cd /home/thc1006/dev/oran-ric-platform/simulator/e2-simulator

# Run in background
python3 src/e2_simulator.py &
SIM_PID=$!
sleep 3

# Test health endpoint
curl http://localhost:8080/health
# Expected: {"status": "healthy", "uav_enabled": true, ...}

# Test metrics endpoint
curl http://localhost:8080/metrics
# Expected: {"uav_positions": {...}, "uav_velocities": {...}, ...}

# Cleanup
kill $SIM_PID
```

### Test 2: ns-O-RAN Bridge Standalone
```bash
cd /home/thc1006/dev/oran-ric-platform/simulator/e2-simulator
python3 src/e2_simulator.py &
SIM_PID=$!
sleep 3

cd /home/thc1006/dev/oran-ric-platform/simulator/ns-oran-bridge
python3 src/ns_oran_bridge.py --e2-host localhost --e2-port 8080 &
BRIDGE_PID=$!
sleep 3

# Test bridge health
curl http://localhost:5000/health
# Expected: {"status": "healthy", "e2_simulator_connected": true}

# Test bridge stats
curl http://localhost:5000/stats
# Expected: {"events_received": 0, "events_processed": 0, ...}

# Cleanup
kill $BRIDGE_PID $SIM_PID
```

### Test 3: UAV Integration Test Suite
```bash
cd /home/thc1006/dev/oran-ric-platform/simulator/e2-simulator

# Start E2-simulator
python3 src/e2_simulator.py &
SIM_PID=$!
sleep 3

# Run tests
python3 test_uav_integration.py --url http://localhost:8080
# Expected: All 6 tests pass

# Cleanup
kill $SIM_PID
```

### Test 4: Bridge Integration Test Suite
```bash
cd /home/thc1006/dev/oran-ric-platform/simulator/e2-simulator
python3 src/e2_simulator.py &
SIM_PID=$!
sleep 3

cd /home/thc1006/dev/oran-ric-platform/simulator/ns-oran-bridge
python3 src/ns_oran_bridge.py --e2-host localhost --e2-port 8080 &
BRIDGE_PID=$!
sleep 3

# Run tests
python3 test_bridge.py --url http://localhost:5000
# Expected: All 6 tests pass

# Cleanup
kill $BRIDGE_PID $SIM_PID
```

## Kubernetes Deployment Verification

### Prerequisites Check
```bash
# Verify kubectl is configured
kubectl cluster-info

# Verify namespace exists or create it
kubectl get namespace ricxapp || kubectl create namespace ricxapp

# Verify registry access (if using private registry)
kubectl -n ricxapp get secret regcred 2>/dev/null || echo "No registry secret (using localhost:5000)"
```

### Deploy Using Script
```bash
cd /home/thc1006/dev/oran-ric-platform/simulator
chmod +x deploy-uav-integration.sh
./deploy-uav-integration.sh
```

### Manual Deployment
```bash
# Deploy E2-Simulator
kubectl apply -f /home/thc1006/dev/oran-ric-platform/simulator/e2-simulator/deploy/deployment.yaml

# Deploy ns-O-RAN Bridge
kubectl apply -f /home/thc1006/dev/oran-ric-platform/simulator/ns-oran-bridge/deploy/deployment.yaml

# Wait for deployments to be ready
kubectl -n ricxapp wait --for=condition=available --timeout=120s deployment/e2-simulator
kubectl -n ricxapp wait --for=condition=available --timeout=120s deployment/ns-oran-bridge
```

## Post-Deployment Verification

### Check Pod Status
```bash
# View pods
kubectl -n ricxapp get pods

# Expected output:
# NAME                             READY   STATUS    RESTARTS
# e2-simulator-xxxxxxxxxx-xxxxx    1/1     Running   0
# ns-oran-bridge-xxxxxxxxxx-xxxxx  1/1     Running   0

# Check pod details
kubectl -n ricxapp describe pod -l app=e2-simulator
kubectl -n ricxapp describe pod -l app=ns-oran-bridge
```

### Check Service Status
```bash
# View services
kubectl -n ricxapp get svc

# Expected output shows:
# e2-simulator   ClusterIP   10.x.x.x   8080/TCP
# ns-oran-bridge ClusterIP  10.x.x.x   5000/TCP

# Test service discovery (from within cluster)
kubectl -n ricxapp run -it --rm debug --image=busybox --restart=Never -- \
  wget -qO- http://e2-simulator:8080/health
```

### View Logs
```bash
# E2-Simulator logs
kubectl -n ricxapp logs -f deployment/e2-simulator
# Expected: Startup messages, "HTTP API server started on 0.0.0.0:8080"

# ns-O-RAN Bridge logs
kubectl -n ricxapp logs -f deployment/ns-oran-bridge
# Expected: Startup messages, "E2-Simulator: http://e2-simulator.ricxapp.svc.cluster.local:8080"
```

### Test Endpoints via Port Forward

#### E2-Simulator Endpoints
```bash
# Port forward
kubectl -n ricxapp port-forward svc/e2-simulator 8080:8080 &
PF_PID=$!
sleep 2

# Test health
curl http://localhost:8080/health
# Expected: 200 OK with healthy status

# Test metrics
curl http://localhost:8080/metrics
# Expected: 200 OK with UAV positions and velocities

# Test config API
curl -X PUT http://localhost:8080/config/uav \
  -H "Content-Type: application/json" \
  -d '{"uav_id": "test_uav", "position": {"x": 100, "y": 200, "z": 150}}'
# Expected: 200 OK with configured status

# Test control API
curl -X POST http://localhost:8080/ns-oran/control \
  -H "Content-Type: application/json" \
  -d '{"command_type": "config", "interval": 3}'
# Expected: 200 OK with configured status

# Cleanup
kill $PF_PID
```

#### ns-O-RAN Bridge Endpoints
```bash
# Port forward
kubectl -n ricxapp port-forward svc/ns-oran-bridge 5000:5000 &
PF_PID=$!
sleep 2

# Test health
curl http://localhost:5000/health
# Expected: 200 OK with bridge healthy and e2_simulator_connected

# Test stats
curl http://localhost:5000/stats
# Expected: 200 OK with event statistics

# Test event handling
curl -X POST http://localhost:5000/ns-oran/event \
  -H "Content-Type: application/json" \
  -d '{"event_type": "uav_position_update", "uav_id": "uav_001", "position": {"x": 300, "y": 400, "z": 250}}'
# Expected: 200 OK with processed status

# Cleanup
kill $PF_PID
```

### Test Backward Compatibility with kpimon

```bash
# Check if kpimon is running
kubectl -n ricxapp get deployment kpimon

# If kpimon is running, check it's receiving indications
kubectl -n ricxapp logs -f deployment/kpimon | grep -i "indication\|kpi\|received"

# If kpimon is not running, the E2-simulator should continue
# sending indications (visible in logs):
kubectl -n ricxapp logs deployment/e2-simulator | grep "Generated KPI"
```

## Validation Test Suite

### Run Full Validation
```bash
# Port forward both services
kubectl -n ricxapp port-forward svc/e2-simulator 8080:8080 &
E2_PF=$!
kubectl -n ricxapp port-forward svc/ns-oran-bridge 5000:5000 &
BRIDGE_PF=$!
sleep 2

cd /home/thc1006/dev/oran-ric-platform/simulator

# Run E2-simulator tests
echo "=== Testing E2-Simulator ==="
python3 e2-simulator/test_uav_integration.py --url http://localhost:8080

# Run bridge tests
echo "=== Testing ns-O-RAN Bridge ==="
python3 ns-oran-bridge/test_bridge.py --url http://localhost:5000

# Cleanup
kill $E2_PF $BRIDGE_PF
```

## Integration Validation Scenarios

### Scenario 1: UAV Position Update Flow
```bash
# 1. Port forward both services
# 2. Send position update to bridge
curl -X POST http://localhost:5000/ns-oran/event \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "uav_position_update",
    "uav_id": "uav_001",
    "position": {"x": 300, "y": 400, "z": 250},
    "velocity": {"vx": 3, "vy": 4, "vz": 1}
  }'

# 3. Verify in E2-simulator metrics
curl http://localhost:8080/metrics | jq '.uav_positions.uav_001'
# Expected: {"x": 300, "y": 400, "z": 250}

# 4. Check bridge processed the event
curl http://localhost:5000/stats | jq '.events_processed'
# Expected: 1 (or higher if other tests ran)
```

### Scenario 2: Configuration Update
```bash
# 1. Send config update to bridge
curl -X POST http://localhost:5000/ns-oran/event \
  -H "Content-Type: application/json" \
  -d '{"event_type": "network_config", "indication_interval": 3}'

# 2. Verify config was updated
curl http://localhost:8080/metrics | jq '.config.interval'
# Expected: 3

# 3. Verify bridge stats
curl http://localhost:5000/stats | jq '.events_processed'
# Expected: increased by 1
```

### Scenario 3: Data Flow Completeness
```bash
# 1. Check E2-simulator is generating indications
kubectl -n ricxapp logs deployment/e2-simulator --tail=50 | grep "uav_id"
# Expected: Lines showing UAV IDs in indications

# 2. Check if kpimon received indications (if running)
kubectl -n ricxapp logs deployment/kpimon --tail=50 | grep "indication"
# Expected: Lines showing received indications

# 3. Verify metrics endpoint includes all fields
curl http://localhost:8080/metrics | jq '.config.uavs'
# Expected: Array with UAV IDs
```

## Performance Validation

### Resource Usage Monitoring
```bash
# Check pod resource usage
kubectl -n ricxapp top pods

# Expected:
# NAME                    CPU(m)   MEMORY(Mi)
# e2-simulator-...        50-100   100-150
# ns-oran-bridge-...      30-50    60-100

# Check detailed metrics
kubectl -n ricxapp describe pod -l app=e2-simulator | grep -A 5 "Limits\|Requests"
```

### Stress Test
```bash
# Send multiple rapid updates to bridge
for i in {1..100}; do
  curl -X POST http://localhost:5000/ns-oran/event \
    -H "Content-Type: application/json" \
    -d "{\"event_type\": \"uav_position_update\", \"uav_id\": \"uav_001\", \"position\": {\"x\": $((i*10)), \"y\": 400, \"z\": 250}}" &
done
wait

# Check stats
curl http://localhost:5000/stats | jq '.events_processed'
# Expected: ~100 events processed without errors
```

## Troubleshooting

### Pod Fails to Start
```bash
# Check events
kubectl -n ricxapp describe deployment e2-simulator
kubectl -n ricxapp describe deployment ns-oran-bridge

# Check logs for errors
kubectl -n ricxapp logs deployment/e2-simulator
kubectl -n ricxapp logs deployment/ns-oran-bridge

# Common issues:
# - Image not found: Verify docker push was successful
# - Port conflict: Check if port 8080/5000 already in use
# - Memory/CPU: Increase limits in deployment.yaml
```

### Slow Response Times
```bash
# Check CPU/memory usage
kubectl -n ricxapp top pods

# Check network latency between services
kubectl -n ricxapp exec -it deployment/ns-oran-bridge -- \
  curl -w "@/dev/stdin" -o /dev/null -s http://e2-simulator:8080/health
# Expected: response time < 100ms

# Check event queue
curl http://localhost:5000/stats | jq '.events_received, .events_processed'
# If received >> processed, bridge may be overloaded
```

### Connection Failures
```bash
# Test DNS resolution
kubectl -n ricxapp exec -it deployment/ns-oran-bridge -- \
  nslookup e2-simulator

# Test direct connection to service
kubectl -n ricxapp exec -it deployment/ns-oran-bridge -- \
  curl -v http://e2-simulator:8080/health

# Check network policies
kubectl -n ricxapp get networkpolicies
```

## Sign-Off Checklist

- [ ] All Python files pass syntax validation
- [ ] Docker images build successfully
- [ ] Docker images push to registry successfully
- [ ] Kubernetes manifests are valid YAML
- [ ] Pods deploy successfully
- [ ] Services are created correctly
- [ ] Health checks pass (liveness and readiness)
- [ ] E2-simulator HTTP endpoints respond correctly
- [ ] ns-O-RAN bridge HTTP endpoints respond correctly
- [ ] Bridge can connect to E2-simulator
- [ ] Test suites pass (all 12+ tests)
- [ ] Backward compatibility verified with kpimon
- [ ] Integration scenarios work end-to-end
- [ ] Performance is acceptable (CPU/memory usage normal)
- [ ] Logs are clear and informative
- [ ] Documentation is complete and accurate

## Additional Notes

- Monitor logs continuously during initial testing
- Keep previous version available for rollback
- Plan for UAV data volume when scaling
- Test with your specific ns-O-RAN configuration
- Document any environmental modifications needed

---

**Deployment Date**: _______________
**Verified By**: _______________
**Comments**:
