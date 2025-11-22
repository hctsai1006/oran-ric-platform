#!/usr/bin/env python3
"""
Algorithm Comparison Test Script

Compares multiple handover and resource allocation algorithms:
1. Rule-based (Current xApp) - RSRP threshold handover, adaptive PRB
2. Random Baseline - Random decisions for baseline comparison
3. Greedy Algorithm - Always select strongest signal, proportional PRB
4. Conservative Algorithm - Delayed handover, conservative PRB allocation

Uses existing CSV data from ns-3 simulation.
"""

import csv
import json
import math
import random
import statistics
import argparse
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_CSV_PATH = "/tmp/ns3-uav-full.csv"
DEFAULT_OUTPUT_DIR = "results/algorithms"

# System parameters
TOTAL_PRB = 100
PRB_BANDWIDTH_HZ = 180e3  # 180 kHz per PRB (LTE)
HANDOVER_DELAY_MS = 50    # Average handover delay

# Thresholds
RSRP_HANDOVER_THRESHOLD = -110  # dBm, trigger handover consideration
RSRP_CRITICAL_THRESHOLD = -120  # dBm, service degradation
HYSTERESIS_DB = 3.0             # Handover hysteresis

# Random seed for reproducibility
RANDOM_SEED = 42


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class MeasurementSample:
    """Single measurement sample from ns-3 simulation."""
    time: float
    cell_id: int
    rsrp_dbm: float
    sinr_db: float  # rsrq_db column is actually SINR


@dataclass
class AlgorithmDecision:
    """Decision made by an algorithm at a time step."""
    time: float
    current_cell: int
    target_cell: int
    prb_allocation: int
    handover_triggered: bool
    reason: str


@dataclass
class AlgorithmMetrics:
    """Performance metrics for an algorithm."""
    name: str
    total_samples: int = 0

    # Throughput metrics
    avg_throughput_mbps: float = 0.0
    min_throughput_mbps: float = 0.0
    max_throughput_mbps: float = 0.0
    std_throughput_mbps: float = 0.0
    throughput_5th_percentile: float = 0.0
    throughput_95th_percentile: float = 0.0

    # PRB metrics
    avg_prb: float = 0.0
    total_prb_used: int = 0
    prb_efficiency: float = 0.0  # Throughput per PRB

    # Handover metrics
    handover_count: int = 0
    total_handover_delay_ms: int = 0
    ping_pong_count: int = 0  # Rapid back-and-forth handovers

    # Signal quality metrics
    avg_rsrp: float = 0.0
    avg_sinr: float = 0.0
    samples_below_threshold: int = 0
    samples_critical: int = 0

    # QoS metrics
    service_continuity: float = 0.0  # Percentage of time with acceptable service
    fairness_index: float = 0.0      # Jain's fairness index for throughput


# =============================================================================
# Base Algorithm Class
# =============================================================================

class BaseAlgorithm(ABC):
    """Abstract base class for handover/resource allocation algorithms."""

    def __init__(self, name: str):
        self.name = name
        self.decisions: List[AlgorithmDecision] = []
        self.current_serving_cell: Optional[int] = None
        self.handover_count = 0
        self.ping_pong_count = 0
        self.handover_history: List[Tuple[float, int, int]] = []  # (time, from, to)

    @abstractmethod
    def decide(self, sample: MeasurementSample,
               neighbor_samples: Dict[int, MeasurementSample]) -> AlgorithmDecision:
        """Make handover and PRB allocation decision."""
        pass

    def _calculate_throughput(self, sinr_db: float, prb: int) -> float:
        """Calculate throughput using Shannon capacity formula."""
        sinr_linear = 10 ** (sinr_db / 10)
        spectral_efficiency = math.log2(1 + sinr_linear)
        bandwidth_hz = prb * PRB_BANDWIDTH_HZ
        throughput_mbps = (bandwidth_hz * spectral_efficiency) / 1e6
        return throughput_mbps

    def _detect_ping_pong(self, time: float, from_cell: int, to_cell: int,
                          window_sec: float = 5.0) -> bool:
        """Detect ping-pong handover (back-and-forth within time window)."""
        for ho_time, ho_from, ho_to in reversed(self.handover_history):
            if time - ho_time > window_sec:
                break
            if ho_from == to_cell and ho_to == from_cell:
                return True
        return False

    def record_decision(self, decision: AlgorithmDecision):
        """Record a decision and update handover statistics."""
        if decision.handover_triggered:
            self.handover_count += 1
            if self.current_serving_cell is not None:
                if self._detect_ping_pong(decision.time,
                                          self.current_serving_cell,
                                          decision.target_cell):
                    self.ping_pong_count += 1
                self.handover_history.append(
                    (decision.time, self.current_serving_cell, decision.target_cell)
                )
            self.current_serving_cell = decision.target_cell
        elif self.current_serving_cell is None:
            self.current_serving_cell = decision.current_cell

        self.decisions.append(decision)

    def calculate_metrics(self, samples: List[MeasurementSample]) -> AlgorithmMetrics:
        """Calculate performance metrics from decisions."""
        if not self.decisions:
            return AlgorithmMetrics(name=self.name)

        throughputs = []
        prbs = []
        rsrps = []
        sinrs = []
        service_ok_count = 0

        for decision, sample in zip(self.decisions, samples):
            throughput = self._calculate_throughput(sample.sinr_db, decision.prb_allocation)
            throughputs.append(throughput)
            prbs.append(decision.prb_allocation)
            rsrps.append(sample.rsrp_dbm)
            sinrs.append(sample.sinr_db)

            # Service is OK if RSRP > critical threshold
            if sample.rsrp_dbm > RSRP_CRITICAL_THRESHOLD:
                service_ok_count += 1

        # Calculate Jain's fairness index
        if throughputs:
            sum_throughput = sum(throughputs)
            sum_squared = sum(t**2 for t in throughputs)
            n = len(throughputs)
            fairness = (sum_throughput ** 2) / (n * sum_squared) if sum_squared > 0 else 0
        else:
            fairness = 0

        sorted_throughputs = sorted(throughputs)
        n = len(sorted_throughputs)

        return AlgorithmMetrics(
            name=self.name,
            total_samples=len(self.decisions),
            avg_throughput_mbps=statistics.mean(throughputs) if throughputs else 0,
            min_throughput_mbps=min(throughputs) if throughputs else 0,
            max_throughput_mbps=max(throughputs) if throughputs else 0,
            std_throughput_mbps=statistics.stdev(throughputs) if len(throughputs) > 1 else 0,
            throughput_5th_percentile=sorted_throughputs[int(n * 0.05)] if n > 20 else (min(throughputs) if throughputs else 0),
            throughput_95th_percentile=sorted_throughputs[int(n * 0.95)] if n > 20 else (max(throughputs) if throughputs else 0),
            avg_prb=statistics.mean(prbs) if prbs else 0,
            total_prb_used=sum(prbs),
            prb_efficiency=statistics.mean(throughputs) / statistics.mean(prbs) if prbs and statistics.mean(prbs) > 0 else 0,
            handover_count=self.handover_count,
            total_handover_delay_ms=self.handover_count * HANDOVER_DELAY_MS,
            ping_pong_count=self.ping_pong_count,
            avg_rsrp=statistics.mean(rsrps) if rsrps else 0,
            avg_sinr=statistics.mean(sinrs) if sinrs else 0,
            samples_below_threshold=sum(1 for r in rsrps if r < RSRP_HANDOVER_THRESHOLD),
            samples_critical=sum(1 for r in rsrps if r < RSRP_CRITICAL_THRESHOLD),
            service_continuity=service_ok_count / len(self.decisions) * 100 if self.decisions else 0,
            fairness_index=fairness
        )


# =============================================================================
# Algorithm Implementations
# =============================================================================

class RuleBasedAlgorithm(BaseAlgorithm):
    """
    Rule-based Algorithm (Current xApp Implementation)

    Handover Logic:
    - Trigger when RSRP < threshold AND neighbor is better by hysteresis margin

    PRB Allocation:
    - Dynamic based on SINR:
      * High SINR (>15 dB): 6-8 PRBs
      * Medium SINR (5-15 dB): 8-12 PRBs
      * Low SINR (<5 dB): 12-15 PRBs
    - Additional PRBs for cell edge (low RSRP)
    """

    def __init__(self):
        super().__init__("Rule-based (xApp)")
        self.rsrp_threshold = RSRP_HANDOVER_THRESHOLD
        self.hysteresis = HYSTERESIS_DB

    def decide(self, sample: MeasurementSample,
               neighbor_samples: Dict[int, MeasurementSample]) -> AlgorithmDecision:

        current_cell = sample.cell_id
        target_cell = current_cell
        handover = False
        reason = "Maintain connection"

        # Find best neighbor
        best_neighbor = None
        best_neighbor_rsrp = float('-inf')
        for cell_id, neighbor in neighbor_samples.items():
            if neighbor.rsrp_dbm > best_neighbor_rsrp:
                best_neighbor_rsrp = neighbor.rsrp_dbm
                best_neighbor = cell_id

        # Handover decision
        if (sample.rsrp_dbm < self.rsrp_threshold and
            best_neighbor is not None and
            best_neighbor_rsrp > sample.rsrp_dbm + self.hysteresis):
            target_cell = best_neighbor
            handover = True
            reason = f"RSRP={sample.rsrp_dbm:.1f}dBm < threshold, neighbor {best_neighbor} is {best_neighbor_rsrp - sample.rsrp_dbm:.1f}dB better"

        # PRB allocation based on SINR and RSRP
        sinr = sample.sinr_db
        rsrp = sample.rsrp_dbm

        if sinr > 15:
            base_prb = 7
        elif sinr > 10:
            base_prb = 9
        elif sinr > 5:
            base_prb = 11
        else:
            base_prb = 14

        # Cell edge compensation
        if rsrp < -118:
            base_prb += 3
        elif rsrp < -115:
            base_prb += 2
        elif rsrp < -110:
            base_prb += 1

        prb = max(5, min(20, base_prb))

        decision = AlgorithmDecision(
            time=sample.time,
            current_cell=current_cell,
            target_cell=target_cell,
            prb_allocation=prb,
            handover_triggered=handover,
            reason=reason
        )
        self.record_decision(decision)
        return decision


class RandomAlgorithm(BaseAlgorithm):
    """
    Random Baseline Algorithm

    Handover Logic:
    - Random handover decision with 5% probability per sample
    - Randomly selects a cell if handover occurs

    PRB Allocation:
    - Random PRB between 5-15
    """

    def __init__(self, seed: int = RANDOM_SEED):
        super().__init__("Random Baseline")
        self.rng = random.Random(seed)
        self.handover_probability = 0.05

    def decide(self, sample: MeasurementSample,
               neighbor_samples: Dict[int, MeasurementSample]) -> AlgorithmDecision:

        current_cell = sample.cell_id
        target_cell = current_cell
        handover = False
        reason = "Random: maintain"

        # Random handover decision
        if self.rng.random() < self.handover_probability:
            available_cells = list(neighbor_samples.keys())
            if available_cells:
                target_cell = self.rng.choice(available_cells)
                if target_cell != current_cell:
                    handover = True
                    reason = f"Random: handover to cell {target_cell}"

        # Random PRB allocation
        prb = self.rng.randint(5, 15)

        decision = AlgorithmDecision(
            time=sample.time,
            current_cell=current_cell,
            target_cell=target_cell,
            prb_allocation=prb,
            handover_triggered=handover,
            reason=reason
        )
        self.record_decision(decision)
        return decision


class GreedyAlgorithm(BaseAlgorithm):
    """
    Greedy Algorithm

    Handover Logic:
    - Always select the cell with strongest RSRP signal
    - Immediate handover without hysteresis

    PRB Allocation:
    - Proportional to SINR: better signal = more PRBs
    - PRB = 5 + (SINR_normalized * 15)
    """

    def __init__(self):
        super().__init__("Greedy")

    def decide(self, sample: MeasurementSample,
               neighbor_samples: Dict[int, MeasurementSample]) -> AlgorithmDecision:

        current_cell = sample.cell_id

        # Find best cell (including current)
        best_cell = current_cell
        best_rsrp = sample.rsrp_dbm

        for cell_id, neighbor in neighbor_samples.items():
            if neighbor.rsrp_dbm > best_rsrp:
                best_rsrp = neighbor.rsrp_dbm
                best_cell = cell_id

        target_cell = best_cell
        handover = (target_cell != current_cell)
        reason = f"Greedy: best RSRP={best_rsrp:.1f}dBm at cell {best_cell}"

        # PRB proportional to SINR
        # Normalize SINR: assume range -5 to 25 dB
        sinr_normalized = (sample.sinr_db + 5) / 30
        sinr_normalized = max(0, min(1, sinr_normalized))
        prb = int(5 + sinr_normalized * 15)
        prb = max(5, min(20, prb))

        decision = AlgorithmDecision(
            time=sample.time,
            current_cell=current_cell,
            target_cell=target_cell,
            prb_allocation=prb,
            handover_triggered=handover,
            reason=reason
        )
        self.record_decision(decision)
        return decision


class ConservativeAlgorithm(BaseAlgorithm):
    """
    Conservative Algorithm

    Handover Logic:
    - Requires 3 consecutive samples with low RSRP before handover
    - Larger hysteresis margin (5 dB)
    - Prioritizes connection stability

    PRB Allocation:
    - Conservative: fixed base allocation
    - Only minor adjustments for extreme conditions
    - PRB = 8 (default), +2 if SINR < 5, +2 if RSRP < -115
    """

    def __init__(self):
        super().__init__("Conservative")
        self.low_rsrp_counter = 0
        self.consecutive_threshold = 3
        self.hysteresis = 5.0  # Larger hysteresis

    def decide(self, sample: MeasurementSample,
               neighbor_samples: Dict[int, MeasurementSample]) -> AlgorithmDecision:

        current_cell = sample.cell_id
        target_cell = current_cell
        handover = False
        reason = "Conservative: maintain stability"

        # Count consecutive low RSRP samples
        if sample.rsrp_dbm < RSRP_HANDOVER_THRESHOLD:
            self.low_rsrp_counter += 1
        else:
            self.low_rsrp_counter = 0

        # Only handover after consecutive low RSRP samples
        if self.low_rsrp_counter >= self.consecutive_threshold:
            # Find best neighbor with larger hysteresis
            best_neighbor = None
            best_neighbor_rsrp = float('-inf')
            for cell_id, neighbor in neighbor_samples.items():
                if neighbor.rsrp_dbm > best_neighbor_rsrp:
                    best_neighbor_rsrp = neighbor.rsrp_dbm
                    best_neighbor = cell_id

            if (best_neighbor is not None and
                best_neighbor_rsrp > sample.rsrp_dbm + self.hysteresis):
                target_cell = best_neighbor
                handover = True
                self.low_rsrp_counter = 0
                reason = f"Conservative: {self.consecutive_threshold} consecutive low RSRP, handover to {best_neighbor}"

        # Conservative PRB allocation
        prb = 8  # Base allocation

        if sample.sinr_db < 5:
            prb += 2
        if sample.rsrp_dbm < -115:
            prb += 2

        prb = max(5, min(15, prb))  # More conservative max

        decision = AlgorithmDecision(
            time=sample.time,
            current_cell=current_cell,
            target_cell=target_cell,
            prb_allocation=prb,
            handover_triggered=handover,
            reason=reason
        )
        self.record_decision(decision)
        return decision


# =============================================================================
# Data Loading and Processing
# =============================================================================

def load_csv_data(csv_path: str, sample_interval: float = 1.0) -> List[MeasurementSample]:
    """Load measurement data from CSV file."""
    samples = []
    last_time = -sample_interval

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sim_time = float(row['time'])
            if sim_time - last_time >= sample_interval:
                last_time = sim_time
                samples.append(MeasurementSample(
                    time=sim_time,
                    cell_id=int(row['cell_id']),
                    rsrp_dbm=float(row['rsrp_dbm']),
                    sinr_db=float(row['rsrq_db'])  # Column is actually SINR
                ))
    return samples


def generate_neighbor_data(sample: MeasurementSample,
                           all_cells: List[int],
                           rsrp_variation: float = 5.0,
                           seed: int = None) -> Dict[int, MeasurementSample]:
    """
    Generate simulated neighbor cell measurements.

    In real systems, UE would report measurements from multiple cells.
    Here we simulate neighbor measurements based on the current serving cell.
    """
    rng = random.Random(seed) if seed else random.Random()
    neighbors = {}

    for cell_id in all_cells:
        if cell_id == sample.cell_id:
            continue

        # Simulate neighbor RSRP: generally worse than serving with variation
        rsrp_offset = rng.gauss(-3, rsrp_variation)  # Generally worse
        neighbor_rsrp = sample.rsrp_dbm + rsrp_offset

        # SINR correlation with RSRP
        sinr_offset = rng.gauss(0, 2)
        neighbor_sinr = sample.sinr_db + sinr_offset * (rsrp_offset / rsrp_variation)

        neighbors[cell_id] = MeasurementSample(
            time=sample.time,
            cell_id=cell_id,
            rsrp_dbm=neighbor_rsrp,
            sinr_db=neighbor_sinr
        )

    return neighbors


# =============================================================================
# Comparison and Analysis
# =============================================================================

def run_comparison(samples: List[MeasurementSample],
                   all_cells: List[int],
                   seed: int = RANDOM_SEED) -> Dict[str, AlgorithmMetrics]:
    """Run all algorithms and collect metrics."""

    algorithms = [
        RuleBasedAlgorithm(),
        RandomAlgorithm(seed=seed),
        GreedyAlgorithm(),
        ConservativeAlgorithm()
    ]

    print(f"\nRunning {len(algorithms)} algorithms on {len(samples)} samples...")

    # Process each sample through all algorithms
    for i, sample in enumerate(samples):
        # Generate neighbor data (deterministic based on sample index)
        neighbors = generate_neighbor_data(sample, all_cells, seed=seed + i)

        for algo in algorithms:
            algo.decide(sample, neighbors)

        if (i + 1) % 20 == 0:
            print(f"  Processed {i + 1}/{len(samples)} samples")

    # Calculate metrics for each algorithm
    results = {}
    for algo in algorithms:
        metrics = algo.calculate_metrics(samples)
        results[algo.name] = metrics
        print(f"  {algo.name}: {metrics.handover_count} handovers, "
              f"avg throughput={metrics.avg_throughput_mbps:.2f} Mbps")

    return results


def generate_comparison_table(results: Dict[str, AlgorithmMetrics]) -> str:
    """Generate formatted comparison table."""
    lines = []
    lines.append("=" * 100)
    lines.append("ALGORITHM COMPARISON RESULTS")
    lines.append("=" * 100)
    lines.append("")

    # Header
    algo_names = list(results.keys())
    header = f"{'Metric':<35}"
    for name in algo_names:
        short_name = name[:15] if len(name) > 15 else name
        header += f"{short_name:>15}"
    lines.append(header)
    lines.append("-" * 100)

    # Throughput metrics
    lines.append("")
    lines.append("[ Throughput Performance ]")

    metrics_to_show = [
        ("Avg Throughput (Mbps)", "avg_throughput_mbps", ".2f"),
        ("Min Throughput (Mbps)", "min_throughput_mbps", ".2f"),
        ("Max Throughput (Mbps)", "max_throughput_mbps", ".2f"),
        ("Std Dev (Mbps)", "std_throughput_mbps", ".2f"),
        ("5th Percentile (Mbps)", "throughput_5th_percentile", ".2f"),
        ("95th Percentile (Mbps)", "throughput_95th_percentile", ".2f"),
    ]

    for label, attr, fmt in metrics_to_show:
        row = f"{label:<35}"
        for name in algo_names:
            val = getattr(results[name], attr)
            row += f"{val:>15{fmt}}"
        lines.append(row)

    # Resource efficiency metrics
    lines.append("")
    lines.append("[ Resource Efficiency ]")

    metrics_to_show = [
        ("Avg PRB Allocation", "avg_prb", ".1f"),
        ("Total PRB Used", "total_prb_used", "d"),
        ("PRB Efficiency (Mbps/PRB)", "prb_efficiency", ".3f"),
    ]

    for label, attr, fmt in metrics_to_show:
        row = f"{label:<35}"
        for name in algo_names:
            val = getattr(results[name], attr)
            row += f"{val:>15{fmt}}"
        lines.append(row)

    # Handover metrics
    lines.append("")
    lines.append("[ Handover Performance ]")

    metrics_to_show = [
        ("Handover Count", "handover_count", "d"),
        ("Ping-Pong Handovers", "ping_pong_count", "d"),
        ("Total HO Delay (ms)", "total_handover_delay_ms", "d"),
    ]

    for label, attr, fmt in metrics_to_show:
        row = f"{label:<35}"
        for name in algo_names:
            val = getattr(results[name], attr)
            row += f"{val:>15{fmt}}"
        lines.append(row)

    # Signal quality metrics
    lines.append("")
    lines.append("[ Signal Quality ]")

    metrics_to_show = [
        ("Avg RSRP (dBm)", "avg_rsrp", ".2f"),
        ("Avg SINR (dB)", "avg_sinr", ".2f"),
        ("Samples Below -110 dBm", "samples_below_threshold", "d"),
        ("Samples Critical (<-120 dBm)", "samples_critical", "d"),
    ]

    for label, attr, fmt in metrics_to_show:
        row = f"{label:<35}"
        for name in algo_names:
            val = getattr(results[name], attr)
            row += f"{val:>15{fmt}}"
        lines.append(row)

    # QoS metrics
    lines.append("")
    lines.append("[ QoS Metrics ]")

    metrics_to_show = [
        ("Service Continuity (%)", "service_continuity", ".1f"),
        ("Fairness Index", "fairness_index", ".4f"),
    ]

    for label, attr, fmt in metrics_to_show:
        row = f"{label:<35}"
        for name in algo_names:
            val = getattr(results[name], attr)
            row += f"{val:>15{fmt}}"
        lines.append(row)

    lines.append("")
    lines.append("=" * 100)

    return "\n".join(lines)


def generate_ranking_summary(results: Dict[str, AlgorithmMetrics]) -> str:
    """Generate ranking summary for each metric category."""
    lines = []
    lines.append("")
    lines.append("PERFORMANCE RANKING SUMMARY")
    lines.append("=" * 80)

    algo_names = list(results.keys())

    # Define ranking criteria (metric, higher_is_better)
    rankings = {
        "Throughput": [
            ("avg_throughput_mbps", True),
            ("min_throughput_mbps", True),
            ("throughput_5th_percentile", True),
        ],
        "Resource Efficiency": [
            ("prb_efficiency", True),
            ("avg_prb", False),  # Lower is better (fewer resources)
        ],
        "Handover Performance": [
            ("handover_count", False),  # Lower is better
            ("ping_pong_count", False),
        ],
        "QoS": [
            ("service_continuity", True),
            ("fairness_index", True),
        ],
    }

    category_winners = defaultdict(lambda: defaultdict(int))

    for category, metrics_list in rankings.items():
        lines.append(f"\n{category}:")
        lines.append("-" * 40)

        for metric, higher_is_better in metrics_list:
            values = [(name, getattr(results[name], metric)) for name in algo_names]
            sorted_values = sorted(values, key=lambda x: x[1], reverse=higher_is_better)

            winner = sorted_values[0][0]
            category_winners[category][winner] += 1

            ranking_str = " > ".join([f"{name}({val:.2f})" for name, val in sorted_values])
            metric_label = metric.replace('_', ' ').title()
            lines.append(f"  {metric_label}: {ranking_str}")

    # Overall ranking
    lines.append("")
    lines.append("OVERALL RANKING (by category wins):")
    lines.append("-" * 40)

    overall_scores = defaultdict(int)
    for category, winners in category_winners.items():
        for algo, wins in winners.items():
            overall_scores[algo] += wins

    sorted_overall = sorted(overall_scores.items(), key=lambda x: x[1], reverse=True)
    for rank, (algo, score) in enumerate(sorted_overall, 1):
        lines.append(f"  {rank}. {algo}: {score} metric wins")

    lines.append("")
    lines.append("=" * 80)

    return "\n".join(lines)


def generate_improvement_analysis(results: Dict[str, AlgorithmMetrics]) -> str:
    """Generate improvement analysis comparing xApp to baseline."""
    lines = []
    lines.append("")
    lines.append("IMPROVEMENT ANALYSIS (vs Random Baseline)")
    lines.append("=" * 80)

    baseline = results.get("Random Baseline")
    if not baseline:
        return "\nNo Random Baseline found for comparison.\n"

    metrics_to_compare = [
        ("avg_throughput_mbps", "Avg Throughput", True, "%"),
        ("min_throughput_mbps", "Min Throughput", True, "%"),
        ("prb_efficiency", "PRB Efficiency", True, "%"),
        ("handover_count", "Handover Count", False, "%"),
        ("service_continuity", "Service Continuity", True, "pp"),  # percentage points
    ]

    for algo_name, metrics in results.items():
        if algo_name == "Random Baseline":
            continue

        lines.append(f"\n{algo_name} vs Random Baseline:")
        lines.append("-" * 50)

        for attr, label, higher_is_better, unit in metrics_to_compare:
            baseline_val = getattr(baseline, attr)
            algo_val = getattr(metrics, attr)

            if unit == "pp":
                improvement = algo_val - baseline_val
                direction = "better" if improvement > 0 else "worse"
            elif baseline_val != 0:
                if higher_is_better:
                    improvement = ((algo_val - baseline_val) / abs(baseline_val)) * 100
                else:
                    improvement = ((baseline_val - algo_val) / abs(baseline_val)) * 100
                direction = "improvement" if improvement > 0 else "degradation"
            else:
                improvement = 0
                direction = "N/A"

            if unit == "pp":
                lines.append(f"  {label}: {improvement:+.1f} percentage points ({direction})")
            else:
                lines.append(f"  {label}: {improvement:+.1f}% {direction}")

    lines.append("")
    lines.append("=" * 80)

    return "\n".join(lines)


# =============================================================================
# Visualization
# =============================================================================

def generate_charts(results: Dict[str, AlgorithmMetrics], output_dir: Path):
    """Generate comparison charts using matplotlib."""
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("Warning: matplotlib not available, skipping chart generation")
        return

    algo_names = list(results.keys())
    n_algos = len(algo_names)
    x = np.arange(n_algos)
    bar_width = 0.6

    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Algorithm Performance Comparison', fontsize=14, fontweight='bold')

    # 1. Throughput comparison
    ax1 = axes[0, 0]
    throughputs = [results[name].avg_throughput_mbps for name in algo_names]
    mins = [results[name].min_throughput_mbps for name in algo_names]
    maxs = [results[name].max_throughput_mbps for name in algo_names]

    bars = ax1.bar(x, throughputs, bar_width, label='Average', color='steelblue')
    ax1.errorbar(x, throughputs,
                 yerr=[np.array(throughputs) - np.array(mins),
                       np.array(maxs) - np.array(throughputs)],
                 fmt='none', color='black', capsize=3)
    ax1.set_ylabel('Throughput (Mbps)')
    ax1.set_title('Throughput Performance')
    ax1.set_xticks(x)
    ax1.set_xticklabels([name[:12] for name in algo_names], rotation=15, ha='right')
    ax1.grid(axis='y', alpha=0.3)

    # Add value labels
    for bar, val in zip(bars, throughputs):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                f'{val:.1f}', ha='center', va='bottom', fontsize=9)

    # 2. PRB Efficiency
    ax2 = axes[0, 1]
    efficiencies = [results[name].prb_efficiency for name in algo_names]
    colors = ['green' if e == max(efficiencies) else 'steelblue' for e in efficiencies]
    bars = ax2.bar(x, efficiencies, bar_width, color=colors)
    ax2.set_ylabel('Throughput per PRB (Mbps/PRB)')
    ax2.set_title('Resource Efficiency')
    ax2.set_xticks(x)
    ax2.set_xticklabels([name[:12] for name in algo_names], rotation=15, ha='right')
    ax2.grid(axis='y', alpha=0.3)

    for bar, val in zip(bars, efficiencies):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f'{val:.3f}', ha='center', va='bottom', fontsize=9)

    # 3. Handover metrics
    ax3 = axes[1, 0]
    handovers = [results[name].handover_count for name in algo_names]
    pingpongs = [results[name].ping_pong_count for name in algo_names]

    width = 0.35
    bars1 = ax3.bar(x - width/2, handovers, width, label='Handovers', color='steelblue')
    bars2 = ax3.bar(x + width/2, pingpongs, width, label='Ping-Pong', color='coral')
    ax3.set_ylabel('Count')
    ax3.set_title('Handover Performance')
    ax3.set_xticks(x)
    ax3.set_xticklabels([name[:12] for name in algo_names], rotation=15, ha='right')
    ax3.legend()
    ax3.grid(axis='y', alpha=0.3)

    # 4. QoS metrics
    ax4 = axes[1, 1]
    continuity = [results[name].service_continuity for name in algo_names]
    fairness = [results[name].fairness_index * 100 for name in algo_names]

    bars1 = ax4.bar(x - width/2, continuity, width, label='Service Continuity (%)', color='steelblue')
    bars2 = ax4.bar(x + width/2, fairness, width, label='Fairness Index (x100)', color='seagreen')
    ax4.set_ylabel('Percentage / Index')
    ax4.set_title('QoS Metrics')
    ax4.set_xticks(x)
    ax4.set_xticklabels([name[:12] for name in algo_names], rotation=15, ha='right')
    ax4.legend()
    ax4.grid(axis='y', alpha=0.3)

    plt.tight_layout()

    chart_path = output_dir / "algorithm_comparison.png"
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved chart: {chart_path}")

    # Generate additional detailed chart
    generate_throughput_distribution_chart(results, output_dir)


def generate_throughput_distribution_chart(results: Dict[str, AlgorithmMetrics],
                                            output_dir: Path):
    """Generate throughput distribution comparison chart."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    algo_names = list(results.keys())

    # Box plot style comparison using percentiles
    positions = range(len(algo_names))

    for i, name in enumerate(algo_names):
        m = results[name]

        # Draw box
        box_low = m.throughput_5th_percentile
        box_high = m.throughput_95th_percentile
        median = m.avg_throughput_mbps

        ax.bar(i, box_high - box_low, bottom=box_low, width=0.5,
               color='steelblue', alpha=0.6, edgecolor='black')
        ax.hlines(median, i - 0.25, i + 0.25, colors='red', linewidth=2)

        # Whiskers
        ax.vlines(i, m.min_throughput_mbps, box_low, colors='black', linewidth=1)
        ax.vlines(i, box_high, m.max_throughput_mbps, colors='black', linewidth=1)
        ax.hlines(m.min_throughput_mbps, i - 0.1, i + 0.1, colors='black')
        ax.hlines(m.max_throughput_mbps, i - 0.1, i + 0.1, colors='black')

    ax.set_xticks(positions)
    ax.set_xticklabels([name[:15] for name in algo_names], rotation=15, ha='right')
    ax.set_ylabel('Throughput (Mbps)')
    ax.set_title('Throughput Distribution by Algorithm\n(5th-95th percentile box, red line=mean)')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()

    chart_path = output_dir / "throughput_distribution.png"
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved chart: {chart_path}")


# =============================================================================
# Output Saving
# =============================================================================

def save_results(output_dir: Path, results: Dict[str, AlgorithmMetrics],
                 table: str, ranking: str, improvement: str):
    """Save all results to files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save JSON results
    json_data = {
        "timestamp": datetime.now().isoformat(),
        "algorithms": {name: asdict(metrics) for name, metrics in results.items()},
        "configuration": {
            "total_prb": TOTAL_PRB,
            "prb_bandwidth_hz": PRB_BANDWIDTH_HZ,
            "handover_delay_ms": HANDOVER_DELAY_MS,
            "rsrp_handover_threshold": RSRP_HANDOVER_THRESHOLD,
            "rsrp_critical_threshold": RSRP_CRITICAL_THRESHOLD,
            "hysteresis_db": HYSTERESIS_DB,
        }
    }

    json_path = output_dir / f"algorithm_comparison_{timestamp}.json"
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    print(f"  Saved JSON results: {json_path}")

    # Save text report
    full_report = table + ranking + improvement
    full_report += f"\n\nGenerated: {datetime.now().isoformat()}\n"

    txt_path = output_dir / f"algorithm_comparison_{timestamp}.txt"
    with open(txt_path, 'w') as f:
        f.write(full_report)
    print(f"  Saved text report: {txt_path}")

    # Save CSV summary
    csv_path = output_dir / f"algorithm_summary_{timestamp}.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)

        # Write header
        header = ["Algorithm"] + [
            "Avg Throughput (Mbps)", "Min Throughput (Mbps)", "Max Throughput (Mbps)",
            "Avg PRB", "PRB Efficiency", "Handover Count", "Ping-Pong Count",
            "HO Delay (ms)", "Service Continuity (%)", "Fairness Index"
        ]
        writer.writerow(header)

        # Write data
        for name, m in results.items():
            row = [
                name,
                f"{m.avg_throughput_mbps:.2f}",
                f"{m.min_throughput_mbps:.2f}",
                f"{m.max_throughput_mbps:.2f}",
                f"{m.avg_prb:.1f}",
                f"{m.prb_efficiency:.4f}",
                m.handover_count,
                m.ping_pong_count,
                m.total_handover_delay_ms,
                f"{m.service_continuity:.1f}",
                f"{m.fairness_index:.4f}"
            ]
            writer.writerow(row)
    print(f"  Saved CSV summary: {csv_path}")

    # Save latest symlink
    latest_json = output_dir / "latest_comparison.json"
    latest_txt = output_dir / "latest_comparison.txt"

    # Remove existing symlinks/files
    for f in [latest_json, latest_txt]:
        if f.exists() or f.is_symlink():
            f.unlink()

    # Copy instead of symlink for better compatibility
    import shutil
    shutil.copy(json_path, latest_json)
    shutil.copy(txt_path, latest_txt)

    return json_path, txt_path, csv_path


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Compare handover and resource allocation algorithms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Algorithms compared:
  1. Rule-based (xApp): RSRP threshold handover, adaptive PRB based on SINR
  2. Random Baseline: Random decisions for baseline comparison
  3. Greedy: Always select strongest signal, proportional PRB
  4. Conservative: Delayed handover, conservative PRB allocation

Example:
  python algorithm_comparison.py --csv /tmp/ns3-uav-full.csv --interval 1.0
        """
    )

    parser.add_argument("--csv", default=DEFAULT_CSV_PATH,
                       help="Path to ns-3 CSV output file")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                       help="Output directory for results")
    parser.add_argument("--interval", type=float, default=1.0,
                       help="Sample interval in seconds (default: 1.0)")
    parser.add_argument("--no-charts", action="store_true",
                       help="Skip chart generation")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED,
                       help="Random seed for reproducibility")

    args = parser.parse_args()

    # Use the seed from args
    random_seed = args.seed

    # Resolve paths
    base_dir = Path(__file__).parent
    csv_path = Path(args.csv)
    output_dir = base_dir / args.output_dir if not Path(args.output_dir).is_absolute() else Path(args.output_dir)

    print("=" * 80)
    print("ALGORITHM COMPARISON TEST")
    print("=" * 80)
    print(f"CSV Data:       {csv_path}")
    print(f"Output Dir:     {output_dir}")
    print(f"Sample Interval: {args.interval}s")
    print(f"Random Seed:    {random_seed}")
    print("=" * 80)

    # Load data
    print("\nLoading CSV data...")
    try:
        samples = load_csv_data(str(csv_path), args.interval)
        print(f"  Loaded {len(samples)} samples")
    except FileNotFoundError:
        print(f"Error: CSV file not found: {csv_path}")
        print("Please ensure the ns-3 simulation data exists.")
        return 1

    if not samples:
        print("Error: No samples loaded from CSV")
        return 1

    # Determine all cells in the data
    all_cells = list(set(s.cell_id for s in samples))
    print(f"  Found {len(all_cells)} unique cells: {all_cells}")

    # Add additional cells for neighbor simulation if needed
    if len(all_cells) < 3:
        for i in range(1, 5):
            if i not in all_cells:
                all_cells.append(i)
        print(f"  Extended to {len(all_cells)} cells for neighbor simulation: {all_cells}")

    # Run comparison
    results = run_comparison(samples, all_cells, seed=random_seed)

    # Generate reports
    print("\nGenerating reports...")
    table = generate_comparison_table(results)
    ranking = generate_ranking_summary(results)
    improvement = generate_improvement_analysis(results)

    # Print results
    print("\n")
    print(table)
    print(ranking)
    print(improvement)

    # Generate charts
    if not args.no_charts:
        print("\nGenerating charts...")
        generate_charts(results, output_dir)

    # Save results
    print("\nSaving results...")
    save_results(output_dir, results, table, ranking, improvement)

    print("\n" + "=" * 80)
    print("COMPARISON COMPLETE")
    print("=" * 80)

    # Print quick summary
    print("\nQuick Summary:")
    print("-" * 40)

    best_throughput = max(results.items(), key=lambda x: x[1].avg_throughput_mbps)
    best_efficiency = max(results.items(), key=lambda x: x[1].prb_efficiency)
    least_handovers = min(results.items(), key=lambda x: x[1].handover_count)

    print(f"  Best Throughput:    {best_throughput[0]} ({best_throughput[1].avg_throughput_mbps:.2f} Mbps)")
    print(f"  Best Efficiency:    {best_efficiency[0]} ({best_efficiency[1].prb_efficiency:.3f} Mbps/PRB)")
    print(f"  Fewest Handovers:   {least_handovers[0]} ({least_handovers[1].handover_count})")

    return 0


if __name__ == "__main__":
    exit(main())
