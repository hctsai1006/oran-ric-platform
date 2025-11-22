#!/bin/bash
#
# UAV LTE Baseline Simulation Runner
# Purpose: Execute baseline simulation without xApp control
#

set -e

NS3_DIR="/opt/ns-oran"
OUTPUT_DIR="/home/thc1006/dev/oran-ric-platform/ns3-uav-simulation/results/baseline"
LOG_FILE="/home/thc1006/dev/oran-ric-platform/ns3-uav-simulation/logs/baseline_run.log"

echo "=============================================="
echo "UAV LTE Baseline Simulation"
echo "=============================================="
echo "Start Time: $(date)"
echo ""

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Build the simulation
echo "[1/3] Building simulation..."
cd "$NS3_DIR"
python3 ns3 build scratch/uav-lte-baseline 2>&1 | tee -a "$LOG_FILE"

if [ $? -ne 0 ]; then
    echo "ERROR: Build failed!"
    exit 1
fi

echo "[2/3] Running baseline simulation..."
echo "  - Simulation time: 100 seconds"
echo "  - UAV path: (100,100) -> (900,900)"
echo "  - Output: $OUTPUT_DIR"
echo ""

# Run simulation
./build/scratch/ns3.38.rc1-uav-lte-baseline-default \
    --simTime=100 \
    --reportInterval=0.5 \
    --outputDir="$OUTPUT_DIR/" \
    --verbose=true \
    2>&1 | tee -a "$LOG_FILE"

echo ""
echo "[3/3] Simulation complete!"
echo "Results saved to: $OUTPUT_DIR"
echo "End Time: $(date)"

# List output files
echo ""
echo "Output files:"
ls -lh "$OUTPUT_DIR"/*.csv "$OUTPUT_DIR"/*.txt 2>/dev/null || echo "No output files found"
