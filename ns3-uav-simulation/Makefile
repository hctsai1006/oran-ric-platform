# Makefile for O-RAN UAV Simulation Experiments
#
# Usage:
#   make test      - Run integration tests
#   make figures   - Generate publication figures
#   make latex     - Generate LaTeX tables
#   make all       - Run complete experiment pipeline
#   make clean     - Clean generated results
#   make help      - Show available targets
#

# =============================================================================
# Configuration
# =============================================================================

SHELL := /bin/bash
.PHONY: all test figures latex clean help setup check ns3 xapp scenarios comparison report

# Directories
SCRIPT_DIR := $(shell pwd)
RESULTS_DIR := $(SCRIPT_DIR)/results
LOG_DIR := $(SCRIPT_DIR)/logs
FIGURES_DIR := $(RESULTS_DIR)/figures
LATEX_DIR := $(RESULTS_DIR)/latex
COMPARISON_DIR := $(RESULTS_DIR)/comparison
SCENARIOS_DIR := $(RESULTS_DIR)/scenarios
NS3_LTE_DIR := $(RESULTS_DIR)/ns3-lte

# External dependencies
NS3_DIR ?= /opt/ns-oran
XAPP_URL ?= http://localhost:5000
CSV_PATH ?= /tmp/ns3-uav-full.csv

# Python
PYTHON := python3

# Timestamp
TIMESTAMP := $(shell date +%Y%m%d_%H%M%S)

# =============================================================================
# Main Targets
# =============================================================================

## all: Run complete experiment pipeline (test + figures + latex)
all: setup check test figures latex report
	@echo ""
	@echo "=============================================="
	@echo "All experiments completed successfully!"
	@echo "=============================================="
	@echo "Results: $(RESULTS_DIR)"
	@echo ""

## test: Run all integration tests
test: setup check xapp scenarios comparison
	@echo ""
	@echo "[TEST] All tests completed"

## figures: Generate publication-quality figures
figures: setup $(FIGURES_DIR)
	@echo ""
	@echo "[FIGURES] Generating publication figures..."
	@$(PYTHON) generate_paper_figures.py
	@echo "[FIGURES] Figures saved to: $(FIGURES_DIR)"
	@ls -la $(FIGURES_DIR)/*.png $(FIGURES_DIR)/*.pdf 2>/dev/null || true

## latex: Generate LaTeX tables
latex: setup $(LATEX_DIR)
	@echo ""
	@echo "[LATEX] Generating LaTeX tables..."
	@$(PYTHON) generate_latex_tables.py
	@echo "[LATEX] Tables saved to: $(LATEX_DIR)"
	@ls -la $(LATEX_DIR)/*.tex 2>/dev/null || true

## clean: Remove all generated results
clean:
	@echo "[CLEAN] Cleaning generated results..."
	@rm -rf $(FIGURES_DIR)/*.png $(FIGURES_DIR)/*.pdf 2>/dev/null || true
	@rm -rf $(LATEX_DIR)/*.tex 2>/dev/null || true
	@rm -rf $(COMPARISON_DIR)/*.json $(COMPARISON_DIR)/*.csv $(COMPARISON_DIR)/*.txt 2>/dev/null || true
	@rm -rf $(SCENARIOS_DIR)/*.json 2>/dev/null || true
	@rm -rf $(LOG_DIR)/*.log 2>/dev/null || true
	@rm -rf $(RESULTS_DIR)/experiment_report_*.txt 2>/dev/null || true
	@echo "[CLEAN] Clean completed"

## clean-all: Remove all results including cached data
clean-all: clean
	@echo "[CLEAN-ALL] Removing all results..."
	@rm -rf $(NS3_LTE_DIR)/*.json 2>/dev/null || true
	@echo "[CLEAN-ALL] Complete clean finished"

## help: Show this help message
help:
	@echo ""
	@echo "O-RAN UAV Simulation - Makefile Targets"
	@echo "========================================"
	@echo ""
	@echo "Main Targets:"
	@echo "  make all        - Run complete experiment pipeline"
	@echo "  make test       - Run all integration tests"
	@echo "  make figures    - Generate publication figures"
	@echo "  make latex      - Generate LaTeX tables"
	@echo "  make clean      - Clean generated results"
	@echo "  make clean-all  - Remove all results including cached data"
	@echo ""
	@echo "Individual Targets:"
	@echo "  make setup      - Create required directories"
	@echo "  make check      - Check dependencies"
	@echo "  make ns3        - Run ns-3 simulation (if available)"
	@echo "  make xapp       - Run xApp integration test"
	@echo "  make scenarios  - Run multi-scenario comparison"
	@echo "  make comparison - Run baseline vs xApp comparison"
	@echo "  make report     - Generate final report"
	@echo ""
	@echo "Configuration:"
	@echo "  NS3_DIR=$(NS3_DIR)"
	@echo "  XAPP_URL=$(XAPP_URL)"
	@echo "  CSV_PATH=$(CSV_PATH)"
	@echo ""
	@echo "Examples:"
	@echo "  make all                           # Run everything"
	@echo "  make test figures                  # Run tests and generate figures"
	@echo "  XAPP_URL=http://myhost:5000 make xapp  # Use custom xApp URL"
	@echo ""

# =============================================================================
# Setup and Checks
# =============================================================================

## setup: Create required directories
setup: $(RESULTS_DIR) $(LOG_DIR) $(FIGURES_DIR) $(LATEX_DIR) $(COMPARISON_DIR) $(SCENARIOS_DIR) $(NS3_LTE_DIR)
	@echo "[SETUP] Directories created"

$(RESULTS_DIR):
	@mkdir -p $@

$(LOG_DIR):
	@mkdir -p $@

$(FIGURES_DIR):
	@mkdir -p $@

$(LATEX_DIR):
	@mkdir -p $@

$(COMPARISON_DIR):
	@mkdir -p $@

$(SCENARIOS_DIR):
	@mkdir -p $@

$(NS3_LTE_DIR):
	@mkdir -p $@

## check: Verify dependencies are available
check:
	@echo ""
	@echo "[CHECK] Verifying dependencies..."
	@echo -n "  Python: " && $(PYTHON) --version
	@echo -n "  matplotlib: " && $(PYTHON) -c "import matplotlib; print(matplotlib.__version__)" 2>/dev/null || echo "NOT INSTALLED"
	@echo -n "  numpy: " && $(PYTHON) -c "import numpy; print(numpy.__version__)" 2>/dev/null || echo "NOT INSTALLED"
	@echo -n "  requests: " && $(PYTHON) -c "import requests; print(requests.__version__)" 2>/dev/null || echo "NOT INSTALLED"
	@echo -n "  CSV data: " && (test -f $(CSV_PATH) && echo "$(CSV_PATH) (OK)" || echo "NOT FOUND")
	@echo -n "  xApp service: " && (curl -s --connect-timeout 2 $(XAPP_URL)/health >/dev/null 2>&1 && echo "$(XAPP_URL) (OK)" || echo "NOT AVAILABLE")
	@echo "[CHECK] Dependency check completed"

# =============================================================================
# Experiment Targets
# =============================================================================

## ns3: Run ns-3 LTE simulation
ns3:
	@echo ""
	@echo "[NS3] Running ns-3 simulation..."
	@if [ -d "$(NS3_DIR)" ] && [ -f "$(NS3_DIR)/ns3" ]; then \
		cd $(NS3_DIR) && \
		$(PYTHON) ns3 build scratch/uav-lte-baseline && \
		./build/scratch/ns3.*-uav-lte-baseline-* --simTime=75 --reportInterval=0.1; \
		echo "[NS3] Simulation completed"; \
	else \
		echo "[NS3] WARNING: ns-3 not found at $(NS3_DIR), skipping"; \
	fi

## xapp: Run xApp integration test
xapp: setup check
	@echo ""
	@echo "[XAPP] Running xApp integration test..."
	@if curl -s --connect-timeout 2 $(XAPP_URL)/health >/dev/null 2>&1; then \
		if [ -f "$(CSV_PATH)" ]; then \
			$(PYTHON) ns3_xapp_integration.py \
				--csv $(CSV_PATH) \
				--interval 1.0 \
				--output $(NS3_LTE_DIR)/ns3_xapp_full_integration.json; \
			echo "[XAPP] Integration test completed"; \
		else \
			echo "[XAPP] WARNING: CSV data not found at $(CSV_PATH)"; \
		fi \
	else \
		echo "[XAPP] WARNING: xApp not available at $(XAPP_URL), skipping"; \
	fi

## scenarios: Run multi-scenario comparison test
scenarios: setup check
	@echo ""
	@echo "[SCENARIOS] Running multi-scenario test..."
	@if curl -s --connect-timeout 2 $(XAPP_URL)/health >/dev/null 2>&1; then \
		if [ -f "$(CSV_PATH)" ]; then \
			$(PYTHON) multi_scenario_test.py \
				--csv $(CSV_PATH) \
				--output $(SCENARIOS_DIR); \
			echo "[SCENARIOS] Multi-scenario test completed"; \
		else \
			echo "[SCENARIOS] WARNING: CSV data not found"; \
		fi \
	else \
		echo "[SCENARIOS] WARNING: xApp not available, skipping"; \
	fi

## comparison: Run baseline vs xApp comparison
comparison: setup check
	@echo ""
	@echo "[COMPARISON] Running baseline comparison..."
	@if [ -f "$(CSV_PATH)" ] && [ -f "$(NS3_LTE_DIR)/ns3_xapp_full_integration.json" ]; then \
		$(PYTHON) baseline_comparison.py \
			--csv $(CSV_PATH) \
			--xapp-results $(NS3_LTE_DIR)/ns3_xapp_full_integration.json \
			--output-dir $(COMPARISON_DIR); \
		echo "[COMPARISON] Comparison analysis completed"; \
	else \
		echo "[COMPARISON] WARNING: Required data files not found, skipping"; \
	fi

## report: Generate experiment report
report: setup
	@echo ""
	@echo "[REPORT] Generating experiment report..."
	@REPORT_FILE=$(RESULTS_DIR)/experiment_report_$(TIMESTAMP).txt; \
	echo "=================================================================================" > $$REPORT_FILE; \
	echo "EXPERIMENT RESULTS REPORT" >> $$REPORT_FILE; \
	echo "=================================================================================" >> $$REPORT_FILE; \
	echo "Generated: $$(date)" >> $$REPORT_FILE; \
	echo "" >> $$REPORT_FILE; \
	echo "--- Output Files ---" >> $$REPORT_FILE; \
	find $(RESULTS_DIR) -type f \( -name "*.json" -o -name "*.csv" -o -name "*.png" -o -name "*.pdf" -o -name "*.tex" \) 2>/dev/null | sort >> $$REPORT_FILE; \
	echo "" >> $$REPORT_FILE; \
	echo "[REPORT] Report saved to: $$REPORT_FILE"

# =============================================================================
# Development Targets
# =============================================================================

## lint: Check Python code style
lint:
	@echo "[LINT] Checking Python code..."
	@$(PYTHON) -m py_compile *.py
	@echo "[LINT] All Python files compile successfully"

## install-deps: Install Python dependencies
install-deps:
	@echo "[INSTALL] Installing Python dependencies..."
	@pip install -r requirements.txt
	@echo "[INSTALL] Dependencies installed"

## quick: Quick test run (baseline scenario only)
quick: setup check
	@echo ""
	@echo "[QUICK] Running quick test..."
	@if curl -s --connect-timeout 2 $(XAPP_URL)/health >/dev/null 2>&1 && [ -f "$(CSV_PATH)" ]; then \
		$(PYTHON) multi_scenario_test.py \
			--csv $(CSV_PATH) \
			--output $(SCENARIOS_DIR) \
			--scenarios baseline; \
		echo "[QUICK] Quick test completed"; \
	else \
		echo "[QUICK] WARNING: Prerequisites not met"; \
	fi

# =============================================================================
# Default target
# =============================================================================

.DEFAULT_GOAL := help
