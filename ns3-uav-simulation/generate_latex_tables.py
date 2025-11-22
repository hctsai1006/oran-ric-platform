#!/usr/bin/env python3
"""
LaTeX Table Generator for O-RAN UAV Simulation Results

This script generates publication-ready LaTeX tables from simulation
result JSON files. Tables use booktabs style for professional formatting.

Usage:
    python generate_latex_tables.py

Output:
    - results/latex/table1_simulation_parameters.tex
    - results/latex/table2_multi_scenario_performance.tex
    - results/latex/table3_performance_improvement.tex
    - results/latex/table4_system_configuration.tex
    - results/latex/tables.tex (combined file)
"""

import json
import os
from pathlib import Path
from datetime import datetime


class LatexTableGenerator:
    """Generate LaTeX tables from simulation results."""

    def __init__(self, results_dir: str = "results"):
        self.results_dir = Path(results_dir)
        self.output_dir = self.results_dir / "latex"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load data files
        self.scenario_data = self._load_json("scenarios/comparison_summary_20251121_224738.json")
        self.comparison_data = self._load_json("comparison/comparison_results_20251121_224740.json")
        self.integration_data = self._load_json("ns3-lte/ns3_xapp_full_integration.json")

    def _load_json(self, relative_path: str) -> dict:
        """Load JSON data from file."""
        file_path = self.results_dir / relative_path
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        print(f"Warning: File not found: {file_path}")
        return {}

    def _format_number(self, value, decimals: int = 2) -> str:
        """Format number with specified decimal places."""
        if isinstance(value, (int, float)):
            if decimals == 0:
                return f"{int(value)}"
            return f"{value:.{decimals}f}"
        return str(value)

    def generate_table1_simulation_parameters(self) -> str:
        """
        Generate Table 1: Simulation Parameters

        Contains the key parameters used in the ns-3 LTE simulation.
        """
        table = r"""\begin{table}[htbp]
\centering
\caption{Simulation Parameters}
\label{tab:simulation_parameters}
\begin{tabular}{@{}lll@{}}
\toprule
\textbf{Parameter} & \textbf{Value} & \textbf{Description} \\
\midrule
\multicolumn{3}{l}{\textit{Network Configuration}} \\
Number of eNBs & 3 & LTE base stations \\
Number of UAVs & 1 & Unmanned aerial vehicle \\
Carrier Frequency & 2.1 GHz & LTE Band 1 \\
Bandwidth & 20 MHz & System bandwidth \\
Total PRBs & 100 & Physical resource blocks \\
\midrule
\multicolumn{3}{l}{\textit{UAV Parameters}} \\
Flight Altitude & 100 m & Above ground level \\
UAV Speed (Baseline) & 20 m/s & Default velocity \\
UAV Speed (Fast) & 40 m/s & High-speed scenario \\
UAV Speed (Slow) & 10 m/s & Low-speed scenario \\
Flight Pattern & Linear & Point-to-point trajectory \\
\midrule
\multicolumn{3}{l}{\textit{Channel Model}} \\
Path Loss Model & Cost231 & Urban propagation \\
Fading Model & Nakagami & Multipath fading \\
Shadow Fading & 8 dB & Log-normal std. dev. \\
\midrule
\multicolumn{3}{l}{\textit{Handover Parameters}} \\
RSRP Threshold & $-110$ dBm & Handover trigger \\
Critical Threshold & $-120$ dBm & Service degradation \\
TTT (Time-to-Trigger) & 256 ms & Handover delay \\
Hysteresis & 3 dB & Ping-pong prevention \\
\midrule
\multicolumn{3}{l}{\textit{Simulation Settings}} \\
Duration & 75 s & Total simulation time \\
Sampling Interval & 1 s & Measurement period \\
Slice Type & eMBB & Enhanced mobile broadband \\
\bottomrule
\end{tabular}
\end{table}
"""
        return table

    def generate_table2_multi_scenario_performance(self) -> str:
        """
        Generate Table 2: Multi-Scenario Performance Comparison

        Compares performance metrics across different simulation scenarios.
        """
        scenarios = self.scenario_data.get("scenarios", [])

        # Build table rows
        rows = []
        for scenario in scenarios:
            name = scenario.get("name", "").replace("_", " ").title()
            samples = scenario.get("total_samples", 0)
            avg_rsrp = self._format_number(scenario.get("avg_rsrp", 0))
            min_rsrp = self._format_number(scenario.get("min_rsrp", 0))
            max_rsrp = self._format_number(scenario.get("max_rsrp", 0))
            std_rsrp = self._format_number(scenario.get("rsrp_std", 0))
            duration = self._format_number(scenario.get("simulation_duration", 0), 1)
            handovers = scenario.get("handover_count", 0)

            rows.append(f"{name} & {samples} & {avg_rsrp} & {min_rsrp} & {max_rsrp} & {std_rsrp} & {duration} & {handovers} \\\\")

        rows_str = "\n".join(rows)

        table = rf"""\begin{{table}}[htbp]
\centering
\caption{{Multi-Scenario Performance Comparison}}
\label{{tab:multi_scenario_performance}}
\begin{{tabular}}{{@{{}}lccccccc@{{}}}}
\toprule
\textbf{{Scenario}} & \textbf{{Samples}} & \textbf{{Avg RSRP}} & \textbf{{Min RSRP}} & \textbf{{Max RSRP}} & \textbf{{Std Dev}} & \textbf{{Duration}} & \textbf{{Handovers}} \\
 & & (dBm) & (dBm) & (dBm) & (dB) & (s) & \\
\midrule
{rows_str}
\bottomrule
\end{{tabular}}
\end{{table}}
"""
        return table

    def generate_table3_performance_improvement(self) -> str:
        """
        Generate Table 3: Baseline vs xApp Performance Improvement

        Shows the performance comparison between baseline (fixed PRB) and
        xApp-controlled (dynamic PRB) operation.
        """
        baseline = self.comparison_data.get("baseline_summary", {})
        xapp = self.comparison_data.get("xapp_summary", {})
        improvements = self.comparison_data.get("improvements", {})

        # Format improvement values with sign
        def format_improvement(val):
            if val > 0:
                return f"+{val:.2f}\\%"
            elif val < 0:
                return f"{val:.2f}\\%"
            return "0.00\\%"

        table = rf"""\begin{{table}}[htbp]
\centering
\caption{{Baseline vs xApp Performance Comparison}}
\label{{tab:performance_improvement}}
\begin{{tabular}}{{@{{}}lccc@{{}}}}
\toprule
\textbf{{Metric}} & \textbf{{Baseline}} & \textbf{{xApp}} & \textbf{{Improvement}} \\
\midrule
\multicolumn{{4}}{{l}}{{\textit{{Signal Quality}}}} \\
Average RSRP (dBm) & {self._format_number(baseline.get('avg_rsrp', 0))} & {self._format_number(xapp.get('avg_rsrp', 0))} & {format_improvement(improvements.get('rsrp_improvement_pct', 0))} \\
Min RSRP (dBm) & {self._format_number(baseline.get('min_rsrp', 0))} & {self._format_number(xapp.get('min_rsrp', 0))} & -- \\
Max RSRP (dBm) & {self._format_number(baseline.get('max_rsrp', 0))} & {self._format_number(xapp.get('max_rsrp', 0))} & -- \\
RSRP Std Dev (dB) & {self._format_number(baseline.get('std_rsrp', 0))} & {self._format_number(xapp.get('std_rsrp', 0))} & -- \\
\midrule
\multicolumn{{4}}{{l}}{{\textit{{Channel Quality}}}} \\
Average SINR (dB) & {self._format_number(baseline.get('avg_sinr', 0))} & {self._format_number(xapp.get('avg_sinr', 0))} & {format_improvement(improvements.get('sinr_improvement_pct', 0))} \\
Min SINR (dB) & {self._format_number(baseline.get('min_sinr', 0))} & {self._format_number(xapp.get('min_sinr', 0))} & -- \\
Max SINR (dB) & {self._format_number(baseline.get('max_sinr', 0))} & {self._format_number(xapp.get('max_sinr', 0))} & -- \\
\midrule
\multicolumn{{4}}{{l}}{{\textit{{Throughput \& Efficiency}}}} \\
Avg Throughput (Mbps) & {self._format_number(baseline.get('avg_throughput_mbps', 0))} & {self._format_number(xapp.get('avg_throughput_mbps', 0))} & {format_improvement(improvements.get('throughput_improvement_pct', 0))} \\
Resource Efficiency & {self._format_number(baseline.get('avg_resource_efficiency', 0))} & {self._format_number(xapp.get('avg_resource_efficiency', 0))} & {format_improvement(improvements.get('efficiency_improvement_pct', 0))} \\
PRB Utilization & {self._format_number(baseline.get('prb_utilization', 0) * 100)}\\% & {self._format_number(xapp.get('prb_utilization', 0) * 100)}\\% & {format_improvement(improvements.get('prb_utilization_reduction_pct', 0))} \\
\midrule
\multicolumn{{4}}{{l}}{{\textit{{Handover Performance}}}} \\
Handover Count & {baseline.get('handover_count', 0)} & {xapp.get('handover_count', 0)} & -- \\
Total HO Delay (ms) & {baseline.get('total_handover_delay_ms', 0)} & {xapp.get('total_handover_delay_ms', 0)} & {format_improvement(improvements.get('handover_delay_reduction_pct', 0))} \\
Avg PRB Allocation & {self._format_number(baseline.get('avg_prb', 0))} & {self._format_number(xapp.get('avg_prb', 0))} & {format_improvement(improvements.get('prb_savings_pct', 0))} \\
\midrule
\multicolumn{{4}}{{l}}{{\textit{{Quality Indicators}}}} \\
Samples Below Threshold & {baseline.get('samples_below_threshold', 0)} & {xapp.get('samples_below_threshold', 0)} & -- \\
Critical Samples & {baseline.get('samples_critical', 0)} & {xapp.get('samples_critical', 0)} & -- \\
\bottomrule
\end{{tabular}}
\end{{table}}
"""
        return table

    def generate_table4_system_configuration(self) -> str:
        """
        Generate Table 4: System Configuration

        Details the O-RAN and xApp system configuration parameters.
        """
        config = self.comparison_data.get("configuration", {})

        table = rf"""\begin{{table}}[htbp]
\centering
\caption{{System Configuration}}
\label{{tab:system_configuration}}
\begin{{tabular}}{{@{{}}lll@{{}}}}
\toprule
\textbf{{Component}} & \textbf{{Parameter}} & \textbf{{Value}} \\
\midrule
\multicolumn{{3}}{{l}}{{\textit{{O-RAN Near-RT RIC}}}} \\
 & Platform & OSC Near-RT RIC (I-release) \\
 & E2 Interface & E2AP v2.0 \\
 & A1 Interface & A1AP v2.0 \\
 & Database & SDL (Redis) \\
\midrule
\multicolumn{{3}}{{l}}{{\textit{{xApp Configuration}}}} \\
 & xApp Framework & Python SDK \\
 & Decision Algorithm & RSRP-based reactive \\
 & Communication & RMR + HTTP REST \\
 & Metrics Export & Prometheus/Grafana \\
\midrule
\multicolumn{{3}}{{l}}{{\textit{{Resource Management}}}} \\
 & Baseline PRB & {config.get('baseline_prb', 10)} \\
 & Total PRBs & {config.get('total_prb', 100)} \\
 & Dynamic Range & 5--15 PRBs \\
 & Slice Type & eMBB \\
\midrule
\multicolumn{{3}}{{l}}{{\textit{{Thresholds}}}} \\
 & RSRP Handover & {config.get('rsrp_handover_threshold', -110)} dBm \\
 & RSRP Critical & {config.get('rsrp_critical_threshold', -120)} dBm \\
 & SINR Minimum & 3.0 dB \\
\midrule
\multicolumn{{3}}{{l}}{{\textit{{ns-3 Simulator}}}} \\
 & Version & ns-3.36+ \\
 & LTE Module & LENA \\
 & Mobility Model & ConstantVelocity \\
 & Integration & CSV-based data exchange \\
\bottomrule
\end{{tabular}}
\end{{table}}
"""
        return table

    def generate_combined_tables(self) -> str:
        """Generate a combined file with all tables."""
        timestamp = datetime.now().strftime("%Y-%m-%d")

        combined = rf"""%% LaTeX Tables for O-RAN UAV Simulation Results
%% Generated: {timestamp}
%%
%% Required packages:
%%   \usepackage{{booktabs}}
%%   \usepackage{{array}}
%%
%% Usage: \input{{tables.tex}} or copy individual tables

% =============================================================================
% Table 1: Simulation Parameters
% =============================================================================
{self.generate_table1_simulation_parameters()}

% =============================================================================
% Table 2: Multi-Scenario Performance Comparison
% =============================================================================
{self.generate_table2_multi_scenario_performance()}

% =============================================================================
% Table 3: Baseline vs xApp Performance Improvement
% =============================================================================
{self.generate_table3_performance_improvement()}

% =============================================================================
% Table 4: System Configuration
% =============================================================================
{self.generate_table4_system_configuration()}
"""
        return combined

    def save_tables(self):
        """Save all tables to individual files and combined file."""
        tables = {
            "table1_simulation_parameters.tex": self.generate_table1_simulation_parameters(),
            "table2_multi_scenario_performance.tex": self.generate_table2_multi_scenario_performance(),
            "table3_performance_improvement.tex": self.generate_table3_performance_improvement(),
            "table4_system_configuration.tex": self.generate_table4_system_configuration(),
            "tables.tex": self.generate_combined_tables(),
        }

        saved_files = []
        for filename, content in tables.items():
            filepath = self.output_dir / filename
            with open(filepath, 'w') as f:
                f.write(content)
            saved_files.append(str(filepath))
            print(f"Saved: {filepath}")

        return saved_files

    def preview_tables(self):
        """Print preview of all generated tables."""
        print("=" * 80)
        print("LaTeX Tables Preview")
        print("=" * 80)

        print("\n--- Table 1: Simulation Parameters ---")
        print(self.generate_table1_simulation_parameters())

        print("\n--- Table 2: Multi-Scenario Performance ---")
        print(self.generate_table2_multi_scenario_performance())

        print("\n--- Table 3: Performance Improvement ---")
        print(self.generate_table3_performance_improvement())

        print("\n--- Table 4: System Configuration ---")
        print(self.generate_table4_system_configuration())


def main():
    """Main entry point."""
    print("LaTeX Table Generator for O-RAN UAV Simulation")
    print("-" * 50)

    # Initialize generator
    generator = LatexTableGenerator()

    # Save tables
    saved_files = generator.save_tables()

    print("\n" + "=" * 50)
    print("Generated files:")
    for f in saved_files:
        print(f"  - {f}")

    # Preview tables
    print("\n")
    generator.preview_tables()

    print("\n" + "=" * 50)
    print("Done! Tables saved to results/latex/")
    print("\nTo use in LaTeX document:")
    print("  1. Add \\usepackage{booktabs} to preamble")
    print("  2. Use \\input{tables.tex} or copy individual tables")


if __name__ == "__main__":
    main()
