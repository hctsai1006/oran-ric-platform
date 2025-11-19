# Beam ID Integration Documentation

**Author:** Agent 5
**Date:** 2025-11-19
**Version:** 1.0

## Overview

This document describes the integration of Beam ID (SSB Index) support into the E2 Simulator and KPIMON xApp. The implementation enables beam-level monitoring and analysis for 5G NR beamforming operations.

## Table of Contents

1. [Background](#background)
2. [Architecture](#architecture)
3. [Data Schema](#data-schema)
4. [Implementation Details](#implementation-details)
5. [Usage Examples](#usage-examples)
6. [Backward Compatibility](#backward-compatibility)
7. [Testing](#testing)
8. [Future Enhancements](#future-enhancements)

---

## Background

### What is Beam ID (SSB Index)?

In 5G NR (New Radio), beamforming is a key technology that uses directional signal transmission to improve coverage and capacity. The SSB (Synchronization Signal Block) Index, also known as Beam ID, identifies different beamforming directions used by a cell.

- **Range:** 0-7 (for sub-6 GHz deployments)
- **Purpose:** Enable beam-level measurements and beam management
- **Key Metrics:**
  - **L1-RSRP:** Layer 1 Reference Signal Received Power (per beam)
  - **L1-SINR:** Layer 1 Signal-to-Interference-plus-Noise Ratio (per beam)

### Why Beam-Level Monitoring?

1. **Beam Management:** Track performance of individual beams for optimization
2. **UE Mobility:** Monitor beam switching as UEs move
3. **Radio Resource Management:** Balance load across beams
4. **Problem Diagnosis:** Identify beam-specific coverage or interference issues

---

## Architecture

### System Components

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  E2 Simulator   │────────>│  KPIMON xApp    │────────>│  Data Stores    │
│                 │  E2 KPM │                 │         │                 │
│ - Generates     │  v3.0   │ - Processes     │         │ - Redis         │
│   beam_id       │         │   beam_id       │         │ - InfluxDB      │
│ - L1-RSRP.beam  │         │ - Stores with   │         │ - Prometheus    │
│ - L1-SINR.beam  │         │   beam tags     │         │                 │
└─────────────────┘         └─────────────────┘         └─────────────────┘
```

### Data Flow

1. **E2 Simulator:** Generates KPI indications with beam_id and beam-specific measurements
2. **KPIMON xApp:** Receives, processes, and stores beam data
3. **Data Stores:** Store metrics tagged/indexed by beam_id for querying

---

## Data Schema

### E2SM-KPM Indication Format (Extended)

```json
{
  "timestamp": "2025-11-19T08:34:10.415742",
  "cell_id": "cell_001",
  "ue_id": "ue_001",
  "beam_id": 1,                    // NEW: SSB Index (0-7)
  "measurements": [
    // Legacy cell-level measurements (backward compatible)
    {
      "name": "DRB.PacketLossDl",
      "value": 2.5
    },
    {
      "name": "UE.RSRP",
      "value": -95.2
    },

    // NEW: Beam-specific measurements
    {
      "name": "L1-RSRP.beam",
      "value": -85.5,
      "beam_id": 1                 // Beam-specific RSRP
    },
    {
      "name": "L1-SINR.beam",
      "value": 15.3,
      "beam_id": 1                 // Beam-specific SINR
    }
  ],
  "indication_sn": 1763512450415,
  "indication_type": "report"
}
```

### Field Descriptions

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `beam_id` | integer | SSB Index (0-7) identifying the serving beam | Yes |
| `measurements[].beam_id` | integer | Beam ID for beam-specific measurements | For beam KPIs |
| `measurements[].name` | string | KPI name (e.g., "L1-RSRP.beam") | Yes |
| `measurements[].value` | float | Measurement value | Yes |

### New KPI Definitions

#### L1-RSRP.beam

- **Name:** Layer 1 Reference Signal Received Power (per beam)
- **Type:** beam_signal
- **Unit:** dBm
- **Range:** -140 to -44 dBm (typical: -100 to -70 dBm)
- **Description:** Measures the power of the reference signal from a specific beam
- **Usage:** Beam selection, handover decisions, load balancing

#### L1-SINR.beam

- **Name:** Layer 1 Signal-to-Interference-plus-Noise Ratio (per beam)
- **Type:** beam_signal
- **Unit:** dB
- **Range:** -20 to 40 dB (typical: 8 to 30 dB)
- **Description:** Measures signal quality for a specific beam
- **Usage:** MCS selection, beam ranking, interference detection

---

## Implementation Details

### E2 Simulator Changes

**File:** `/home/mbwcl711_3060/thc1006/tmep/oran-ric-platform/simulator/e2-simulator/src/e2_simulator.py`

#### 1. Configuration

```python
self.config = {
    # ... existing config ...
    'beams_per_cell': 8,  # Number of beams per cell (SSB Index: 0-7)
}

# Beam configurations per cell
self.beam_config = {
    'cell_001': list(range(8)),  # Beams 0-7
    'cell_002': list(range(8)),
    'cell_003': list(range(8))
}
```

#### 2. Beam Selection

```python
# Select a random beam for this UE (SSB Index)
beam_id = random.choice(self.beam_config[cell_id])
```

#### 3. Beam-Specific Measurements

```python
# Generate L1-RSRP for the serving beam
l1_rsrp = random.uniform(-100.0, -70.0)
beam_quality_factor = 1.0 - (beam_id * 0.05)  # Beam 0 typically best
l1_rsrp = l1_rsrp * beam_quality_factor

# Generate L1-SINR for the serving beam
l1_sinr = random.uniform(8.0, 30.0)
l1_sinr = l1_sinr * beam_quality_factor

measurements.extend([
    {
        'name': 'L1-RSRP.beam',
        'value': l1_rsrp,
        'beam_id': beam_id
    },
    {
        'name': 'L1-SINR.beam',
        'value': l1_sinr,
        'beam_id': beam_id
    }
])
```

### KPIMON xApp Changes

**File:** `/home/mbwcl711_3060/thc1006/tmep/oran-ric-platform/xapps/kpimon-go-xapp/src/kpimon.py`

#### 1. KPI Definitions

```python
self.kpi_definitions = {
    # ... existing KPIs ...
    # Beam-specific KPIs (5G NR beamforming)
    "L1-RSRP.beam": {"id": 21, "type": "beam_signal", "unit": "dBm", "beam_specific": True},
    "L1-SINR.beam": {"id": 22, "type": "beam_signal", "unit": "dB", "beam_specific": True}
}
```

#### 2. Prometheus Metrics

```python
# Updated to include beam_id label
KPI_VALUES = Gauge('kpimon_kpi_value', 'Current KPI values',
                   ['kpi_type', 'cell_id', 'beam_id'])
```

#### 3. Indication Processing

```python
def _handle_indication(self, payload):
    # Extract beam_id (with backward compatibility)
    beam_id = indication.get('beam_id', 'n/a')

    for measurement in measurements:
        measurement_beam_id = measurement.get('beam_id', beam_id)

        # Update Prometheus with beam_id label
        KPI_VALUES.labels(
            kpi_type=kpi_name,
            cell_id=cell_id,
            beam_id=str(measurement_beam_id)
        ).set(kpi_value)
```

#### 4. Redis Storage

```python
# Beam-specific KPIs use beam_id in key
if is_beam_specific:
    key = f"kpi:{cell_id}:{kpi_name}:beam_{measurement_beam_id}"
else:
    key = f"kpi:{cell_id}:{kpi_name}"

# Store beam-specific timeline
if is_beam_specific and measurement_beam_id != 'n/a':
    beam_timeline_key = f"kpi:timeline:{cell_id}:beam_{measurement_beam_id}"
    self.redis_client.zadd(beam_timeline_key, {timestamp: kpi_value})
```

#### 5. InfluxDB Storage

```python
# Tag points with beam_id for filtering
point = influxdb_client.Point("kpi_measurement") \
    .tag("cell_id", kpi['cell_id']) \
    .tag("kpi_name", kpi['kpi_name']) \
    .tag("kpi_type", kpi['kpi_type']) \
    .tag("beam_id", str(kpi.get('beam_id', 'n/a'))) \
    .field("value", float(kpi['kpi_value'])) \
    .time(kpi['timestamp'])

# Mark beam-specific measurements
if kpi.get('beam_specific', False):
    point = point.tag("beam_specific", "true")
```

#### 6. Anomaly Detection

```python
def _detect_anomalies(self, cell_id: str, measurements: List[Dict], beam_id=None):
    # Beam-specific thresholds
    thresholds = {
        # ... existing thresholds ...
        "L1-RSRP.beam": -105.0,    # Alert if beam RSRP < -105 dBm
        "L1-SINR.beam": 10.0       # Alert if beam SINR < 10 dB
    }
```

---

## Usage Examples

### Query Beam-Specific Metrics from Redis

```python
import redis

r = redis.Redis(host='redis-service.ricplt', port=6379, decode_responses=True)

# Get L1-RSRP for cell_001, beam 3
key = "kpi:cell_001:L1-RSRP.beam:beam_3"
data = r.get(key)
print(json.loads(data))

# Get beam timeline
timeline = r.zrange("kpi:timeline:cell_001:beam_3", 0, -1, withscores=True)
```

### Query Beam-Specific Metrics from InfluxDB

```flux
from(bucket: "kpimon")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "kpi_measurement")
  |> filter(fn: (r) => r["cell_id"] == "cell_001")
  |> filter(fn: (r) => r["beam_id"] == "3")
  |> filter(fn: (r) => r["kpi_name"] == "L1-RSRP.beam")
  |> yield(name: "beam_rsrp")
```

### Query Beam-Specific Metrics from Prometheus

```promql
# Get L1-RSRP for all beams in cell_001
kpimon_kpi_value{kpi_type="L1-RSRP.beam", cell_id="cell_001"}

# Get L1-RSRP for specific beam
kpimon_kpi_value{kpi_type="L1-RSRP.beam", cell_id="cell_001", beam_id="3"}

# Compare beams
sum by (beam_id) (kpimon_kpi_value{kpi_type="L1-RSRP.beam", cell_id="cell_001"})
```

### Python Code Example

```python
from e2_simulator import E2Simulator

# Initialize simulator
sim = E2Simulator()

# Generate indication with beam data
indication = sim.generate_kpi_indication()

print(f"Cell: {indication['cell_id']}")
print(f"UE: {indication['ue_id']}")
print(f"Beam ID: {indication['beam_id']}")

# Extract beam-specific measurements
for m in indication['measurements']:
    if 'beam_id' in m:
        print(f"{m['name']}: {m['value']:.2f} (beam {m['beam_id']})")
```

**Output:**
```
Cell: cell_001
UE: ue_005
Beam ID: 2
L1-RSRP.beam: -82.45 (beam 2)
L1-SINR.beam: 18.32 (beam 2)
```

---

## Backward Compatibility

### Design Principles

1. **Optional Field:** `beam_id` is optional; legacy code can ignore it
2. **Separate Measurements:** Beam-specific KPIs don't replace cell-level KPIs
3. **Graceful Degradation:** System works with or without beam data

### Compatibility Matrix

| Component | Without Beam Support | With Beam Support |
|-----------|---------------------|-------------------|
| E2 Simulator | Generates cell-level KPIs | Generates cell + beam KPIs |
| KPIMON xApp | Processes cell-level KPIs | Processes both, tags with beam_id |
| Redis | Stores cell-level data | Stores cell + beam data separately |
| InfluxDB | Tags without beam_id | Tags include beam_id |
| Prometheus | Labels without beam_id | Labels include beam_id |

### Migration Path

1. **Phase 1:** Deploy updated E2 Simulator (generates beam data)
2. **Phase 2:** Deploy updated KPIMON (processes beam data)
3. **Phase 3:** Update dashboards to visualize beam metrics
4. **Phase 4:** Implement beam-aware algorithms in xApps

---

## Testing

### Test Suite

**File:** `/home/mbwcl711_3060/thc1006/tmep/oran-ric-platform/tests/e2e/test_beam_id_support.py`

### Test Coverage

1. **Beam Data Generation**
   - Verifies beam_id field is present
   - Checks beam-specific measurements (L1-RSRP.beam, L1-SINR.beam)
   - Validates beam_id values are in valid range (0-7)

2. **Beam Data Structure**
   - Validates JSON schema
   - Checks beam_id consistency between indication and measurements
   - Verifies data types and ranges

3. **Beam Diversity**
   - Tests that multiple beams are used
   - Validates distribution across cells
   - Ensures realistic beam selection

4. **Backward Compatibility**
   - Verifies legacy KPIs still present
   - Tests that old parsers can ignore beam_id
   - Validates graceful degradation

### Running Tests

```bash
cd /home/mbwcl711_3060/thc1006/tmep/oran-ric-platform
python3 tests/e2e/test_beam_id_support.py
```

### Expected Results

```
================================================================================
TEST SUMMARY
================================================================================
✓ Beam Data Generation: PASSED
✓ Beam Data Structure: PASSED
✓ Beam Diversity: PASSED
✓ Backward Compatibility: PASSED

Total: 4/4 tests passed
================================================================================
```

---

## Future Enhancements

### Planned Features

1. **Multi-Beam Reporting**
   - Report measurements for all beams, not just serving beam
   - Enable comprehensive beam comparison

2. **Beam History Tracking**
   - Track beam changes over time for UE mobility analysis
   - Identify beam handover patterns

3. **Beam-Based Optimization**
   - Load balancing across beams
   - Beam-specific power control
   - Interference mitigation per beam

4. **Advanced Analytics**
   - Beam quality prediction
   - Optimal beam selection algorithms
   - Beam failure prediction

### API Enhancements

1. **Beam Query API**
   - REST API for beam-level queries
   - Filter by cell, beam, UE, time range
   - Aggregate statistics per beam

2. **Beam Control API**
   - Trigger beam measurements
   - Configure beam reporting parameters
   - Request beam switch

### Integration Points

1. **Traffic Steering xApp**
   - Use beam RSRP/SINR for handover decisions
   - Beam-aware load balancing

2. **QoE Predictor xApp**
   - Correlate QoE with beam quality
   - Predict QoE based on beam measurements

3. **RAN Control xApp**
   - Beam-level power control
   - Beam-specific resource allocation

---

## Appendix

### Redis Key Schema

```
# Beam-specific KPI storage
kpi:{cell_id}:{kpi_name}:beam_{beam_id}

# Beam timeline
kpi:timeline:{cell_id}:beam_{beam_id}

# Beam alarms
alarms:{cell_id}:beam_{beam_id}

# Examples
kpi:cell_001:L1-RSRP.beam:beam_3
kpi:timeline:cell_001:beam_3
alarms:cell_001:beam_2
```

### InfluxDB Tag Schema

```
Measurement: kpi_measurement

Tags:
  - cell_id: "cell_001"
  - kpi_name: "L1-RSRP.beam"
  - kpi_type: "beam_signal"
  - beam_id: "3"
  - beam_specific: "true"
  - ue_id: "ue_005"

Fields:
  - value: -82.45

Timestamp: 2025-11-19T08:34:10.415742Z
```

### Prometheus Metrics

```
# Metric name
kpimon_kpi_value

# Labels
kpi_type="L1-RSRP.beam"
cell_id="cell_001"
beam_id="3"

# Value
-82.45
```

---

## References

1. **3GPP TS 38.331** - NR RRC Protocol specification
2. **3GPP TS 38.215** - NR Physical layer measurements
3. **O-RAN.WG3.E2SM-KPM-v03.00** - E2 Service Model for KPM
4. **O-RAN.WG3.E2AP-v03.00** - E2 Application Protocol

---

## Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-19 | Agent 5 | Initial release - Beam ID integration |

---

## Support

For questions or issues related to Beam ID integration:

- **Developer:** Agent 5
- **Project:** O-RAN RIC Platform
- **Repository:** oran-ric-platform
- **Test Suite:** tests/e2e/test_beam_id_support.py
