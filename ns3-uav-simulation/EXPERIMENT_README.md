# O-RAN UAV Simulation Experiment Guide

This document provides comprehensive instructions for reproducing the UAV mobility simulation experiments with O-RAN xApp integration.

## Table of Contents

1. [Environment Requirements](#environment-requirements)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Experiment Workflow](#experiment-workflow)
5. [Individual Experiments](#individual-experiments)
6. [Expected Results](#expected-results)
7. [Troubleshooting](#troubleshooting)

---

## Environment Requirements

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16+ GB |
| Storage | 10 GB | 50+ GB |
| Network | - | Stable connection for xApp |

### Software Requirements

| Software | Version | Purpose |
|----------|---------|---------|
| Ubuntu | 20.04+ | Operating System |
| Python | 3.8+ | Simulation scripts |
| ns-3 | 3.36+ | Network simulation |
| Docker | 20.10+ | xApp deployment (optional) |
| Make | 4.0+ | Build automation |

### Python Dependencies

```
numpy>=1.21.0
scipy>=1.7.0
matplotlib>=3.5.0
requests>=2.25.0
pandas>=1.3.0  (optional)
```

---

## Installation

### Step 1: Clone the Repository

```bash
cd /home/thc1006/dev/oran-ric-platform
git clone <repository-url> ns3-uav-simulation
cd ns3-uav-simulation
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Verify Installation

```bash
make check
```

Expected output:
```
[CHECK] Verifying dependencies...
  Python: Python 3.x.x
  matplotlib: 3.x.x
  numpy: 1.x.x
  requests: 2.x.x
  CSV data: /tmp/ns3-uav-full.csv (OK or NOT FOUND)
  xApp service: http://localhost:5000 (OK or NOT AVAILABLE)
[CHECK] Dependency check completed
```

### Step 4: Set Up xApp Service (Optional)

If running xApp integration tests:

```bash
# Start the UAV Policy xApp
cd ../xapp
./start_xapp.sh
```

Verify the xApp is running:
```bash
curl http://localhost:5000/health
```

---

## Quick Start

### Run All Experiments

```bash
# Complete pipeline
make all

# Or use the shell script
./run_all_experiments.sh
```

### Run Specific Components

```bash
# Generate figures only
make figures

# Generate LaTeX tables only
make latex

# Run tests only
make test
```

---

## Experiment Workflow

### Complete Pipeline

```
                    +------------------+
                    |   ns-3 Simulation|
                    |   (LTE UAV)      |
                    +--------+---------+
                             |
                             v
                    +--------+---------+
                    |   CSV Output     |
                    |   (Radio Data)   |
                    +--------+---------+
                             |
        +--------------------+--------------------+
        |                    |                    |
        v                    v                    v
+-------+-------+   +--------+--------+   +-------+-------+
| xApp          |   | Baseline        |   | Multi-Scenario|
| Integration   |   | Comparison      |   | Analysis      |
+-------+-------+   +--------+--------+   +-------+-------+
        |                    |                    |
        +--------------------+--------------------+
                             |
                             v
                    +--------+---------+
                    |  Result JSON     |
                    |  Files           |
                    +--------+---------+
                             |
        +--------------------+--------------------+
        |                                         |
        v                                         v
+-------+-------+                        +--------+--------+
| Figure        |                        | LaTeX Table     |
| Generation    |                        | Generation      |
+---------------+                        +-----------------+
```

### Data Flow

1. **ns-3 Simulation** generates UAV mobility traces with LTE radio measurements
2. **CSV Output** contains timestamped RSRP, SINR, and cell ID data
3. **xApp Integration** sends radio data to the xApp for handover decisions
4. **Baseline Comparison** compares fixed PRB vs dynamic allocation
5. **Multi-Scenario Analysis** tests different UAV speeds and load conditions
6. **Output Generation** creates publication-ready figures and LaTeX tables

---

## Individual Experiments

### Experiment 1: ns-3 LTE Simulation

**Purpose**: Generate UAV radio measurement data

**Prerequisites**:
- ns-3 installed at `/opt/ns-oran`
- UAV LTE simulation script compiled

**Run**:
```bash
make ns3
```

**Output**:
- `/tmp/ns3-uav-full.csv` - Radio measurement data

**CSV Format**:
```
time,cell_id,rsrp_dbm,rsrq_db,x,y,z
0.0,1,-105.23,12.45,100.0,100.0,100.0
...
```

### Experiment 2: xApp Integration Test

**Purpose**: Test closed-loop control with O-RAN xApp

**Prerequisites**:
- xApp service running at `http://localhost:5000`
- CSV data file available

**Run**:
```bash
make xapp
```

**Output**:
- `results/ns3-lte/ns3_xapp_full_integration.json`

**Metrics**:
- Total samples processed
- Average RSRP
- Handover recommendations
- Maintain decisions

### Experiment 3: Multi-Scenario Analysis

**Purpose**: Compare xApp performance under different conditions

**Scenarios**:

| Scenario | UAV Speed | PRB Utilization | Description |
|----------|-----------|-----------------|-------------|
| baseline | 10 m/s | 50% | Normal conditions |
| fast_uav | 20 m/s | 50% | High mobility |
| slow_uav | 5 m/s | 50% | Low mobility |
| high_load | 10 m/s | 80% | High network load |

**Run**:
```bash
make scenarios
```

**Output**:
- `results/scenarios/baseline_*.json`
- `results/scenarios/fast_uav_*.json`
- `results/scenarios/slow_uav_*.json`
- `results/scenarios/high_load_*.json`
- `results/scenarios/comparison_summary_*.json`

### Experiment 4: Baseline Comparison

**Purpose**: Quantify xApp improvement over fixed resource allocation

**Comparison**:
- **Baseline**: Fixed PRB=10, reactive handover
- **xApp**: Dynamic PRB allocation, intelligent handover

**Run**:
```bash
make comparison
```

**Output**:
- `results/comparison/comparison_results_*.json`
- `results/comparison/comparison_table_*.txt`
- `results/comparison/comparison_summary_*.csv`

**Key Metrics**:
- Resource efficiency improvement (%)
- PRB savings (%)
- Handover delay reduction (%)
- Throughput improvement (%)

### Figure Generation

**Run**:
```bash
make figures
```

**Output Files**:
- `results/figures/rsrp_timeline_handover.png` - RSRP over time with handover events
- `results/figures/xapp_decisions.png` - xApp decision distribution
- `results/figures/uav_trajectory.png` - UAV flight path with cell coverage
- `results/figures/sinr_analysis.png` - SINR analysis over time
- `results/figures/summary_statistics.txt` - Summary metrics

### LaTeX Table Generation

**Run**:
```bash
make latex
```

**Output Files**:
- `results/latex/table1_simulation_parameters.tex`
- `results/latex/table2_multi_scenario_performance.tex`
- `results/latex/table3_performance_improvement.tex`
- `results/latex/table4_system_configuration.tex`
- `results/latex/tables.tex` (combined)

**Usage in LaTeX**:
```latex
\usepackage{booktabs}
\input{tables.tex}
```

---

## Expected Results

### Signal Quality Metrics

| Metric | Expected Range |
|--------|----------------|
| Average RSRP | -108 to -115 dBm |
| Min RSRP | < -120 dBm (cell edge) |
| Max RSRP | > -105 dBm (near eNB) |
| Average SINR | 8-15 dB |

### xApp Performance

| Metric | Baseline | xApp | Improvement |
|--------|----------|------|-------------|
| Resource Efficiency | ~0.6 Mbps/PRB | ~0.9 Mbps/PRB | +50% |
| PRB Utilization | 10% fixed | 7-8% avg | -20-30% |
| Handover Delay | 100ms | 60ms | -40% |

### Scenario Comparison

| Scenario | Handover Rate | Avg RSRP (dBm) |
|----------|---------------|----------------|
| Baseline | ~3% | -111.5 |
| Fast UAV | ~5% | -112.0 |
| Slow UAV | ~2% | -111.0 |
| High Load | ~3% | -111.5 |

---

## Troubleshooting

### Common Issues

#### 1. xApp Connection Failed

**Symptom**:
```
ERROR: xApp is not running at http://localhost:5000
```

**Solution**:
```bash
# Check if xApp is running
curl http://localhost:5000/health

# Start the xApp if needed
cd ../xapp && ./start_xapp.sh
```

#### 2. CSV Data Not Found

**Symptom**:
```
ERROR: CSV file not found: /tmp/ns3-uav-full.csv
```

**Solution**:
```bash
# Run ns-3 simulation first
make ns3

# Or specify custom CSV path
CSV_PATH=/path/to/data.csv make xapp
```

#### 3. Python Module Not Found

**Symptom**:
```
ModuleNotFoundError: No module named 'matplotlib'
```

**Solution**:
```bash
pip install -r requirements.txt
```

#### 4. ns-3 Build Failed

**Symptom**:
```
ERROR: ns-3 build failed
```

**Solution**:
```bash
# Verify ns-3 installation
ls /opt/ns-oran

# Check ns-3 version
cd /opt/ns-oran && python3 ns3 --version

# Rebuild
python3 ns3 configure --enable-examples
python3 ns3 build
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| NS3_DIR | /opt/ns-oran | ns-3 installation path |
| XAPP_URL | http://localhost:5000 | xApp service URL |
| CSV_PATH | /tmp/ns3-uav-full.csv | Input CSV file path |

**Example**:
```bash
NS3_DIR=/custom/ns3 XAPP_URL=http://192.168.1.100:5000 make all
```

---

## Directory Structure

```
ns3-uav-simulation/
|-- run_all_experiments.sh     # Main automation script
|-- Makefile                   # Build automation
|-- requirements.txt           # Python dependencies
|-- EXPERIMENT_README.md       # This file
|
|-- baseline_comparison.py     # Baseline vs xApp comparison
|-- generate_latex_tables.py   # LaTeX table generator
|-- generate_paper_figures.py  # Figure generator
|-- multi_scenario_test.py     # Multi-scenario analysis
|-- ns3_xapp_integration.py    # xApp integration test
|
|-- scripts/
|   |-- run_baseline.sh        # ns-3 baseline runner
|   |-- run_xapp_controlled_test.py
|
|-- results/
|   |-- ns3-lte/               # ns-3 integration results
|   |-- comparison/            # Baseline comparison results
|   |-- scenarios/             # Multi-scenario results
|   |-- figures/               # Generated figures
|   |-- latex/                 # LaTeX tables
|
|-- logs/                      # Experiment logs
```

---

## Contact

For issues with experiment reproduction, please open an issue in the project repository.
