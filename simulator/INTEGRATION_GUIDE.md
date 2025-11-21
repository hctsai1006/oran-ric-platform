# E2-Simulator UAV Integration Guide

This guide explains the UAV integration enhancements to the E2-simulator and ns-O-RAN bridge functionality.

## Overview

The enhanced E2-simulator now supports:
- UAV-specific metrics (position, velocity, signal strength, altitude)
- HTTP API for configuration and control
- Integration with ns-O-RAN systems via the ns-O-RAN bridge
- Full backward compatibility with existing kpimon integration

## Architecture

```
ns-O-RAN System
      |
      | (events)
      v
ns-O-RAN Bridge (port 5000)
      |
      | (HTTP API calls)
      v
E2-Simulator (port 8080)
      |
      +-> kpimon (RMR/HTTP)
      +-> traffic-steering
      +-> qoe-predictor
      +-> ran-control
```

## E2-Simulator Enhancements

### New Configuration Options

```python
'uav_enabled': True,           # Enable/disable UAV features
'uavs': ['uav_001', 'uav_002', 'uav_003'],  # List of simulated UAVs
'max_uav_altitude': 500.0      # Maximum altitude in meters
```

### UAV Data in Indications

Each KPI indication now includes optional UAV data:

```json
{
  "timestamp": "2025-11-21T10:00:00",
  "cell_id": "cell_001",
  "ue_id": "ue_001",
  "beam_id": 0,
  "measurements": [...],
  "uav_id": "uav_001",
  "uav_position": {"x": 100.5, "y": 200.3, "z": 150.0},
  "uav_velocity": {"vx": 5.0, "vy": 2.0, "vz": 0.0},
  "uav_signal_strength": -75.0,
  "uav_altitude_m": 150.0
}
```

### New HTTP Endpoints

#### 1. Health Check
```
GET /health
Response: 200 OK
{
  "status": "healthy",
  "running": true,
  "uav_enabled": true,
  "timestamp": "2025-11-21T10:00:00"
}
```

#### 2. Get Metrics
```
GET /metrics
Response: 200 OK
{
  "uav_positions": {...},
  "uav_velocities": {...},
  "config": {...}
}
```

#### 3. UAV Configuration
```
PUT /config/uav
Request:
{
  "uav_id": "uav_004",
  "position": {"x": 100, "y": 200, "z": 150},
  "velocity": {"vx": 5, "vy": 2, "vz": 0}
}
Response: 200 OK
{
  "status": "configured",
  "uav_id": "uav_004"
}
```

#### 4. ns-O-RAN Control
```
POST /ns-oran/control
Request (UAV Update):
{
  "command_type": "uav_update",
  "uav_id": "uav_001",
  "position": {...},
  "velocity": {...}
}

Request (Configuration):
{
  "command_type": "config",
  "interval": 5,
  "uav_enabled": true
}
Response: 200 OK
{
  "status": "updated|configured"
}
```

#### 5. Indication Endpoint (Backward Compatible)
```
POST /e2/indication
Request:
{
  "timestamp": "...",
  "cell_id": "...",
  "ue_id": "...",
  "measurements": [...]
}
Response: 200 OK
```

## ns-O-RAN Bridge

The bridge acts as an adapter between ns-O-RAN systems and E2-simulator.

### New HTTP Endpoints

#### 1. Health Check
```
GET /health
Checks connection to E2-simulator
```

#### 2. Statistics
```
GET /stats
Returns event processing statistics
```

#### 3. ns-O-RAN Events
```
POST /ns-oran/event
Accepts events from ns-O-RAN systems
```

#### 4. Direct Simulator Commands
```
POST /simulator/command
Send commands directly to E2-simulator
```

### Supported Event Types

#### 1. UAV Position Update
```json
{
  "event_type": "uav_position_update",
  "uav_id": "uav_001",
  "position": {"x": 100.0, "y": 200.0, "z": 150.0},
  "velocity": {"vx": 5.0, "vy": 2.0, "vz": 0.0}
}
```

#### 2. UAV Mission
```json
{
  "event_type": "uav_mission",
  "uav_id": "uav_001",
  "mission_type": "coverage",
  "target_area": {
    "x_min": 0.0,
    "x_max": 500.0,
    "y_min": 0.0,
    "y_max": 500.0,
    "altitude": 200.0
  }
}
```

#### 3. Network Configuration
```json
{
  "event_type": "network_config",
  "indication_interval": 5,
  "uav_enabled": true
}
```

## Deployment

### Build Docker Images

#### E2-Simulator (UAV-enabled)
```bash
cd /home/thc1006/dev/oran-ric-platform/simulator/e2-simulator
docker build -t localhost:5000/e2-simulator:uav-enabled .
docker push localhost:5000/e2-simulator:uav-enabled
```

#### ns-O-RAN Bridge
```bash
cd /home/thc1006/dev/oran-ric-platform/simulator/ns-oran-bridge
docker build -t localhost:5000/ns-oran-bridge:1.0.0 .
docker push localhost:5000/ns-oran-bridge:1.0.0
```

### Deploy to Kubernetes

#### 1. Update E2-Simulator
```bash
kubectl apply -f /home/thc1006/dev/oran-ric-platform/simulator/e2-simulator/deploy/deployment.yaml
```

#### 2. Deploy ns-O-RAN Bridge
```bash
kubectl apply -f /home/thc1006/dev/oran-ric-platform/simulator/ns-oran-bridge/deploy/deployment.yaml
```

### Verify Deployment

```bash
# Check E2-simulator
kubectl -n ricxapp logs -f deployment/e2-simulator

# Check ns-O-RAN bridge
kubectl -n ricxapp logs -f deployment/ns-oran-bridge

# Port forward for testing
kubectl -n ricxapp port-forward svc/e2-simulator 8080:8080 &
kubectl -n ricxapp port-forward svc/ns-oran-bridge 5000:5000 &
```

## Testing

### Test E2-Simulator UAV Features
```bash
cd /home/thc1006/dev/oran-ric-platform/simulator/e2-simulator
python test_uav_integration.py --url http://localhost:8080
```

### Test ns-O-RAN Bridge
```bash
cd /home/thc1006/dev/oran-ric-platform/simulator/ns-oran-bridge
python test_bridge.py --url http://localhost:5000
```

## Example Integration Workflows

### Workflow 1: Update UAV Position from ns-O-RAN

```bash
# Send position update from ns-O-RAN
curl -X POST http://localhost:5000/ns-oran/event \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "uav_position_update",
    "uav_id": "uav_001",
    "position": {"x": 250, "y": 300, "z": 200},
    "velocity": {"vx": 3, "vy": 4, "vz": 0}
  }'

# Bridge translates to E2-simulator control command
# E2-simulator updates UAV state
# Next KPI indication includes new position
```

### Workflow 2: Configure UAV Mission

```bash
# Send mission from ns-O-RAN
curl -X POST http://localhost:5000/ns-oran/event \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "uav_mission",
    "uav_id": "uav_002",
    "mission_type": "surveillance",
    "target_area": {
      "x_min": 100, "x_max": 600,
      "y_min": 100, "y_max": 600,
      "altitude": 250
    }
  }'

# Bridge initializes UAV at mission center
# E2-simulator tracks UAV movements
# kpimon receives updated metrics
```

### Workflow 3: Get Current Simulator State

```bash
# Query current metrics
curl http://localhost:8080/metrics

# Get bridge statistics
curl http://localhost:5000/stats
```

## Backward Compatibility

All existing functionality is preserved:
- kpimon continues to receive indications via HTTP POST
- Traditional E2 indication format still supported
- Non-UAV fields remain unchanged
- Configuration can disable UAV features if needed

To disable UAV features:
```bash
curl -X POST http://localhost:8080/ns-oran/control \
  -H "Content-Type: application/json" \
  -d '{"command_type": "config", "uav_enabled": false}'
```

## Files Modified and Created

### Modified Files
- `/home/thc1006/dev/oran-ric-platform/simulator/e2-simulator/src/e2_simulator.py`
  - Added UAV configuration and position tracking
  - Added HTTP API endpoints using Flask
  - Updated indication generation to include UAV data

- `/home/thc1006/dev/oran-ric-platform/simulator/e2-simulator/requirements.txt`
  - Added Flask and PyYAML dependencies

- `/home/thc1006/dev/oran-ric-platform/simulator/e2-simulator/deploy/deployment.yaml`
  - Added HTTP port exposure
  - Added health checks
  - Added Service definition

### New Files
- `/home/thc1006/dev/oran-ric-platform/simulator/ns-oran-bridge/src/ns_oran_bridge.py`
  - ns-O-RAN bridge application

- `/home/thc1006/dev/oran-ric-platform/simulator/ns-oran-bridge/Dockerfile`
- `/home/thc1006/dev/oran-ric-platform/simulator/ns-oran-bridge/requirements.txt`
- `/home/thc1006/dev/oran-ric-platform/simulator/ns-oran-bridge/config.yaml`
- `/home/thc1006/dev/oran-ric-platform/simulator/ns-oran-bridge/deploy/deployment.yaml`

- `/home/thc1006/dev/oran-ric-platform/simulator/e2-simulator/test_uav_integration.py`
- `/home/thc1006/dev/oran-ric-platform/simulator/ns-oran-bridge/test_bridge.py`

## Troubleshooting

### E2-Simulator not responding
1. Check health endpoint: `curl http://localhost:8080/health`
2. Check logs: `kubectl -n ricxapp logs deployment/e2-simulator`
3. Verify port forwarding is active

### Bridge cannot connect to E2-simulator
1. Verify E2-simulator Service is running: `kubectl -n ricxapp get svc e2-simulator`
2. Check bridge logs: `kubectl -n ricxapp logs deployment/ns-oran-bridge`
3. Test direct connection to simulator from bridge pod

### kpimon not receiving indications
1. E2-simulator continues to send to kpimon on port 8081
2. Verify kpimon endpoint configuration
3. Check E2-simulator logs for connection errors
4. Verify kpimon HTTP server is listening

## Performance Considerations

- UAV position updates occur in-memory (no database overhead)
- HTTP API endpoints are non-blocking
- KPI indication generation includes UAV data only if `uav_enabled: true`
- Position boundary checking uses simple math (O(1) per update)
- Memory usage scales linearly with number of simulated UAVs

Typical resource usage:
- E2-Simulator: 100-200MB memory, 100-200m CPU
- ns-O-RAN Bridge: 50-100MB memory, 50-100m CPU

## Further Enhancement Ideas

1. Persistent UAV state using Redis
2. More complex UAV movement patterns (waypoints, flight plans)
3. UAV-to-cell handover simulation
4. Integration with actual ns-O-RAN APIs
5. gRPC support for E2-simulator control
6. Prometheus metrics export
