# Beam KPI Query API - Quick Start Guide

**5-Minute Getting Started**

---

## What is This?

An interactive REST API to query beam-specific KPI measurements (RSRP, RSRQ, SINR, Throughput) from your O-RAN RIC platform.

**Before:** E2 Simulator pushes all data to xApps (can't choose what you get)
**Now:** Query specific beam data when you need it (pull-on-demand)

---

## Quick Deploy (3 Steps)

### Step 1: Deploy KPIMON with Beam API
```bash
cd /home/mbwcl711_3060/thc1006/tmep/oran-ric-platform
./scripts/deploy-xapp.sh kpimon
```

### Step 2: Expose API Externally
```bash
kubectl apply -f xapps/kpimon-go-xapp/deploy/beam-api-service.yaml
```

### Step 3: Verify It Works
```bash
curl http://localhost:30081/health/alive
```

Expected: `{"status":"alive"}`

---

## Try It Now (Sample Queries)

### Query Beam 1 Current KPIs
```bash
curl "http://localhost:30081/api/beam/1/kpi?kpi_type=all" | jq
```

### Get Signal Quality Only (RSRP, RSRQ, SINR)
```bash
curl "http://localhost:30081/api/beam/1/kpi?kpi_type=rsrp,rsrq,sinr" | jq
```

### List All Active Beams
```bash
curl "http://localhost:30081/api/beam/list" | jq
```

### Find Beams with Good Signal (RSRP > -95 dBm)
```bash
curl "http://localhost:30081/api/beam/list?min_rsrp=-95" | jq
```

---

## Example Response

```json
{
  "status": "success",
  "beam_id": 1,
  "timestamp": "2025-11-19T08:15:30.123Z",
  "data": {
    "signal_quality": {
      "rsrp": {
        "value": -95.5,
        "unit": "dBm",
        "quality": "good"
      },
      "rsrq": {
        "value": -10.2,
        "unit": "dB",
        "quality": "good"
      },
      "sinr": {
        "value": 18.5,
        "unit": "dB",
        "quality": "excellent"
      }
    },
    "throughput": {
      "downlink": {"value": 85.3, "unit": "Mbps"},
      "uplink": {"value": 42.7, "unit": "Mbps"}
    }
  },
  "count": 5,
  "source": "redis"
}
```

---

## API Endpoints

| Endpoint | Description | Example |
|----------|-------------|---------|
| `GET /api/beam/{id}/kpi` | Query beam KPIs | `/api/beam/1/kpi?kpi_type=all` |
| `GET /api/beam/{id}/kpi/timeseries` | Get time-series data | `/api/beam/1/kpi/timeseries?kpi_type=rsrp` |
| `GET /api/beam/list` | List all beams | `/api/beam/list?min_rsrp=-95` |

---

## Query Parameters

### For `/api/beam/{id}/kpi`

| Parameter | Options | Default | Description |
|-----------|---------|---------|-------------|
| `kpi_type` | `rsrp`, `rsrq`, `sinr`, `throughput_dl`, `throughput_ul`, `all` | `all` | Which KPIs to return |
| `time_range` | `current`, `last_5m`, `last_15m`, `last_1h`, `last_24h` | `current` | Time window |
| `aggregation` | `raw`, `mean`, `min`, `max` | `raw` | How to aggregate |
| `cell_id` | e.g., `cell_001` | - | Filter by cell |
| `ue_id` | e.g., `ue_005` | - | Filter by UE |

---

## Run Tests

```bash
# Automated test suite
python3 tests/beam-query-api-test.py

# Interactive demo
python3 tests/beam-query-api-test.py --interactive
```

---

## Integration Examples

### Python
```python
import requests

response = requests.get(
    "http://localhost:30081/api/beam/1/kpi",
    params={"kpi_type": "all"}
)
data = response.json()
rsrp = data['data']['signal_quality']['rsrp']['value']
print(f"Beam 1 RSRP: {rsrp} dBm")
```

### JavaScript
```javascript
fetch('http://localhost:30081/api/beam/1/kpi?kpi_type=all')
  .then(r => r.json())
  .then(data => {
    console.log(`RSRP: ${data.data.signal_quality.rsrp.value} dBm`);
  });
```

### Bash Script
```bash
#!/bin/bash
RSRP=$(curl -s "http://localhost:30081/api/beam/1/kpi?kpi_type=rsrp" | \
       jq -r '.data.signal_quality.rsrp.value')
echo "Beam 1 RSRP: $RSRP dBm"
```

---

## Quality Indicators

The API automatically assesses signal quality:

### RSRP Thresholds
- **Excellent**: ≥ -85 dBm
- **Good**: -85 to -95 dBm
- **Fair**: -95 to -105 dBm
- **Poor**: < -105 dBm

### RSRQ Thresholds
- **Excellent**: ≥ -8 dB
- **Good**: -8 to -10 dB
- **Fair**: -10 to -13 dB
- **Poor**: < -13 dB

### SINR Thresholds
- **Excellent**: ≥ 20 dB
- **Good**: 13 to 20 dB
- **Fair**: 8 to 13 dB
- **Poor**: < 8 dB

---

## Common Use Cases

### 1. Real-Time Monitoring Dashboard
```bash
# Poll every 5 seconds
while true; do
  curl -s "http://localhost:30081/api/beam/1/kpi?kpi_type=rsrp,rsrq,sinr" | \
    jq '.data.signal_quality'
  sleep 5
done
```

### 2. Find Best Beam for UE
```bash
# Compare all beams, find best RSRP
curl -s "http://localhost:30081/api/beam/list" | \
  jq '.beams | sort_by(.summary.rsrp_avg) | reverse | .[0]'
```

### 3. Historical Trend Analysis
```bash
# Get 1 hour of RSRP data, averaged every 30s
curl "http://localhost:30081/api/beam/1/kpi/timeseries?kpi_type=rsrp&interval=30s" | \
  jq '.datapoints'
```

### 4. Beam Health Check
```bash
# List only beams with good signal
curl "http://localhost:30081/api/beam/list?min_rsrp=-95" | \
  jq '.beams[] | {beam_id, rsrp: .summary.rsrp_avg}'
```

---

## Troubleshooting

### Problem: API returns 404 "No data found"

**Fix:**
```bash
# Check E2 Simulator is running
kubectl get pods -n ricplt -l app=e2-simulator

# Check it's generating beam data
kubectl logs -n ricplt -l app=e2-simulator --tail=50 | grep "Beam"
```

### Problem: Connection refused

**Fix:**
```bash
# Verify service is running
kubectl get svc -n ricxapp kpimon-beam-api-nodeport

# Check KPIMON pod status
kubectl get pods -n ricxapp -l app=kpimon
```

### Problem: Stale data (old timestamp)

**Fix:**
```bash
# Restart E2 Simulator
kubectl rollout restart deployment/e2-simulator -n ricplt
```

---

## Access Methods

### Internal (from within Kubernetes)
```bash
http://kpimon.ricxapp.svc.cluster.local:8081/api
```

### External (NodePort)
```bash
http://<your-node-ip>:30081/api
# Or from localhost:
http://localhost:30081/api
```

---

## More Examples

### Run all example queries
```bash
bash docs/beam-api-examples.sh
```

### Interactive demo mode
```bash
python3 tests/beam-query-api-test.py --interactive
```

---

## Full Documentation

- **User Guide:** `docs/BEAM_KPI_QUERY_API.md`
- **Implementation Report:** `BEAM_QUERY_API_IMPLEMENTATION_REPORT.md`
- **OpenAPI Spec:** `xapps/kpimon-go-xapp/api/beam-kpi-api.yaml`
- **Test Suite:** `tests/beam-query-api-test.py`

---

## Support

**Check logs:**
```bash
kubectl logs -n ricxapp -l app=kpimon --tail=100
```

**Run tests:**
```bash
python3 tests/beam-query-api-test.py
```

**View Swagger UI:**
Upload `xapps/kpimon-go-xapp/api/beam-kpi-api.yaml` to https://editor.swagger.io

---

## What's Included

✅ REST API with 3 main endpoints
✅ Real-time data from Redis (300s cache)
✅ Historical data from InfluxDB (optional)
✅ Automatic quality assessment
✅ Comprehensive test suite
✅ Full OpenAPI specification
✅ Integration examples (Python, JavaScript, Bash)

---

**Ready to use!** Start with the example queries above.
