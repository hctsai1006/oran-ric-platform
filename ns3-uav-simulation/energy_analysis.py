#!/usr/bin/env python3
"""
Energy Efficiency Analysis for UAV xApp

Comprehensive energy analysis including:
1. PRB Energy Model - Energy per PRB using standard LTE power model
2. UAV Battery Impact - Transmission power vs RSRP relationship
3. Network Energy - eNB energy consumption comparison

Based on assumptions:
- PRB power: 0.5W per PRB
- UAV Tx power: 23 dBm max
- eNB power per PRB: 1W

Generates:
- Energy efficiency comparison bar chart
- Energy vs throughput trade-off curve
- LaTeX table with energy metrics
- JSON results
"""

import csv
import json
import math
import statistics
import argparse
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# =============================================================================
# Energy Model Constants
# =============================================================================

# PRB Power Model (per user allocation assumptions)
PRB_POWER_W = 0.5           # Power per PRB (W) - UE side
ENB_POWER_PER_PRB_W = 1.0   # eNB power per PRB (W) - network side
ENB_STATIC_POWER_W = 50.0   # eNB static/baseline power (W)

# UAV Transmission Power Model
UAV_MAX_TX_POWER_DBM = 23.0  # Max UAV transmit power (dBm) - LTE UE Class 3
UAV_MIN_TX_POWER_DBM = -40.0 # Min UAV transmit power (dBm)

# Power control parameters
TARGET_SINR_DB = 10.0        # Target SINR for power control
PATH_LOSS_EXPONENT = 3.5     # Urban/suburban path loss exponent
REFERENCE_DISTANCE_M = 1.0   # Reference distance for path loss
REFERENCE_PATH_LOSS_DB = 30.0 # Path loss at reference distance

# UAV Battery Model
UAV_BATTERY_CAPACITY_WH = 100.0  # Typical UAV battery (Wh)
UAV_FLIGHT_POWER_W = 150.0       # Power for flight (hovering) (W)
UAV_COMMS_BASE_POWER_W = 2.0     # Base communication power (W)

# LTE System Parameters
PRB_BANDWIDTH_HZ = 180e3     # 180 kHz per PRB (LTE)
TOTAL_PRB = 100              # Total PRBs in cell
SAMPLE_INTERVAL_S = 1.0      # Sample interval (seconds)

# Simulation duration
DEFAULT_SIM_DURATION_S = 77  # Default simulation duration

# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class EnergyMetrics:
    """Energy metrics for a single sample."""
    time: float
    cell_id: int
    rsrp_dbm: float
    sinr_db: float
    prb_allocation: int

    # Calculated energy metrics
    ue_tx_power_dbm: float = 0.0
    ue_tx_power_w: float = 0.0
    prb_energy_j: float = 0.0
    enb_energy_j: float = 0.0
    total_energy_j: float = 0.0
    throughput_mbps: float = 0.0
    energy_efficiency_bits_per_j: float = 0.0
    battery_drain_w: float = 0.0


@dataclass
class AlgorithmEnergyResults:
    """Energy analysis results for an algorithm."""
    name: str
    total_samples: int = 0
    simulation_duration_s: float = 0.0

    # PRB Energy Model
    total_prb_energy_j: float = 0.0
    avg_prb_energy_per_sample_j: float = 0.0
    avg_prb_allocation: float = 0.0

    # Throughput
    total_throughput_mb: float = 0.0
    avg_throughput_mbps: float = 0.0

    # Energy Efficiency
    energy_efficiency_bits_per_j: float = 0.0
    energy_efficiency_mb_per_j: float = 0.0

    # UAV Battery Impact
    avg_tx_power_dbm: float = 0.0
    avg_tx_power_w: float = 0.0
    total_tx_energy_j: float = 0.0
    estimated_battery_drain_percent: float = 0.0
    estimated_flight_time_extension_percent: float = 0.0

    # Network Energy (eNB)
    total_enb_energy_j: float = 0.0
    avg_enb_power_w: float = 0.0

    # Total System Energy
    total_system_energy_j: float = 0.0

    # RSRP statistics for reference
    avg_rsrp_dbm: float = 0.0
    avg_sinr_db: float = 0.0


# =============================================================================
# Energy Calculation Functions
# =============================================================================

def rsrp_to_path_loss(rsrp_dbm: float, tx_power_dbm: float = UAV_MAX_TX_POWER_DBM) -> float:
    """Calculate path loss from RSRP measurement."""
    # Path loss = Tx Power - RSRP
    return tx_power_dbm - rsrp_dbm


def calculate_ue_tx_power(rsrp_dbm: float, target_sinr_db: float = TARGET_SINR_DB) -> float:
    """
    Calculate required UE transmit power using open-loop power control.

    Based on 3GPP TS 36.213 uplink power control:
    P_tx = min(P_max, P_0 + alpha * PL + 10*log10(M) + delta_TF + f(i))

    Simplified model:
    - Higher path loss (lower RSRP) requires higher Tx power
    - Power is clamped to [P_min, P_max]
    """
    # Estimate path loss from RSRP
    # Assuming eNB Tx power of ~46 dBm
    path_loss_db = 46.0 - rsrp_dbm

    # Simple power control: compensate for path loss
    # P_tx = P_0 + alpha * PL
    p0_dbm = -80.0  # Base power level
    alpha = 0.8     # Path loss compensation factor

    tx_power_dbm = p0_dbm + alpha * path_loss_db

    # Clamp to valid range
    tx_power_dbm = max(UAV_MIN_TX_POWER_DBM, min(UAV_MAX_TX_POWER_DBM, tx_power_dbm))

    return tx_power_dbm


def calculate_ue_tx_power_with_prb(rsrp_dbm: float, prb: int, sinr_db: float) -> float:
    """
    Calculate UE transmit power considering PRB allocation and channel quality.

    More PRBs allow for lower per-PRB power while maintaining the same total throughput.
    Better channel quality (higher SINR/RSRP) allows lower Tx power.

    This models the energy-saving potential of intelligent PRB allocation:
    - More PRBs spread power over wider bandwidth (lower spectral power density)
    - Better channel conditions require less power boosting
    """
    # Base path loss estimation
    path_loss_db = 46.0 - rsrp_dbm

    # Base power calculation
    p0_dbm = -80.0
    alpha = 0.8
    base_tx_power_dbm = p0_dbm + alpha * path_loss_db

    # PRB-based power adjustment
    # More PRBs -> can use lower power density
    # Reference: 10 PRBs is baseline
    prb_factor_db = 10 * math.log10(10 / max(5, prb)) if prb > 0 else 0

    # Channel quality adjustment
    # Better SINR -> less power boosting needed
    if sinr_db > 15:
        sinr_adjustment_db = -2  # Good channel, reduce power
    elif sinr_db > 10:
        sinr_adjustment_db = -1
    elif sinr_db > 5:
        sinr_adjustment_db = 0
    else:
        sinr_adjustment_db = 1  # Poor channel, boost power

    # Cell edge adjustment based on RSRP
    if rsrp_dbm < -118:
        edge_adjustment_db = 2  # Very edge, need more power
    elif rsrp_dbm < -115:
        edge_adjustment_db = 1
    elif rsrp_dbm > -105:
        edge_adjustment_db = -1  # Good coverage, reduce power
    else:
        edge_adjustment_db = 0

    # Final Tx power
    tx_power_dbm = base_tx_power_dbm + prb_factor_db + sinr_adjustment_db + edge_adjustment_db

    # Clamp to valid range
    tx_power_dbm = max(UAV_MIN_TX_POWER_DBM, min(UAV_MAX_TX_POWER_DBM, tx_power_dbm))

    return tx_power_dbm


def dbm_to_watts(power_dbm: float) -> float:
    """Convert power from dBm to Watts."""
    return 10 ** ((power_dbm - 30) / 10)


def calculate_throughput(sinr_db: float, prb: int) -> float:
    """Calculate throughput using Shannon capacity formula."""
    sinr_linear = 10 ** (sinr_db / 10)
    spectral_efficiency = math.log2(1 + sinr_linear)
    bandwidth_hz = prb * PRB_BANDWIDTH_HZ
    throughput_mbps = (bandwidth_hz * spectral_efficiency) / 1e6
    return throughput_mbps


def calculate_prb_energy(prb: int, duration_s: float = SAMPLE_INTERVAL_S) -> float:
    """Calculate energy consumed by PRB allocation (Joules)."""
    power_w = prb * PRB_POWER_W
    energy_j = power_w * duration_s
    return energy_j


def calculate_enb_energy(prb: int, duration_s: float = SAMPLE_INTERVAL_S) -> float:
    """Calculate eNB energy for serving this PRB allocation (Joules)."""
    # eNB energy = static power + dynamic power per PRB
    power_w = ENB_STATIC_POWER_W + (prb * ENB_POWER_PER_PRB_W)
    energy_j = power_w * duration_s
    return energy_j


def calculate_battery_drain_rate(tx_power_w: float) -> float:
    """Calculate total UAV battery drain rate (Watts)."""
    # Total power = flight power + communication power
    comm_power = UAV_COMMS_BASE_POWER_W + tx_power_w
    total_power = UAV_FLIGHT_POWER_W + comm_power
    return total_power


# =============================================================================
# PRB Allocation Algorithms (Simplified)
# =============================================================================

def baseline_prb_allocation(rsrp_dbm: float, sinr_db: float) -> int:
    """Baseline: Fixed PRB allocation."""
    return 10


def xapp_prb_allocation(rsrp_dbm: float, sinr_db: float) -> int:
    """
    xApp dynamic PRB allocation based on channel conditions.
    Optimized for energy efficiency while maintaining QoS.
    """
    # Base allocation based on SINR
    if sinr_db > 15:
        base_prb = 6   # High SINR - efficient use
    elif sinr_db > 10:
        base_prb = 8
    elif sinr_db > 5:
        base_prb = 10
    else:
        base_prb = 12   # Low SINR - need more PRBs

    # Cell edge compensation
    if rsrp_dbm < -118:
        base_prb += 4
    elif rsrp_dbm < -115:
        base_prb += 2
    elif rsrp_dbm < -110:
        base_prb += 1

    # Energy optimization: reduce when conditions are good
    if sinr_db > 18 and rsrp_dbm > -105:
        base_prb = max(5, base_prb - 2)

    return max(5, min(20, base_prb))


def greedy_prb_allocation(rsrp_dbm: float, sinr_db: float) -> int:
    """Greedy: Proportional to SINR (higher SINR = more PRBs)."""
    sinr_normalized = (sinr_db + 5) / 30
    sinr_normalized = max(0, min(1, sinr_normalized))
    prb = int(5 + sinr_normalized * 15)
    return max(5, min(20, prb))


def conservative_prb_allocation(rsrp_dbm: float, sinr_db: float) -> int:
    """Conservative: Fixed base with minimal adjustments."""
    prb = 8
    if sinr_db < 5:
        prb += 2
    if rsrp_dbm < -115:
        prb += 2
    return max(5, min(15, prb))


def energy_optimal_prb_allocation(rsrp_dbm: float, sinr_db: float) -> int:
    """
    Energy-optimal PRB allocation.
    Minimizes energy while meeting minimum throughput requirement.
    """
    # Target minimum throughput: 3 Mbps
    target_throughput_mbps = 3.0

    # Calculate minimum PRBs needed for target throughput
    sinr_linear = 10 ** (sinr_db / 10)
    spectral_efficiency = math.log2(1 + sinr_linear)

    if spectral_efficiency > 0:
        min_prbs = math.ceil(target_throughput_mbps * 1e6 / (spectral_efficiency * PRB_BANDWIDTH_HZ))
    else:
        min_prbs = 15

    # Add margin for cell edge
    if rsrp_dbm < -115:
        min_prbs += 2

    return max(5, min(15, min_prbs))


# Algorithm mapping
ALGORITHMS = {
    "Baseline (Fixed)": baseline_prb_allocation,
    "xApp (Adaptive)": xapp_prb_allocation,
    "Greedy": greedy_prb_allocation,
    "Conservative": conservative_prb_allocation,
    "Energy-Optimal": energy_optimal_prb_allocation,
}


# =============================================================================
# Data Loading
# =============================================================================

def load_csv_data(csv_path: str, sample_interval: float = 1.0) -> List[Dict]:
    """Load measurement data from CSV file."""
    samples = []
    last_time = -sample_interval

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sim_time = float(row['time'])
            if sim_time - last_time >= sample_interval:
                last_time = sim_time
                samples.append({
                    "time": sim_time,
                    "cell_id": int(row['cell_id']),
                    "rsrp_dbm": float(row['rsrp_dbm']),
                    "sinr_db": float(row['rsrq_db'])  # Column is actually SINR
                })
    return samples


def load_xapp_results(json_path: str) -> List[Dict]:
    """Load xApp integration results."""
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data.get("xapp_decisions", [])


# =============================================================================
# Energy Analysis
# =============================================================================

def analyze_algorithm_energy(
    samples: List[Dict],
    algorithm_name: str,
    prb_func: callable
) -> Tuple[AlgorithmEnergyResults, List[EnergyMetrics]]:
    """Perform energy analysis for a single algorithm."""

    detailed_metrics = []

    total_prb_energy = 0.0
    total_enb_energy = 0.0
    total_tx_energy = 0.0
    total_throughput = 0.0

    tx_powers_dbm = []
    tx_powers_w = []
    prb_allocations = []
    rsrps = []
    sinrs = []
    throughputs = []
    battery_drains = []

    for sample in samples:
        rsrp = sample["rsrp_dbm"]
        sinr = sample["sinr_db"]

        # Calculate PRB allocation
        prb = prb_func(rsrp, sinr)

        # Calculate UE transmit power (considering PRB allocation and channel quality)
        tx_power_dbm = calculate_ue_tx_power_with_prb(rsrp, prb, sinr)
        tx_power_w = dbm_to_watts(tx_power_dbm)

        # Calculate energy components
        prb_energy = calculate_prb_energy(prb)
        enb_energy = calculate_enb_energy(prb)
        tx_energy = tx_power_w * SAMPLE_INTERVAL_S

        # Calculate throughput
        throughput = calculate_throughput(sinr, prb)

        # Calculate battery drain
        battery_drain = calculate_battery_drain_rate(tx_power_w)

        # Calculate energy efficiency (bits per Joule)
        total_energy = prb_energy + tx_energy
        bits_transferred = throughput * 1e6 * SAMPLE_INTERVAL_S
        if total_energy > 0:
            energy_efficiency = bits_transferred / total_energy
        else:
            energy_efficiency = 0

        # Store detailed metrics
        metric = EnergyMetrics(
            time=sample["time"],
            cell_id=sample["cell_id"],
            rsrp_dbm=rsrp,
            sinr_db=sinr,
            prb_allocation=prb,
            ue_tx_power_dbm=tx_power_dbm,
            ue_tx_power_w=tx_power_w,
            prb_energy_j=prb_energy,
            enb_energy_j=enb_energy,
            total_energy_j=total_energy,
            throughput_mbps=throughput,
            energy_efficiency_bits_per_j=energy_efficiency,
            battery_drain_w=battery_drain
        )
        detailed_metrics.append(metric)

        # Accumulate totals
        total_prb_energy += prb_energy
        total_enb_energy += enb_energy
        total_tx_energy += tx_energy
        total_throughput += throughput * SAMPLE_INTERVAL_S

        # Store for statistics
        tx_powers_dbm.append(tx_power_dbm)
        tx_powers_w.append(tx_power_w)
        prb_allocations.append(prb)
        rsrps.append(rsrp)
        sinrs.append(sinr)
        throughputs.append(throughput)
        battery_drains.append(battery_drain)

    # Calculate summary metrics
    n_samples = len(samples)
    sim_duration = n_samples * SAMPLE_INTERVAL_S

    total_system_energy = total_prb_energy + total_tx_energy + total_enb_energy

    # Energy efficiency
    total_bits = total_throughput * 1e6
    if total_prb_energy + total_tx_energy > 0:
        energy_efficiency_bpj = total_bits / (total_prb_energy + total_tx_energy)
    else:
        energy_efficiency_bpj = 0

    # Battery impact
    avg_battery_drain = statistics.mean(battery_drains) if battery_drains else 0
    # Baseline battery drain (flight only)
    baseline_battery_drain = UAV_FLIGHT_POWER_W + UAV_COMMS_BASE_POWER_W + dbm_to_watts(UAV_MAX_TX_POWER_DBM)

    # Estimate battery percentage used
    total_battery_energy_j = UAV_BATTERY_CAPACITY_WH * 3600  # Convert Wh to J
    battery_used_j = sum(battery_drains) * SAMPLE_INTERVAL_S
    battery_drain_percent = (battery_used_j / total_battery_energy_j) * 100

    # Flight time extension compared to max power
    if avg_battery_drain > 0:
        flight_time_extension = ((baseline_battery_drain - avg_battery_drain) / baseline_battery_drain) * 100
    else:
        flight_time_extension = 0

    results = AlgorithmEnergyResults(
        name=algorithm_name,
        total_samples=n_samples,
        simulation_duration_s=sim_duration,
        total_prb_energy_j=total_prb_energy,
        avg_prb_energy_per_sample_j=total_prb_energy / n_samples if n_samples > 0 else 0,
        avg_prb_allocation=statistics.mean(prb_allocations) if prb_allocations else 0,
        total_throughput_mb=total_throughput,
        avg_throughput_mbps=statistics.mean(throughputs) if throughputs else 0,
        energy_efficiency_bits_per_j=energy_efficiency_bpj,
        energy_efficiency_mb_per_j=total_throughput / (total_prb_energy + total_tx_energy) if (total_prb_energy + total_tx_energy) > 0 else 0,
        avg_tx_power_dbm=statistics.mean(tx_powers_dbm) if tx_powers_dbm else 0,
        avg_tx_power_w=statistics.mean(tx_powers_w) if tx_powers_w else 0,
        total_tx_energy_j=total_tx_energy,
        estimated_battery_drain_percent=battery_drain_percent,
        estimated_flight_time_extension_percent=flight_time_extension,
        total_enb_energy_j=total_enb_energy,
        avg_enb_power_w=total_enb_energy / sim_duration if sim_duration > 0 else 0,
        total_system_energy_j=total_system_energy,
        avg_rsrp_dbm=statistics.mean(rsrps) if rsrps else 0,
        avg_sinr_db=statistics.mean(sinrs) if sinrs else 0
    )

    return results, detailed_metrics


def run_energy_analysis(samples: List[Dict]) -> Dict[str, AlgorithmEnergyResults]:
    """Run energy analysis for all algorithms."""
    results = {}

    for algo_name, prb_func in ALGORITHMS.items():
        algo_results, _ = analyze_algorithm_energy(samples, algo_name, prb_func)
        results[algo_name] = algo_results
        print(f"  {algo_name}: {algo_results.energy_efficiency_bits_per_j/1e6:.2f} Mbits/J, "
              f"{algo_results.avg_prb_allocation:.1f} avg PRB")

    return results


# =============================================================================
# Visualization
# =============================================================================

def generate_energy_charts(
    results: Dict[str, AlgorithmEnergyResults],
    samples: List[Dict],
    output_dir: Path
):
    """Generate energy analysis charts."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("Warning: matplotlib not available, skipping chart generation")
        return

    algo_names = list(results.keys())
    n_algos = len(algo_names)

    # Color palette
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

    # Figure 1: Energy Efficiency Comparison Bar Chart
    fig1, ax1 = plt.subplots(figsize=(10, 6))

    efficiencies = [results[name].energy_efficiency_bits_per_j / 1e6 for name in algo_names]
    x = np.arange(n_algos)
    bars = ax1.bar(x, efficiencies, color=colors[:n_algos], edgecolor='black', linewidth=1.2)

    ax1.set_xlabel('Algorithm', fontsize=12)
    ax1.set_ylabel('Energy Efficiency (Mbits/Joule)', fontsize=12)
    ax1.set_title('Energy Efficiency Comparison by Algorithm', fontsize=14, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(algo_names, rotation=20, ha='right')
    ax1.grid(axis='y', alpha=0.3)

    # Add value labels
    for bar, val in zip(bars, efficiencies):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{val:.1f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Highlight best
    best_idx = efficiencies.index(max(efficiencies))
    bars[best_idx].set_edgecolor('gold')
    bars[best_idx].set_linewidth(3)

    plt.tight_layout()
    chart1_path = output_dir / "energy_efficiency_comparison.png"
    plt.savefig(chart1_path, dpi=150, bbox_inches='tight')
    plt.savefig(output_dir / "energy_efficiency_comparison.pdf", bbox_inches='tight')
    plt.close()
    print(f"  Saved: {chart1_path}")

    # Figure 2: Energy vs Throughput Trade-off Curve
    fig2, ax2 = plt.subplots(figsize=(10, 6))

    for i, name in enumerate(algo_names):
        r = results[name]
        # Plot point
        ax2.scatter(r.total_prb_energy_j + r.total_tx_energy_j, r.total_throughput_mb,
                   s=200, c=colors[i], marker='o', label=name, edgecolors='black', linewidths=1.5)

    ax2.set_xlabel('Total Energy Consumption (Joules)', fontsize=12)
    ax2.set_ylabel('Total Throughput (MB)', fontsize=12)
    ax2.set_title('Energy vs Throughput Trade-off', fontsize=14, fontweight='bold')
    ax2.legend(loc='best', fontsize=10)
    ax2.grid(True, alpha=0.3)

    # Add efficiency iso-lines
    energy_range = np.linspace(ax2.get_xlim()[0], ax2.get_xlim()[1], 100)
    for eff in [5, 10, 15, 20]:  # MB/J efficiency lines
        throughput_line = energy_range * eff
        valid = throughput_line <= ax2.get_ylim()[1] * 1.2
        ax2.plot(energy_range[valid], throughput_line[valid], '--', alpha=0.3, color='gray')
        if valid.any():
            ax2.annotate(f'{eff} MB/J', xy=(energy_range[valid][-1], throughput_line[valid][-1]),
                        fontsize=8, alpha=0.5)

    plt.tight_layout()
    chart2_path = output_dir / "energy_throughput_tradeoff.png"
    plt.savefig(chart2_path, dpi=150, bbox_inches='tight')
    plt.savefig(output_dir / "energy_throughput_tradeoff.pdf", bbox_inches='tight')
    plt.close()
    print(f"  Saved: {chart2_path}")

    # Figure 3: Energy Breakdown Stacked Bar
    fig3, ax3 = plt.subplots(figsize=(10, 6))

    prb_energy = [results[name].total_prb_energy_j for name in algo_names]
    tx_energy = [results[name].total_tx_energy_j for name in algo_names]

    width = 0.6
    ax3.bar(x, prb_energy, width, label='PRB Energy', color='steelblue')
    ax3.bar(x, tx_energy, width, bottom=prb_energy, label='Tx Energy', color='coral')

    ax3.set_xlabel('Algorithm', fontsize=12)
    ax3.set_ylabel('Energy (Joules)', fontsize=12)
    ax3.set_title('Energy Consumption Breakdown', fontsize=14, fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(algo_names, rotation=20, ha='right')
    ax3.legend()
    ax3.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    chart3_path = output_dir / "energy_breakdown.png"
    plt.savefig(chart3_path, dpi=150, bbox_inches='tight')
    plt.savefig(output_dir / "energy_breakdown.pdf", bbox_inches='tight')
    plt.close()
    print(f"  Saved: {chart3_path}")

    # Figure 4: Battery Impact and Flight Time Extension
    fig4, (ax4a, ax4b) = plt.subplots(1, 2, figsize=(14, 5))

    # 4a: Battery drain rate
    drain_rates = [results[name].estimated_battery_drain_percent for name in algo_names]
    bars = ax4a.bar(x, drain_rates, color=colors[:n_algos])
    ax4a.set_xlabel('Algorithm', fontsize=12)
    ax4a.set_ylabel('Battery Usage (%)', fontsize=12)
    ax4a.set_title(f'Estimated Battery Usage\n({DEFAULT_SIM_DURATION_S}s simulation)', fontsize=12, fontweight='bold')
    ax4a.set_xticks(x)
    ax4a.set_xticklabels([n.split()[0] for n in algo_names], rotation=20, ha='right')
    ax4a.grid(axis='y', alpha=0.3)

    # 4b: Flight time extension
    extensions = [results[name].estimated_flight_time_extension_percent for name in algo_names]
    bars = ax4b.bar(x, extensions, color=colors[:n_algos])
    ax4b.set_xlabel('Algorithm', fontsize=12)
    ax4b.set_ylabel('Flight Time Extension (%)', fontsize=12)
    ax4b.set_title('Potential Flight Time Extension\n(vs Max Power)', fontsize=12, fontweight='bold')
    ax4b.set_xticks(x)
    ax4b.set_xticklabels([n.split()[0] for n in algo_names], rotation=20, ha='right')
    ax4b.grid(axis='y', alpha=0.3)
    ax4b.axhline(y=0, color='r', linestyle='--', alpha=0.5)

    plt.tight_layout()
    chart4_path = output_dir / "battery_impact.png"
    plt.savefig(chart4_path, dpi=150, bbox_inches='tight')
    plt.savefig(output_dir / "battery_impact.pdf", bbox_inches='tight')
    plt.close()
    print(f"  Saved: {chart4_path}")

    # Figure 5: eNB Energy Comparison
    fig5, ax5 = plt.subplots(figsize=(10, 6))

    enb_energy = [results[name].total_enb_energy_j for name in algo_names]
    bars = ax5.bar(x, enb_energy, color=colors[:n_algos])
    ax5.set_xlabel('Algorithm', fontsize=12)
    ax5.set_ylabel('eNB Energy (Joules)', fontsize=12)
    ax5.set_title('Network (eNB) Energy Consumption', fontsize=14, fontweight='bold')
    ax5.set_xticks(x)
    ax5.set_xticklabels(algo_names, rotation=20, ha='right')
    ax5.grid(axis='y', alpha=0.3)

    # Add percentage labels relative to baseline
    baseline_enb = results["Baseline (Fixed)"].total_enb_energy_j
    for bar, val in zip(bars, enb_energy):
        pct_diff = ((val - baseline_enb) / baseline_enb) * 100
        label = f'{pct_diff:+.1f}%'
        ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10,
                label, ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    chart5_path = output_dir / "enb_energy_comparison.png"
    plt.savefig(chart5_path, dpi=150, bbox_inches='tight')
    plt.savefig(output_dir / "enb_energy_comparison.pdf", bbox_inches='tight')
    plt.close()
    print(f"  Saved: {chart5_path}")


# =============================================================================
# LaTeX Table Generation
# =============================================================================

def generate_latex_table(results: Dict[str, AlgorithmEnergyResults], output_dir: Path) -> str:
    """Generate LaTeX table with energy metrics."""

    lines = []
    lines.append(r"\begin{table}[htbp]")
    lines.append(r"\centering")
    lines.append(r"\caption{Energy Efficiency Analysis Results}")
    lines.append(r"\label{tab:energy_analysis}")
    lines.append(r"\begin{tabular}{l|c|c|c|c|c}")
    lines.append(r"\hline")
    lines.append(r"\textbf{Metric} & \textbf{Baseline} & \textbf{xApp} & \textbf{Greedy} & \textbf{Conservative} & \textbf{Energy-Opt} \\")
    lines.append(r"\hline")

    # Define metrics to include
    metrics = [
        ("Avg PRB Allocation", "avg_prb_allocation", ".1f", ""),
        ("Total PRB Energy (J)", "total_prb_energy_j", ".1f", ""),
        ("Avg Throughput (Mbps)", "avg_throughput_mbps", ".2f", ""),
        ("Energy Efficiency (Mbits/J)", "energy_efficiency_bits_per_j", ".2f", "1e-6"),
        ("Avg Tx Power (dBm)", "avg_tx_power_dbm", ".1f", ""),
        ("Total Tx Energy (J)", "total_tx_energy_j", ".2f", ""),
        ("eNB Energy (J)", "total_enb_energy_j", ".1f", ""),
        ("Battery Usage (\\%)", "estimated_battery_drain_percent", ".3f", ""),
        ("Flight Extension (\\%)", "estimated_flight_time_extension_percent", ".2f", ""),
    ]

    algo_order = ["Baseline (Fixed)", "xApp (Adaptive)", "Greedy", "Conservative", "Energy-Optimal"]

    for label, attr, fmt, scale in metrics:
        row = f"{label}"
        for algo in algo_order:
            val = getattr(results[algo], attr)
            if scale == "1e-6":
                val = val / 1e6
            row += f" & {val:{fmt}}"
        row += r" \\"
        lines.append(row)

    lines.append(r"\hline")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")

    latex_content = "\n".join(lines)

    # Save to file
    latex_path = output_dir / "energy_metrics_table.tex"
    with open(latex_path, 'w') as f:
        f.write(latex_content)
    print(f"  Saved LaTeX table: {latex_path}")

    return latex_content


# =============================================================================
# Report Generation
# =============================================================================

def generate_text_report(results: Dict[str, AlgorithmEnergyResults]) -> str:
    """Generate text report of energy analysis."""
    lines = []
    lines.append("=" * 100)
    lines.append("ENERGY EFFICIENCY ANALYSIS REPORT - UAV xApp")
    lines.append("=" * 100)
    lines.append("")

    # Configuration
    lines.append("ANALYSIS CONFIGURATION:")
    lines.append("-" * 50)
    lines.append(f"  PRB Power:             {PRB_POWER_W} W per PRB")
    lines.append(f"  eNB Power per PRB:     {ENB_POWER_PER_PRB_W} W")
    lines.append(f"  eNB Static Power:      {ENB_STATIC_POWER_W} W")
    lines.append(f"  UAV Max Tx Power:      {UAV_MAX_TX_POWER_DBM} dBm")
    lines.append(f"  UAV Battery Capacity:  {UAV_BATTERY_CAPACITY_WH} Wh")
    lines.append(f"  UAV Flight Power:      {UAV_FLIGHT_POWER_W} W")
    lines.append("")

    # Summary Table
    lines.append("ENERGY METRICS COMPARISON:")
    lines.append("-" * 100)

    header = f"{'Algorithm':<20} {'Avg PRB':>10} {'Throughput':>12} {'PRB Energy':>12} {'Efficiency':>14} {'Battery':>10}"
    lines.append(header)
    lines.append(f"{'':20} {'':>10} {'(Mbps)':>12} {'(J)':>12} {'(Mbits/J)':>14} {'Usage (%)':>10}")
    lines.append("-" * 100)

    for name, r in results.items():
        row = f"{name:<20} {r.avg_prb_allocation:>10.1f} {r.avg_throughput_mbps:>12.2f} "
        row += f"{r.total_prb_energy_j:>12.1f} {r.energy_efficiency_bits_per_j/1e6:>14.2f} "
        row += f"{r.estimated_battery_drain_percent:>10.3f}"
        lines.append(row)

    lines.append("")

    # Detailed Analysis per Algorithm
    lines.append("=" * 100)
    lines.append("DETAILED ENERGY BREAKDOWN:")
    lines.append("=" * 100)

    for name, r in results.items():
        lines.append("")
        lines.append(f"[ {name} ]")
        lines.append("-" * 60)
        lines.append(f"  Samples:                    {r.total_samples}")
        lines.append(f"  Simulation Duration:        {r.simulation_duration_s:.1f} s")
        lines.append("")
        lines.append("  PRB Energy Model:")
        lines.append(f"    Average PRB Allocation:   {r.avg_prb_allocation:.2f}")
        lines.append(f"    Total PRB Energy:         {r.total_prb_energy_j:.2f} J")
        lines.append(f"    Avg PRB Energy/Sample:    {r.avg_prb_energy_per_sample_j:.3f} J")
        lines.append("")
        lines.append("  UAV Battery Impact:")
        lines.append(f"    Average Tx Power:         {r.avg_tx_power_dbm:.2f} dBm ({r.avg_tx_power_w*1000:.2f} mW)")
        lines.append(f"    Total Tx Energy:          {r.total_tx_energy_j:.3f} J")
        lines.append(f"    Battery Usage:            {r.estimated_battery_drain_percent:.4f} %")
        lines.append(f"    Flight Time Extension:    {r.estimated_flight_time_extension_percent:+.2f} %")
        lines.append("")
        lines.append("  Network (eNB) Energy:")
        lines.append(f"    Total eNB Energy:         {r.total_enb_energy_j:.1f} J")
        lines.append(f"    Average eNB Power:        {r.avg_enb_power_w:.1f} W")
        lines.append("")
        lines.append("  Throughput Performance:")
        lines.append(f"    Total Throughput:         {r.total_throughput_mb:.2f} MB")
        lines.append(f"    Average Throughput:       {r.avg_throughput_mbps:.2f} Mbps")
        lines.append("")
        lines.append("  Energy Efficiency:")
        lines.append(f"    Efficiency (bits/J):      {r.energy_efficiency_bits_per_j:.0f}")
        lines.append(f"    Efficiency (Mbits/J):     {r.energy_efficiency_bits_per_j/1e6:.2f}")
        lines.append(f"    Efficiency (MB/J):        {r.energy_efficiency_mb_per_j:.2f}")

    # Comparison Summary
    lines.append("")
    lines.append("=" * 100)
    lines.append("COMPARISON SUMMARY:")
    lines.append("=" * 100)

    baseline = results.get("Baseline (Fixed)")
    xapp = results.get("xApp (Adaptive)")

    if baseline and xapp:
        lines.append("")
        lines.append("xApp vs Baseline Improvements:")
        lines.append("-" * 50)

        # Energy efficiency improvement
        eff_improvement = ((xapp.energy_efficiency_bits_per_j - baseline.energy_efficiency_bits_per_j)
                          / baseline.energy_efficiency_bits_per_j) * 100
        lines.append(f"  Energy Efficiency:          {eff_improvement:+.1f}%")

        # PRB savings
        prb_savings = ((baseline.total_prb_energy_j - xapp.total_prb_energy_j)
                      / baseline.total_prb_energy_j) * 100
        lines.append(f"  PRB Energy Savings:         {prb_savings:+.1f}%")

        # Battery improvement
        battery_improvement = baseline.estimated_battery_drain_percent - xapp.estimated_battery_drain_percent
        lines.append(f"  Battery Usage Reduction:    {battery_improvement:+.4f} percentage points")

        # eNB energy savings
        enb_savings = ((baseline.total_enb_energy_j - xapp.total_enb_energy_j)
                      / baseline.total_enb_energy_j) * 100
        lines.append(f"  Network Energy Savings:     {enb_savings:+.1f}%")

        # Throughput comparison
        tput_diff = ((xapp.avg_throughput_mbps - baseline.avg_throughput_mbps)
                    / baseline.avg_throughput_mbps) * 100
        lines.append(f"  Throughput Change:          {tput_diff:+.1f}%")

    # Best algorithm rankings
    lines.append("")
    lines.append("Best Performing Algorithms:")
    lines.append("-" * 50)

    # Highest efficiency
    best_eff = max(results.items(), key=lambda x: x[1].energy_efficiency_bits_per_j)
    lines.append(f"  Highest Energy Efficiency:  {best_eff[0]} ({best_eff[1].energy_efficiency_bits_per_j/1e6:.2f} Mbits/J)")

    # Lowest energy
    best_energy = min(results.items(), key=lambda x: x[1].total_prb_energy_j)
    lines.append(f"  Lowest PRB Energy:          {best_energy[0]} ({best_energy[1].total_prb_energy_j:.1f} J)")

    # Best battery life
    best_battery = min(results.items(), key=lambda x: x[1].estimated_battery_drain_percent)
    lines.append(f"  Best Battery Life:          {best_battery[0]} ({best_battery[1].estimated_battery_drain_percent:.4f}%)")

    lines.append("")
    lines.append("=" * 100)
    lines.append(f"Generated: {datetime.now().isoformat()}")

    return "\n".join(lines)


# =============================================================================
# Output Saving
# =============================================================================

def save_results(
    output_dir: Path,
    results: Dict[str, AlgorithmEnergyResults],
    report: str,
    latex: str
):
    """Save all analysis results."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save JSON results
    json_data = {
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "prb_power_w": PRB_POWER_W,
            "enb_power_per_prb_w": ENB_POWER_PER_PRB_W,
            "enb_static_power_w": ENB_STATIC_POWER_W,
            "uav_max_tx_power_dbm": UAV_MAX_TX_POWER_DBM,
            "uav_battery_capacity_wh": UAV_BATTERY_CAPACITY_WH,
            "uav_flight_power_w": UAV_FLIGHT_POWER_W,
            "prb_bandwidth_hz": PRB_BANDWIDTH_HZ,
        },
        "algorithms": {name: asdict(r) for name, r in results.items()},
        "summary": {
            "best_energy_efficiency": max(results.items(), key=lambda x: x[1].energy_efficiency_bits_per_j)[0],
            "lowest_energy": min(results.items(), key=lambda x: x[1].total_prb_energy_j)[0],
            "best_battery_life": min(results.items(), key=lambda x: x[1].estimated_battery_drain_percent)[0],
        }
    }

    json_path = output_dir / f"energy_analysis_{timestamp}.json"
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    print(f"  Saved JSON: {json_path}")

    # Save latest version
    latest_json = output_dir / "energy_analysis_latest.json"
    with open(latest_json, 'w') as f:
        json.dump(json_data, f, indent=2)

    # Save text report
    txt_path = output_dir / f"energy_report_{timestamp}.txt"
    with open(txt_path, 'w') as f:
        f.write(report)
    print(f"  Saved report: {txt_path}")

    # Save CSV summary
    csv_path = output_dir / f"energy_summary_{timestamp}.csv"
    with open(csv_path, 'w', newline='') as f:
        import csv
        writer = csv.writer(f)
        header = ["Algorithm", "Avg_PRB", "Throughput_Mbps", "PRB_Energy_J", "Tx_Energy_J",
                 "eNB_Energy_J", "Efficiency_Mbits_per_J", "Battery_Usage_Pct", "Flight_Extension_Pct"]
        writer.writerow(header)
        for name, r in results.items():
            writer.writerow([
                name,
                f"{r.avg_prb_allocation:.2f}",
                f"{r.avg_throughput_mbps:.2f}",
                f"{r.total_prb_energy_j:.2f}",
                f"{r.total_tx_energy_j:.4f}",
                f"{r.total_enb_energy_j:.2f}",
                f"{r.energy_efficiency_bits_per_j/1e6:.2f}",
                f"{r.estimated_battery_drain_percent:.4f}",
                f"{r.estimated_flight_time_extension_percent:.2f}"
            ])
    print(f"  Saved CSV: {csv_path}")

    return json_path, txt_path, csv_path


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Energy Efficiency Analysis for UAV xApp",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Energy Model Assumptions:
  - PRB power: 0.5W per PRB (user allocation)
  - eNB power: 1W per PRB + 50W static
  - UAV Tx power: up to 23 dBm (LTE Class 3)
  - UAV battery: 100 Wh capacity

Example:
  python energy_analysis.py --csv /tmp/ns3-uav-full.csv
        """
    )

    parser.add_argument("--csv", default="/tmp/ns3-uav-full.csv",
                       help="Path to ns-3 CSV output file")
    parser.add_argument("--xapp-results", default="results/ns3-lte/ns3_xapp_full_integration.json",
                       help="Path to xApp integration results")
    parser.add_argument("--output-dir", default="results/energy",
                       help="Output directory for results")
    parser.add_argument("--no-charts", action="store_true",
                       help="Skip chart generation")
    parser.add_argument("--interval", type=float, default=1.0,
                       help="Sample interval in seconds")

    args = parser.parse_args()

    # Resolve paths
    base_dir = Path(__file__).parent
    csv_path = Path(args.csv)
    output_dir = base_dir / args.output_dir if not Path(args.output_dir).is_absolute() else Path(args.output_dir)

    print("=" * 80)
    print("ENERGY EFFICIENCY ANALYSIS - UAV xApp")
    print("=" * 80)
    print(f"CSV Data:    {csv_path}")
    print(f"Output Dir:  {output_dir}")
    print("=" * 80)

    # Print configuration
    print("\nEnergy Model Configuration:")
    print(f"  PRB Power:           {PRB_POWER_W} W per PRB")
    print(f"  eNB Power per PRB:   {ENB_POWER_PER_PRB_W} W")
    print(f"  UAV Max Tx Power:    {UAV_MAX_TX_POWER_DBM} dBm")
    print(f"  UAV Battery:         {UAV_BATTERY_CAPACITY_WH} Wh")
    print()

    # Load data
    print("Loading simulation data...")
    try:
        samples = load_csv_data(str(csv_path), args.interval)
        print(f"  Loaded {len(samples)} samples")
    except FileNotFoundError:
        print(f"Error: CSV file not found: {csv_path}")
        print("Please ensure the ns-3 simulation data exists.")
        return 1

    if not samples:
        print("Error: No samples loaded")
        return 1

    # Print data statistics
    rsrps = [s["rsrp_dbm"] for s in samples]
    sinrs = [s["sinr_db"] for s in samples]
    print(f"  RSRP range: {min(rsrps):.1f} to {max(rsrps):.1f} dBm")
    print(f"  SINR range: {min(sinrs):.1f} to {max(sinrs):.1f} dB")

    # Run energy analysis
    print("\nRunning energy analysis for all algorithms...")
    results = run_energy_analysis(samples)

    # Generate reports
    print("\nGenerating reports...")
    report = generate_text_report(results)

    # Print report
    print("\n")
    print(report)

    # Generate charts
    if not args.no_charts:
        print("\nGenerating charts...")
        output_dir.mkdir(parents=True, exist_ok=True)
        generate_energy_charts(results, samples, output_dir)

    # Generate LaTeX table
    print("\nGenerating LaTeX table...")
    output_dir.mkdir(parents=True, exist_ok=True)
    latex = generate_latex_table(results, output_dir)

    # Save results
    print("\nSaving results...")
    save_results(output_dir, results, report, latex)

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"Results saved to: {output_dir}")

    return 0


if __name__ == "__main__":
    exit(main())
