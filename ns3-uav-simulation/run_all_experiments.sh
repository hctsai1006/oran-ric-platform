#!/bin/bash
#
# Complete Experiment Automation Script
# Purpose: Run all experiments in sequence, collect results, and generate final report
#
# Usage:
#   ./run_all_experiments.sh              # Run all experiments
#   ./run_all_experiments.sh --skip-ns3   # Skip ns-3 simulation (use existing data)
#   ./run_all_experiments.sh --quick      # Quick mode (fewer scenarios)
#

set -e

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NS3_DIR="${NS3_DIR:-/opt/ns-oran}"
XAPP_URL="${XAPP_URL:-http://localhost:5000}"
CSV_PATH="${CSV_PATH:-/tmp/ns3-uav-full.csv}"

# Output directories
RESULTS_DIR="${SCRIPT_DIR}/results"
LOG_DIR="${SCRIPT_DIR}/logs"
FIGURES_DIR="${RESULTS_DIR}/figures"
LATEX_DIR="${RESULTS_DIR}/latex"
COMPARISON_DIR="${RESULTS_DIR}/comparison"
SCENARIOS_DIR="${RESULTS_DIR}/scenarios"

# Timestamp for this run
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RUN_LOG="${LOG_DIR}/experiment_run_${TIMESTAMP}.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Helper Functions
# =============================================================================

log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")

    case $level in
        INFO)  color=$GREEN ;;
        WARN)  color=$YELLOW ;;
        ERROR) color=$RED ;;
        *)     color=$NC ;;
    esac

    echo -e "${color}[${timestamp}] [${level}] ${message}${NC}" | tee -a "$RUN_LOG"
}

section_header() {
    local title=$1
    echo "" | tee -a "$RUN_LOG"
    echo -e "${BLUE}=============================================================================${NC}" | tee -a "$RUN_LOG"
    echo -e "${BLUE}  ${title}${NC}" | tee -a "$RUN_LOG"
    echo -e "${BLUE}=============================================================================${NC}" | tee -a "$RUN_LOG"
    echo "" | tee -a "$RUN_LOG"
}

check_command() {
    local cmd=$1
    if ! command -v "$cmd" &> /dev/null; then
        log ERROR "Required command not found: $cmd"
        return 1
    fi
    log INFO "Found: $cmd ($(which $cmd))"
    return 0
}

# =============================================================================
# Dependency Checks
# =============================================================================

check_dependencies() {
    section_header "Checking Dependencies"

    local all_ok=true

    # Check Python
    if check_command python3; then
        PYTHON_VERSION=$(python3 --version 2>&1)
        log INFO "Python version: $PYTHON_VERSION"
    else
        all_ok=false
    fi

    # Check required Python packages
    log INFO "Checking Python packages..."
    python3 -c "import matplotlib" 2>/dev/null || { log WARN "matplotlib not installed"; all_ok=false; }
    python3 -c "import numpy" 2>/dev/null || { log WARN "numpy not installed"; all_ok=false; }
    python3 -c "import requests" 2>/dev/null || { log WARN "requests not installed"; all_ok=false; }
    log INFO "Python packages OK"

    # Check ns-3 (optional)
    if [ "$SKIP_NS3" != "true" ]; then
        if [ -d "$NS3_DIR" ]; then
            log INFO "ns-3 directory found: $NS3_DIR"
            if [ -f "$NS3_DIR/ns3" ]; then
                log INFO "ns-3 build system available"
            else
                log WARN "ns-3 build system not found - will skip ns-3 simulation"
                SKIP_NS3=true
            fi
        else
            log WARN "ns-3 directory not found: $NS3_DIR - will skip ns-3 simulation"
            SKIP_NS3=true
        fi
    fi

    # Check xApp service
    log INFO "Checking xApp service at $XAPP_URL..."
    if curl -s --connect-timeout 5 "${XAPP_URL}/health" > /dev/null 2>&1; then
        log INFO "xApp service is running"
        XAPP_AVAILABLE=true
    else
        log WARN "xApp service is not available at $XAPP_URL"
        XAPP_AVAILABLE=false
    fi

    # Check CSV data
    if [ -f "$CSV_PATH" ]; then
        local csv_lines=$(wc -l < "$CSV_PATH")
        log INFO "CSV data file found: $CSV_PATH ($csv_lines lines)"
        CSV_AVAILABLE=true
    else
        log WARN "CSV data file not found: $CSV_PATH"
        CSV_AVAILABLE=false
    fi

    # Summary
    echo ""
    log INFO "Dependency check summary:"
    log INFO "  - Python: OK"
    log INFO "  - ns-3: $([ "$SKIP_NS3" = "true" ] && echo "SKIP" || echo "OK")"
    log INFO "  - xApp: $([ "$XAPP_AVAILABLE" = "true" ] && echo "OK" || echo "NOT AVAILABLE")"
    log INFO "  - CSV Data: $([ "$CSV_AVAILABLE" = "true" ] && echo "OK" || echo "NOT FOUND")"

    return 0
}

# =============================================================================
# Setup
# =============================================================================

setup_directories() {
    section_header "Setting Up Directories"

    mkdir -p "$RESULTS_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$FIGURES_DIR"
    mkdir -p "$LATEX_DIR"
    mkdir -p "$COMPARISON_DIR"
    mkdir -p "$SCENARIOS_DIR"

    log INFO "Created results directories"
    log INFO "Run log: $RUN_LOG"
}

# =============================================================================
# Experiment 1: ns-3 Simulation
# =============================================================================

run_ns3_simulation() {
    section_header "Experiment 1: ns-3 LTE Simulation"

    if [ "$SKIP_NS3" = "true" ]; then
        log INFO "Skipping ns-3 simulation (--skip-ns3 flag or ns-3 not available)"
        return 0
    fi

    log INFO "Running ns-3 UAV LTE simulation..."

    cd "$NS3_DIR"

    # Build simulation
    log INFO "Building ns-3 simulation..."
    if python3 ns3 build scratch/uav-lte-baseline >> "$RUN_LOG" 2>&1; then
        log INFO "Build successful"
    else
        log ERROR "ns-3 build failed - check $RUN_LOG for details"
        return 1
    fi

    # Run simulation
    log INFO "Running simulation (this may take a few minutes)..."
    if ./build/scratch/ns3.*-uav-lte-baseline-* \
        --simTime=75 \
        --reportInterval=0.1 \
        >> "$RUN_LOG" 2>&1; then
        log INFO "Simulation completed successfully"
    else
        log ERROR "Simulation failed - check $RUN_LOG for details"
        return 1
    fi

    # Copy results
    if [ -f "/tmp/ns3-uav-full.csv" ]; then
        cp /tmp/ns3-uav-full.csv "${RESULTS_DIR}/ns3-lte/"
        log INFO "Simulation results copied to ${RESULTS_DIR}/ns3-lte/"
    fi

    cd "$SCRIPT_DIR"
    return 0
}

# =============================================================================
# Experiment 2: xApp Integration Test
# =============================================================================

run_xapp_integration() {
    section_header "Experiment 2: xApp Integration Test"

    if [ "$XAPP_AVAILABLE" != "true" ]; then
        log WARN "Skipping xApp integration test - service not available"
        return 0
    fi

    if [ "$CSV_AVAILABLE" != "true" ]; then
        log WARN "Skipping xApp integration test - CSV data not available"
        return 0
    fi

    log INFO "Running xApp integration test..."

    local output_file="${RESULTS_DIR}/ns3-lte/ns3_xapp_full_integration.json"

    python3 "${SCRIPT_DIR}/ns3_xapp_integration.py" \
        --csv "$CSV_PATH" \
        --interval 1.0 \
        --output "$output_file" \
        >> "$RUN_LOG" 2>&1

    if [ $? -eq 0 ]; then
        log INFO "xApp integration test completed"
        log INFO "Results saved to: $output_file"
    else
        log ERROR "xApp integration test failed"
        return 1
    fi

    return 0
}

# =============================================================================
# Experiment 3: Multi-Scenario Test
# =============================================================================

run_multi_scenario_test() {
    section_header "Experiment 3: Multi-Scenario Analysis"

    if [ "$XAPP_AVAILABLE" != "true" ]; then
        log WARN "Skipping multi-scenario test - xApp service not available"
        return 0
    fi

    if [ "$CSV_AVAILABLE" != "true" ]; then
        log WARN "Skipping multi-scenario test - CSV data not available"
        return 0
    fi

    log INFO "Running multi-scenario comparison test..."

    local scenarios="baseline fast_uav slow_uav high_load"
    if [ "$QUICK_MODE" = "true" ]; then
        scenarios="baseline fast_uav"
        log INFO "Quick mode: running only baseline and fast_uav scenarios"
    fi

    python3 "${SCRIPT_DIR}/multi_scenario_test.py" \
        --csv "$CSV_PATH" \
        --output "$SCENARIOS_DIR" \
        --scenarios $scenarios \
        >> "$RUN_LOG" 2>&1

    if [ $? -eq 0 ]; then
        log INFO "Multi-scenario test completed"
    else
        log ERROR "Multi-scenario test failed"
        return 1
    fi

    return 0
}

# =============================================================================
# Experiment 4: Baseline Comparison
# =============================================================================

run_baseline_comparison() {
    section_header "Experiment 4: Baseline vs xApp Comparison"

    if [ "$CSV_AVAILABLE" != "true" ]; then
        log WARN "Skipping baseline comparison - CSV data not available"
        return 0
    fi

    local xapp_results="${RESULTS_DIR}/ns3-lte/ns3_xapp_full_integration.json"
    if [ ! -f "$xapp_results" ]; then
        log WARN "Skipping baseline comparison - xApp results not found"
        return 0
    fi

    log INFO "Running baseline vs xApp comparison analysis..."

    python3 "${SCRIPT_DIR}/baseline_comparison.py" \
        --csv "$CSV_PATH" \
        --xapp-results "$xapp_results" \
        --output-dir "$COMPARISON_DIR" \
        >> "$RUN_LOG" 2>&1

    if [ $? -eq 0 ]; then
        log INFO "Baseline comparison completed"
    else
        log ERROR "Baseline comparison failed"
        return 1
    fi

    return 0
}

# =============================================================================
# Generate Figures
# =============================================================================

generate_figures() {
    section_header "Generating Publication Figures"

    local integration_results="${RESULTS_DIR}/ns3-lte/ns3_xapp_full_integration.json"
    if [ ! -f "$integration_results" ]; then
        log WARN "Skipping figure generation - integration results not found"
        return 0
    fi

    log INFO "Generating paper-quality figures..."

    python3 "${SCRIPT_DIR}/generate_paper_figures.py" >> "$RUN_LOG" 2>&1

    if [ $? -eq 0 ]; then
        log INFO "Figures generated successfully"
        log INFO "Figures saved to: $FIGURES_DIR"

        # List generated figures
        echo ""
        log INFO "Generated files:"
        ls -lh "$FIGURES_DIR"/*.png "$FIGURES_DIR"/*.pdf 2>/dev/null | while read line; do
            log INFO "  $line"
        done
    else
        log ERROR "Figure generation failed"
        return 1
    fi

    return 0
}

# =============================================================================
# Generate LaTeX Tables
# =============================================================================

generate_latex_tables() {
    section_header "Generating LaTeX Tables"

    log INFO "Generating LaTeX tables..."

    python3 "${SCRIPT_DIR}/generate_latex_tables.py" >> "$RUN_LOG" 2>&1

    if [ $? -eq 0 ]; then
        log INFO "LaTeX tables generated successfully"
        log INFO "Tables saved to: $LATEX_DIR"

        # List generated files
        echo ""
        log INFO "Generated files:"
        ls -lh "$LATEX_DIR"/*.tex 2>/dev/null | while read line; do
            log INFO "  $line"
        done
    else
        log ERROR "LaTeX table generation failed"
        return 1
    fi

    return 0
}

# =============================================================================
# Generate Final Report
# =============================================================================

generate_final_report() {
    section_header "Generating Final Report"

    local report_file="${RESULTS_DIR}/experiment_report_${TIMESTAMP}.txt"

    cat > "$report_file" << EOF
================================================================================
EXPERIMENT RESULTS REPORT
================================================================================
Generated: $(date)
Run ID: ${TIMESTAMP}

================================================================================
ENVIRONMENT
================================================================================
Working Directory: ${SCRIPT_DIR}
ns-3 Directory: ${NS3_DIR}
xApp URL: ${XAPP_URL}
CSV Data Path: ${CSV_PATH}

================================================================================
EXPERIMENT SUMMARY
================================================================================
EOF

    # Add experiment results if available
    if [ -f "${RESULTS_DIR}/ns3-lte/ns3_xapp_full_integration.json" ]; then
        echo "" >> "$report_file"
        echo "--- xApp Integration Results ---" >> "$report_file"
        python3 -c "
import json
with open('${RESULTS_DIR}/ns3-lte/ns3_xapp_full_integration.json') as f:
    data = json.load(f)
    print(f\"Total Samples: {data.get('total_samples', 'N/A')}\")
    print(f\"Average RSRP: {data.get('avg_rsrp', 'N/A'):.2f} dBm\")
    print(f\"Handover Recommendations: {data.get('handover_recommendations', 'N/A')}\")
    print(f\"Maintain Decisions: {data.get('maintain_decisions', 'N/A')}\")
" >> "$report_file" 2>/dev/null || echo "Could not parse integration results" >> "$report_file"
    fi

    # Add comparison results if available
    local comparison_file=$(ls -t "${COMPARISON_DIR}"/comparison_results_*.json 2>/dev/null | head -1)
    if [ -n "$comparison_file" ] && [ -f "$comparison_file" ]; then
        echo "" >> "$report_file"
        echo "--- Performance Comparison ---" >> "$report_file"
        python3 -c "
import json
with open('$comparison_file') as f:
    data = json.load(f)
    improvements = data.get('improvements', {})
    print(f\"Resource Efficiency Improvement: {improvements.get('efficiency_improvement_pct', 'N/A'):.2f}%\")
    print(f\"PRB Savings: {improvements.get('prb_savings_pct', 'N/A'):.2f}%\")
    print(f\"Handover Delay Reduction: {improvements.get('handover_delay_reduction_pct', 'N/A'):.2f}%\")
" >> "$report_file" 2>/dev/null || echo "Could not parse comparison results" >> "$report_file"
    fi

    # Add file listings
    cat >> "$report_file" << EOF

================================================================================
OUTPUT FILES
================================================================================
EOF

    echo "--- Results Directory ---" >> "$report_file"
    find "$RESULTS_DIR" -type f -name "*.json" -o -name "*.csv" -o -name "*.txt" -o -name "*.png" -o -name "*.pdf" -o -name "*.tex" 2>/dev/null | sort >> "$report_file"

    cat >> "$report_file" << EOF

================================================================================
END OF REPORT
================================================================================
EOF

    log INFO "Final report generated: $report_file"

    # Print summary to console
    echo ""
    log INFO "==============================================="
    log INFO "EXPERIMENT RUN COMPLETE"
    log INFO "==============================================="
    log INFO "Run ID: ${TIMESTAMP}"
    log INFO "Results Directory: ${RESULTS_DIR}"
    log INFO "Log File: ${RUN_LOG}"
    log INFO "Report: ${report_file}"
    echo ""

    return 0
}

# =============================================================================
# Main
# =============================================================================

main() {
    # Parse arguments
    SKIP_NS3=false
    QUICK_MODE=false

    for arg in "$@"; do
        case $arg in
            --skip-ns3)
                SKIP_NS3=true
                ;;
            --quick)
                QUICK_MODE=true
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --skip-ns3    Skip ns-3 simulation (use existing CSV data)"
                echo "  --quick       Quick mode (fewer scenarios)"
                echo "  --help, -h    Show this help message"
                exit 0
                ;;
        esac
    done

    # Setup
    setup_directories

    # Start logging
    echo "Experiment Run Started: $(date)" > "$RUN_LOG"
    echo "Arguments: $@" >> "$RUN_LOG"
    echo "" >> "$RUN_LOG"

    section_header "O-RAN UAV Simulation Experiment Suite"
    log INFO "Starting experiment run: ${TIMESTAMP}"
    log INFO "Working directory: ${SCRIPT_DIR}"

    # Check dependencies
    check_dependencies

    # Run experiments
    local experiments_run=0
    local experiments_failed=0

    # Experiment 1: ns-3 Simulation
    if run_ns3_simulation; then
        ((experiments_run++))
    else
        ((experiments_failed++))
    fi

    # Experiment 2: xApp Integration
    if run_xapp_integration; then
        ((experiments_run++))
    else
        ((experiments_failed++))
    fi

    # Experiment 3: Multi-Scenario
    if run_multi_scenario_test; then
        ((experiments_run++))
    else
        ((experiments_failed++))
    fi

    # Experiment 4: Baseline Comparison
    if run_baseline_comparison; then
        ((experiments_run++))
    else
        ((experiments_failed++))
    fi

    # Generate outputs
    if generate_figures; then
        ((experiments_run++))
    else
        ((experiments_failed++))
    fi

    if generate_latex_tables; then
        ((experiments_run++))
    else
        ((experiments_failed++))
    fi

    # Generate final report
    generate_final_report

    # Final summary
    section_header "Experiment Suite Summary"
    log INFO "Experiments completed: ${experiments_run}"
    log INFO "Experiments failed: ${experiments_failed}"

    if [ $experiments_failed -gt 0 ]; then
        log WARN "Some experiments failed - check log file for details"
        exit 1
    else
        log INFO "All experiments completed successfully"
        exit 0
    fi
}

# Run main function
main "$@"
