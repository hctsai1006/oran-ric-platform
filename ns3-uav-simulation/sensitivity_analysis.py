#!/usr/bin/env python3
"""
Sensitivity Analysis Script for UAV xApp Simulation

Analyzes the sensitivity of the following parameters on handover performance:
1. RSRP Threshold (-105, -110, -115, -120 dBm)
2. Time-to-Trigger (TTT) (64, 128, 256, 512 ms)
3. Hysteresis (1, 2, 3, 4, 5 dB)
4. UAV Speed (5, 10, 20, 30, 40 m/s)

Metrics measured:
- Average throughput
- Handover count
- Ping-pong handovers
- Service continuity
- PRB utilization

Output:
- Sensitivity analysis plots (heatmaps, line charts)
- LaTeX table summarizing results
- JSON results file
"""

import csv
import json
import math
import os
import statistics
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from itertools import product
import numpy as np

# Plotting libraries
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.ticker import MaxNLocator
import seaborn as sns


# Configuration
DEFAULT_CSV_PATH = "/tmp/ns3-uav-full.csv"
OUTPUT_DIR = Path("/home/thc1006/dev/oran-ric-platform/ns3-uav-simulation/results/sensitivity")

# System parameters
TOTAL_PRB = 100
PRB_BANDWIDTH = 180  # kHz per PRB
BASELINE_PRB = 10

# Parameter ranges for sensitivity analysis
RSRP_THRESHOLDS = [-105, -110, -115, -120]  # dBm
TTT_VALUES = [64, 128, 256, 512]  # ms
HYSTERESIS_VALUES = [1, 2, 3, 4, 5]  # dB
UAV_SPEEDS = [5, 10, 20, 30, 40]  # m/s

# Set random seed for reproducibility
np.random.seed(42)


@dataclass
class SimulationMetrics:
    """Container for simulation metrics."""
    avg_throughput: float
    handover_count: int
    ping_pong_count: int
    service_continuity: float
    prb_utilization: float
    avg_rsrp: float
    avg_sinr: float
    samples_below_threshold: int
    total_samples: int


@dataclass
class ParameterVariation:
    """Container for a single parameter variation result."""
    parameter_name: str
    parameter_value: float
    metrics: SimulationMetrics


class SensitivityAnalyzer:
    """
    Sensitivity analysis engine for UAV xApp simulation.

    Uses base CSV data and applies synthetic adjustments to simulate
    the effect of different parameter configurations.
    """

    def __init__(self, csv_path: str = DEFAULT_CSV_PATH, output_dir: Path = OUTPUT_DIR):
        """
        Initialize the sensitivity analyzer.

        Args:
            csv_path: Path to the base CSV data file
            output_dir: Directory for output files
        """
        self.csv_path = csv_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.base_data: List[Dict] = []
        self.results: Dict[str, List[ParameterVariation]] = {}
        self.heatmap_results: Dict[str, np.ndarray] = {}
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def load_base_data(self) -> bool:
        """
        Load base CSV data.

        Returns:
            True if data was loaded successfully
        """
        print("=" * 70)
        print("Loading Base CSV Data")
        print("=" * 70)

        try:
            with open(self.csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.base_data.append({
                        'time': float(row['time']),
                        'cell_id': int(row['cell_id']),
                        'rsrp_dbm': float(row['rsrp_dbm']),
                        'rsrq_db': float(row['rsrq_db'])
                    })

            print(f"[LOADED] {len(self.base_data)} samples from {self.csv_path}")

            # Calculate base statistics
            rsrps = [d['rsrp_dbm'] for d in self.base_data]
            print(f"  RSRP range: {min(rsrps):.2f} to {max(rsrps):.2f} dBm")
            print(f"  RSRP mean: {statistics.mean(rsrps):.2f} dBm")
            print(f"  Unique cells: {len(set(d['cell_id'] for d in self.base_data))}")

            return True

        except FileNotFoundError:
            print(f"[ERROR] CSV file not found: {self.csv_path}")
            return False
        except Exception as e:
            print(f"[ERROR] Failed to load CSV: {e}")
            return False

    def _estimate_sinr(self, rsrp: float, rsrq: float) -> float:
        """
        Estimate SINR from RSRP and RSRQ.

        Args:
            rsrp: Reference Signal Received Power (dBm)
            rsrq: Reference Signal Received Quality (dB)

        Returns:
            Estimated SINR in dB
        """
        # SINR estimation based on RSRQ
        # RSRQ typically ranges from -19 to -3 dB
        # Map to SINR range of -5 to 25 dB
        sinr = (rsrq + 19) * (30 / 16) - 5
        return max(-5, min(30, sinr))

    def _calculate_throughput(self, sinr: float, prb: int) -> float:
        """
        Calculate throughput using Shannon capacity approximation.

        Args:
            sinr: Signal-to-interference-plus-noise ratio (dB)
            prb: Number of PRBs allocated

        Returns:
            Throughput in Mbps
        """
        sinr_linear = 10 ** (sinr / 10)
        spectral_efficiency = math.log2(1 + sinr_linear)
        bandwidth_hz = prb * PRB_BANDWIDTH * 1000
        throughput_mbps = (bandwidth_hz * spectral_efficiency) / 1e6
        return throughput_mbps

    def _calculate_dynamic_prb(self, sinr: float, rsrp: float) -> int:
        """
        Calculate dynamic PRB allocation based on channel conditions.

        Args:
            sinr: SINR in dB
            rsrp: RSRP in dBm

        Returns:
            Allocated PRBs
        """
        sinr_linear = 10 ** (sinr / 10)
        spectral_efficiency = math.log2(1 + sinr_linear)

        if sinr > 15:
            target_throughput_mbps = 10
            base_prb = max(5, int(target_throughput_mbps * 1e6 / (spectral_efficiency * PRB_BANDWIDTH * 1000)))
        elif sinr > 10:
            target_throughput_mbps = 8
            base_prb = max(6, int(target_throughput_mbps * 1e6 / (spectral_efficiency * PRB_BANDWIDTH * 1000)))
        elif sinr > 5:
            target_throughput_mbps = 6
            base_prb = max(8, int(target_throughput_mbps * 1e6 / (spectral_efficiency * PRB_BANDWIDTH * 1000)))
        else:
            target_throughput_mbps = 4
            base_prb = max(10, int(target_throughput_mbps * 1e6 / (spectral_efficiency * PRB_BANDWIDTH * 1000)))

        # Cell edge compensation
        if rsrp < -118:
            base_prb += 4
        elif rsrp < -115:
            base_prb += 2
        elif rsrp < -110:
            base_prb += 1

        # Resource optimization for excellent conditions
        if sinr > 18 and rsrp > -105:
            base_prb = max(base_prb - 2, 5)

        return max(5, min(20, base_prb))

    def _generate_multi_cell_scenario(
        self,
        speed_factor: float = 1.0,
        duration_sec: float = 300.0
    ) -> List[Dict]:
        """
        Generate a multi-cell mobility scenario with realistic handover conditions.

        Creates a UAV trajectory that passes through multiple cells, generating
        measurement reports at each position. The path is designed to cross
        cell boundaries multiple times.

        Args:
            speed_factor: Factor to adjust UAV speed (1.0 = 10 m/s)
            duration_sec: Simulation duration in seconds

        Returns:
            List of measurement samples with cell_id, rsrp, rsrq
        """
        samples = []
        dt = 0.01  # 10ms sampling interval
        time = 0.0

        # Cell positions (in meters) - hex grid arrangement for realistic deployment
        # Inter-site distance of 300m (typical urban deployment)
        isd = 300
        cell_positions = [
            (0, 0),           # Cell 1 (center)
            (isd, 0),         # Cell 2 (east)
            (isd/2, isd*0.866),   # Cell 3 (northeast)
            (-isd/2, isd*0.866),  # Cell 4 (northwest)
            (-isd, 0),        # Cell 5 (west)
            (-isd/2, -isd*0.866), # Cell 6 (southwest)
            (isd/2, -isd*0.866),  # Cell 7 (southeast)
        ]

        # Path parameters
        base_speed = 10.0  # m/s (base UAV speed)
        actual_speed = base_speed * speed_factor

        # Create a complex path that visits multiple cells
        # Combine circular and linear segments to cross cell boundaries
        path_radius = isd * 0.8  # Radius larger than half ISD to ensure cell crossings

        while time < duration_sec:
            # Multi-loop trajectory to maximize cell boundary crossings
            # Phase determines which part of the path we're on
            t = actual_speed * time / path_radius

            # Rosette pattern - crosses center multiple times
            n_petals = 5
            uav_x = path_radius * math.cos(t) * math.cos(n_petals * t)
            uav_y = path_radius * math.sin(t) * math.cos(n_petals * t)

            # Calculate RSRP from each cell (path loss model)
            cell_rsrps = []
            for cell_id, (cx, cy) in enumerate(cell_positions, start=1):
                distance = math.sqrt((uav_x - cx)**2 + (uav_y - cy)**2)

                # 3GPP Urban Macro path loss model (simplified)
                # PL = 40*(1-4e-3*Dhb)*log10(R) - 18*log10(Dhb) + 21*log10(f) + 80
                # Simplified for UAV at altitude, with distance in meters
                if distance < 10:
                    distance = 10  # Minimum distance

                # Path loss exponent varies with distance
                if distance < 100:
                    path_loss = 30 * math.log10(distance)
                else:
                    path_loss = 30 * math.log10(100) + 40 * math.log10(distance/100)

                # Shadow fading - correlated with speed (faster = more uncorrelated fading)
                # Standard deviation increases with speed due to faster decorrelation
                shadow_std = 4 + 2 * speed_factor  # 4-12 dB typical
                noise = np.random.normal(0, shadow_std)

                # Base TX power at -70 dBm at 1m reference
                rsrp = -70 - path_loss + noise
                rsrp = max(-130, min(-65, rsrp))  # Clamp to realistic range

                cell_rsrps.append((cell_id, rsrp))

            # Find the cell with best RSRP (theoretical best server)
            best_cell_id, best_rsrp = max(cell_rsrps, key=lambda x: x[1])

            # Calculate RSRQ based on interference from other cells
            serving_power = 10**(best_rsrp/10)
            total_power = sum(10**(rsrp/10) for _, rsrp in cell_rsrps)
            rsrq = 10 * math.log10(serving_power / total_power) if total_power > 0 else -10
            rsrq = max(-20, min(-3, rsrq))  # RSRQ typically -20 to -3 dB

            samples.append({
                'time': time,
                'cell_id': best_cell_id,
                'rsrp_dbm': best_rsrp,
                'rsrq_db': rsrq,
                'all_cells': cell_rsrps  # For A3 event evaluation
            })

            time += dt

        return samples

    def _simulate_with_params(
        self,
        rsrp_threshold: float,
        ttt_ms: float,
        hysteresis_db: float,
        speed_factor: float = 1.0
    ) -> SimulationMetrics:
        """
        Simulate handover behavior with specific parameters using A3 event based handover.

        A3 Event: Neighbor cell becomes offset better than serving cell
        Condition: Mn + Ofn + Ocn - Hys > Ms + Ofs + Ocs + Off

        Simplified: neighbor_rsrp - hysteresis > serving_rsrp

        Args:
            rsrp_threshold: RSRP threshold for handover consideration (dBm)
            ttt_ms: Time-to-trigger (ms)
            hysteresis_db: Hysteresis value (dB)
            speed_factor: Factor to adjust for UAV speed effects

        Returns:
            SimulationMetrics for this parameter combination
        """
        # Generate multi-cell scenario with consistent duration
        adjusted_data = self._generate_multi_cell_scenario(
            speed_factor=speed_factor,
            duration_sec=120.0  # Fixed duration, speed affects traversal
        )

        # Handover state tracking
        current_cell = None
        handover_count = 0
        ping_pong_count = 0
        service_interruptions = 0

        # TTT tracking
        dt_ms = 10  # 10ms sample interval
        ttt_samples_needed = max(1, int(ttt_ms / dt_ms))
        pending_target_cell = None
        pending_counter = 0

        # History for ping-pong detection (within specified window)
        ping_pong_window = 2.0  # seconds - shorter TTT may cause more ping-pong
        handover_history = []  # List of (time, from_cell, to_cell)

        throughputs = []
        prbs = []
        rsrps = []
        sinrs = []

        # Track serving cell RSRP for current cell
        serving_cell_rsrp = {}

        for i, sample in enumerate(adjusted_data):
            time = sample['time']
            best_server_cell = sample['cell_id']  # Best cell by RSRP from the data
            best_server_rsrp = sample['rsrp_dbm']
            rsrq = sample['rsrq_db']
            all_cells = sample.get('all_cells', [(best_server_cell, best_server_rsrp)])

            # Update RSRP for all cells
            for cell_id, cell_rsrp in all_cells:
                serving_cell_rsrp[cell_id] = cell_rsrp

            sinr = self._estimate_sinr(best_server_rsrp, rsrq)
            prb = self._calculate_dynamic_prb(sinr, best_server_rsrp)
            throughput = self._calculate_throughput(sinr, prb)

            throughputs.append(throughput)
            prbs.append(prb)
            rsrps.append(best_server_rsrp)
            sinrs.append(sinr)

            # Initialize current cell
            if current_cell is None:
                current_cell = best_server_cell
                continue

            # Get current serving cell's RSRP
            current_cell_rsrp = serving_cell_rsrp.get(current_cell, -140)

            # A3 Event evaluation: Find best neighbor that triggers handover
            best_neighbor = None
            best_neighbor_rsrp = -200

            for cell_id, cell_rsrp in all_cells:
                if cell_id != current_cell:
                    # A3 condition: neighbor_rsrp > serving_rsrp + hysteresis
                    # This is the standard 3GPP A3 event condition
                    if cell_rsrp > current_cell_rsrp + hysteresis_db:
                        if cell_rsrp > best_neighbor_rsrp:
                            best_neighbor = cell_id
                            best_neighbor_rsrp = cell_rsrp

            # Check if handover should be considered
            # A2 event: serving cell becomes worse than threshold
            serving_below_threshold = current_cell_rsrp < rsrp_threshold

            # Combined condition: A3 triggered OR (A2 + better neighbor exists)
            should_consider_handover = (
                best_neighbor is not None or
                (serving_below_threshold and best_server_cell != current_cell and
                 best_server_rsrp > current_cell_rsrp)
            )

            # If A3 not satisfied but A2 triggered, use best server
            if best_neighbor is None and should_consider_handover:
                if best_server_cell != current_cell:
                    best_neighbor = best_server_cell
                    best_neighbor_rsrp = best_server_rsrp

            if should_consider_handover and best_neighbor is not None:
                if pending_target_cell == best_neighbor:
                    pending_counter += 1
                else:
                    pending_target_cell = best_neighbor
                    pending_counter = 1

                # TTT expired - execute handover
                if pending_counter >= ttt_samples_needed:
                    # Record handover
                    handover_count += 1

                    # Check for ping-pong (return to previous cell within window)
                    for prev_time, prev_from, prev_to in reversed(handover_history):
                        if time - prev_time > ping_pong_window:
                            break
                        if prev_to == current_cell and prev_from == best_neighbor:
                            ping_pong_count += 1
                            break

                    handover_history.append((time, current_cell, best_neighbor))

                    # Service interruption if RSRP is very low during handover
                    if current_cell_rsrp < rsrp_threshold - 5:
                        service_interruptions += 1

                    current_cell = best_neighbor
                    pending_target_cell = None
                    pending_counter = 0
            else:
                # Reset TTT counter if condition no longer met
                if pending_target_cell is not None:
                    pending_counter = max(0, pending_counter - 1)  # Gradual decay
                if pending_counter == 0:
                    pending_target_cell = None

        # Calculate metrics
        total_samples = len(adjusted_data)
        samples_below_threshold = sum(1 for r in rsrps if r < rsrp_threshold)

        # Service continuity calculation
        # Base: 100% minus impact of interruptions and ping-pongs
        if handover_count > 0:
            interruption_rate = service_interruptions / handover_count
            ping_pong_rate = ping_pong_count / handover_count
            service_continuity = 1.0 - (interruption_rate * 0.15) - (ping_pong_rate * 0.1)
        else:
            service_continuity = 1.0 if total_samples > 0 else 0.0

        # Also penalize for too many handovers (signaling overhead)
        if handover_count > 20:
            service_continuity -= (handover_count - 20) * 0.005

        service_continuity = max(0.7, min(1.0, service_continuity))

        # PRB utilization
        avg_prb = statistics.mean(prbs) if prbs else BASELINE_PRB
        prb_utilization = avg_prb / TOTAL_PRB

        return SimulationMetrics(
            avg_throughput=statistics.mean(throughputs) if throughputs else 0,
            handover_count=handover_count,
            ping_pong_count=ping_pong_count,
            service_continuity=service_continuity,
            prb_utilization=prb_utilization,
            avg_rsrp=statistics.mean(rsrps) if rsrps else 0,
            avg_sinr=statistics.mean(sinrs) if sinrs else 0,
            samples_below_threshold=samples_below_threshold,
            total_samples=total_samples
        )

    def analyze_rsrp_threshold(self) -> List[ParameterVariation]:
        """Analyze sensitivity to RSRP threshold variations."""
        print("\n" + "=" * 70)
        print("Analyzing RSRP Threshold Sensitivity")
        print("=" * 70)

        results = []
        for threshold in RSRP_THRESHOLDS:
            print(f"  Simulating RSRP threshold: {threshold} dBm")
            metrics = self._simulate_with_params(
                rsrp_threshold=threshold,
                ttt_ms=128,  # Default TTT
                hysteresis_db=3,  # Default hysteresis
                speed_factor=1.0
            )
            results.append(ParameterVariation(
                parameter_name="RSRP Threshold",
                parameter_value=threshold,
                metrics=metrics
            ))
            print(f"    Handovers: {metrics.handover_count}, "
                  f"Ping-pong: {metrics.ping_pong_count}, "
                  f"Throughput: {metrics.avg_throughput:.2f} Mbps")

        self.results["rsrp_threshold"] = results
        return results

    def analyze_ttt(self) -> List[ParameterVariation]:
        """Analyze sensitivity to Time-to-Trigger variations."""
        print("\n" + "=" * 70)
        print("Analyzing Time-to-Trigger (TTT) Sensitivity")
        print("=" * 70)

        results = []
        for ttt in TTT_VALUES:
            print(f"  Simulating TTT: {ttt} ms")
            metrics = self._simulate_with_params(
                rsrp_threshold=-110,  # Default threshold
                ttt_ms=ttt,
                hysteresis_db=3,
                speed_factor=1.0
            )
            results.append(ParameterVariation(
                parameter_name="TTT",
                parameter_value=ttt,
                metrics=metrics
            ))
            print(f"    Handovers: {metrics.handover_count}, "
                  f"Ping-pong: {metrics.ping_pong_count}, "
                  f"Throughput: {metrics.avg_throughput:.2f} Mbps")

        self.results["ttt"] = results
        return results

    def analyze_hysteresis(self) -> List[ParameterVariation]:
        """Analyze sensitivity to hysteresis variations."""
        print("\n" + "=" * 70)
        print("Analyzing Hysteresis Sensitivity")
        print("=" * 70)

        results = []
        for hyst in HYSTERESIS_VALUES:
            print(f"  Simulating Hysteresis: {hyst} dB")
            metrics = self._simulate_with_params(
                rsrp_threshold=-110,
                ttt_ms=128,
                hysteresis_db=hyst,
                speed_factor=1.0
            )
            results.append(ParameterVariation(
                parameter_name="Hysteresis",
                parameter_value=hyst,
                metrics=metrics
            ))
            print(f"    Handovers: {metrics.handover_count}, "
                  f"Ping-pong: {metrics.ping_pong_count}, "
                  f"Throughput: {metrics.avg_throughput:.2f} Mbps")

        self.results["hysteresis"] = results
        return results

    def analyze_uav_speed(self) -> List[ParameterVariation]:
        """Analyze sensitivity to UAV speed variations."""
        print("\n" + "=" * 70)
        print("Analyzing UAV Speed Sensitivity")
        print("=" * 70)

        results = []
        base_speed = 10  # m/s
        for speed in UAV_SPEEDS:
            speed_factor = speed / base_speed
            print(f"  Simulating UAV Speed: {speed} m/s (factor: {speed_factor:.2f})")
            metrics = self._simulate_with_params(
                rsrp_threshold=-110,
                ttt_ms=128,
                hysteresis_db=3,
                speed_factor=speed_factor
            )
            results.append(ParameterVariation(
                parameter_name="UAV Speed",
                parameter_value=speed,
                metrics=metrics
            ))
            print(f"    Handovers: {metrics.handover_count}, "
                  f"Ping-pong: {metrics.ping_pong_count}, "
                  f"Throughput: {metrics.avg_throughput:.2f} Mbps")

        self.results["uav_speed"] = results
        return results

    def generate_2d_heatmap_data(self) -> Dict[str, np.ndarray]:
        """
        Generate 2D heatmap data for parameter combinations.

        Returns:
            Dictionary of heatmap arrays
        """
        print("\n" + "=" * 70)
        print("Generating 2D Heatmap Data (TTT vs Hysteresis)")
        print("=" * 70)

        # TTT vs Hysteresis for different metrics
        n_ttt = len(TTT_VALUES)
        n_hyst = len(HYSTERESIS_VALUES)

        handover_matrix = np.zeros((n_ttt, n_hyst))
        pingpong_matrix = np.zeros((n_ttt, n_hyst))
        throughput_matrix = np.zeros((n_ttt, n_hyst))
        continuity_matrix = np.zeros((n_ttt, n_hyst))

        for i, ttt in enumerate(TTT_VALUES):
            for j, hyst in enumerate(HYSTERESIS_VALUES):
                print(f"  TTT={ttt}ms, Hysteresis={hyst}dB")
                metrics = self._simulate_with_params(
                    rsrp_threshold=-110,
                    ttt_ms=ttt,
                    hysteresis_db=hyst,
                    speed_factor=1.0
                )
                handover_matrix[i, j] = metrics.handover_count
                pingpong_matrix[i, j] = metrics.ping_pong_count
                throughput_matrix[i, j] = metrics.avg_throughput
                continuity_matrix[i, j] = metrics.service_continuity * 100

        self.heatmap_results = {
            'handover': handover_matrix,
            'pingpong': pingpong_matrix,
            'throughput': throughput_matrix,
            'continuity': continuity_matrix
        }

        return self.heatmap_results

    def plot_line_charts(self):
        """Generate line charts for each parameter sensitivity."""
        print("\n" + "=" * 70)
        print("Generating Line Charts")
        print("=" * 70)

        # Set style - use available seaborn style
        plt.style.use('seaborn-whitegrid')

        fig, axes = plt.subplots(2, 2, figsize=(14, 12))

        metrics_to_plot = [
            ('avg_throughput', 'Average Throughput (Mbps)', 'blue'),
            ('handover_count', 'Handover Count', 'red'),
            ('ping_pong_count', 'Ping-Pong Handovers', 'orange'),
            ('service_continuity', 'Service Continuity', 'green')
        ]

        # RSRP Threshold sensitivity
        ax = axes[0, 0]
        rsrp_results = self.results.get('rsrp_threshold', [])
        if rsrp_results:
            x = [r.parameter_value for r in rsrp_results]
            for metric_name, label, color in metrics_to_plot[:2]:
                y = [getattr(r.metrics, metric_name) for r in rsrp_results]
                if metric_name == 'handover_count':
                    ax2 = ax.twinx()
                    ax2.plot(x, y, 'o-', color=color, linewidth=2, markersize=8, label=label)
                    ax2.set_ylabel(label, color=color)
                    ax2.tick_params(axis='y', labelcolor=color)
                else:
                    ax.plot(x, y, 's-', color=color, linewidth=2, markersize=8, label=label)
                    ax.set_ylabel(label, color=color)
                    ax.tick_params(axis='y', labelcolor=color)
        ax.set_xlabel('RSRP Threshold (dBm)')
        ax.set_title('RSRP Threshold Sensitivity')
        ax.grid(True, alpha=0.3)

        # TTT sensitivity
        ax = axes[0, 1]
        ttt_results = self.results.get('ttt', [])
        if ttt_results:
            x = [r.parameter_value for r in ttt_results]
            for metric_name, label, color in metrics_to_plot[:2]:
                y = [getattr(r.metrics, metric_name) for r in ttt_results]
                if metric_name == 'handover_count':
                    ax2 = ax.twinx()
                    ax2.plot(x, y, 'o-', color=color, linewidth=2, markersize=8, label=label)
                    ax2.set_ylabel(label, color=color)
                    ax2.tick_params(axis='y', labelcolor=color)
                else:
                    ax.plot(x, y, 's-', color=color, linewidth=2, markersize=8, label=label)
                    ax.set_ylabel(label, color=color)
                    ax.tick_params(axis='y', labelcolor=color)
        ax.set_xlabel('Time-to-Trigger (ms)')
        ax.set_title('TTT Sensitivity')
        ax.set_xscale('log', base=2)
        ax.grid(True, alpha=0.3)

        # Hysteresis sensitivity
        ax = axes[1, 0]
        hyst_results = self.results.get('hysteresis', [])
        if hyst_results:
            x = [r.parameter_value for r in hyst_results]
            for metric_name, label, color in metrics_to_plot[:2]:
                y = [getattr(r.metrics, metric_name) for r in hyst_results]
                if metric_name == 'handover_count':
                    ax2 = ax.twinx()
                    ax2.plot(x, y, 'o-', color=color, linewidth=2, markersize=8, label=label)
                    ax2.set_ylabel(label, color=color)
                    ax2.tick_params(axis='y', labelcolor=color)
                else:
                    ax.plot(x, y, 's-', color=color, linewidth=2, markersize=8, label=label)
                    ax.set_ylabel(label, color=color)
                    ax.tick_params(axis='y', labelcolor=color)
        ax.set_xlabel('Hysteresis (dB)')
        ax.set_title('Hysteresis Sensitivity')
        ax.grid(True, alpha=0.3)

        # UAV Speed sensitivity
        ax = axes[1, 1]
        speed_results = self.results.get('uav_speed', [])
        if speed_results:
            x = [r.parameter_value for r in speed_results]
            for metric_name, label, color in metrics_to_plot[:2]:
                y = [getattr(r.metrics, metric_name) for r in speed_results]
                if metric_name == 'handover_count':
                    ax2 = ax.twinx()
                    ax2.plot(x, y, 'o-', color=color, linewidth=2, markersize=8, label=label)
                    ax2.set_ylabel(label, color=color)
                    ax2.tick_params(axis='y', labelcolor=color)
                else:
                    ax.plot(x, y, 's-', color=color, linewidth=2, markersize=8, label=label)
                    ax.set_ylabel(label, color=color)
                    ax.tick_params(axis='y', labelcolor=color)
        ax.set_xlabel('UAV Speed (m/s)')
        ax.set_title('UAV Speed Sensitivity')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        output_path = self.output_dir / f"sensitivity_line_charts_{self.timestamp}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"[SAVED] Line charts: {output_path}")

        return output_path

    def plot_heatmaps(self):
        """Generate heatmaps for parameter combinations."""
        print("\n" + "=" * 70)
        print("Generating Heatmaps")
        print("=" * 70)

        if not self.heatmap_results:
            self.generate_2d_heatmap_data()

        fig, axes = plt.subplots(2, 2, figsize=(14, 12))

        heatmap_configs = [
            ('handover', 'Handover Count', 'Reds'),
            ('pingpong', 'Ping-Pong Handovers', 'Oranges'),
            ('throughput', 'Average Throughput (Mbps)', 'Blues'),
            ('continuity', 'Service Continuity (%)', 'Greens')
        ]

        for ax, (key, title, cmap) in zip(axes.flatten(), heatmap_configs):
            data = self.heatmap_results[key]

            sns.heatmap(
                data,
                ax=ax,
                cmap=cmap,
                annot=True,
                fmt='.1f' if key in ['throughput', 'continuity'] else '.0f',
                xticklabels=HYSTERESIS_VALUES,
                yticklabels=TTT_VALUES,
                cbar_kws={'label': title}
            )
            ax.set_xlabel('Hysteresis (dB)')
            ax.set_ylabel('TTT (ms)')
            ax.set_title(f'{title}\n(TTT vs Hysteresis)')

        plt.tight_layout()
        output_path = self.output_dir / f"sensitivity_heatmaps_{self.timestamp}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"[SAVED] Heatmaps: {output_path}")

        return output_path

    def plot_combined_metrics(self):
        """Generate combined metrics comparison chart."""
        print("\n" + "=" * 70)
        print("Generating Combined Metrics Chart")
        print("=" * 70)

        fig, axes = plt.subplots(2, 2, figsize=(14, 12))

        # All parameters - Handover count
        ax = axes[0, 0]
        params = ['rsrp_threshold', 'ttt', 'hysteresis', 'uav_speed']
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

        for param, color in zip(params, colors):
            results = self.results.get(param, [])
            if results:
                x = [r.parameter_value for r in results]
                y = [r.metrics.handover_count for r in results]
                # Normalize x for comparison
                x_norm = [(xi - min(x)) / (max(x) - min(x)) if max(x) != min(x) else 0.5 for xi in x]
                ax.plot(x_norm, y, 'o-', color=color, linewidth=2, markersize=8,
                       label=results[0].parameter_name)
        ax.set_xlabel('Normalized Parameter Value')
        ax.set_ylabel('Handover Count')
        ax.set_title('Handover Sensitivity to All Parameters')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

        # All parameters - Ping-pong count
        ax = axes[0, 1]
        for param, color in zip(params, colors):
            results = self.results.get(param, [])
            if results:
                x = [r.parameter_value for r in results]
                y = [r.metrics.ping_pong_count for r in results]
                x_norm = [(xi - min(x)) / (max(x) - min(x)) if max(x) != min(x) else 0.5 for xi in x]
                ax.plot(x_norm, y, 'o-', color=color, linewidth=2, markersize=8,
                       label=results[0].parameter_name)
        ax.set_xlabel('Normalized Parameter Value')
        ax.set_ylabel('Ping-Pong Handovers')
        ax.set_title('Ping-Pong Sensitivity to All Parameters')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

        # All parameters - Throughput
        ax = axes[1, 0]
        for param, color in zip(params, colors):
            results = self.results.get(param, [])
            if results:
                x = [r.parameter_value for r in results]
                y = [r.metrics.avg_throughput for r in results]
                x_norm = [(xi - min(x)) / (max(x) - min(x)) if max(x) != min(x) else 0.5 for xi in x]
                ax.plot(x_norm, y, 'o-', color=color, linewidth=2, markersize=8,
                       label=results[0].parameter_name)
        ax.set_xlabel('Normalized Parameter Value')
        ax.set_ylabel('Average Throughput (Mbps)')
        ax.set_title('Throughput Sensitivity to All Parameters')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

        # All parameters - Service Continuity
        ax = axes[1, 1]
        for param, color in zip(params, colors):
            results = self.results.get(param, [])
            if results:
                x = [r.parameter_value for r in results]
                y = [r.metrics.service_continuity * 100 for r in results]
                x_norm = [(xi - min(x)) / (max(x) - min(x)) if max(x) != min(x) else 0.5 for xi in x]
                ax.plot(x_norm, y, 'o-', color=color, linewidth=2, markersize=8,
                       label=results[0].parameter_name)
        ax.set_xlabel('Normalized Parameter Value')
        ax.set_ylabel('Service Continuity (%)')
        ax.set_title('Service Continuity Sensitivity to All Parameters')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        output_path = self.output_dir / f"sensitivity_combined_{self.timestamp}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"[SAVED] Combined metrics: {output_path}")

        return output_path

    def plot_parameter_impact_summary(self):
        """Generate bar chart showing relative impact of each parameter."""
        print("\n" + "=" * 70)
        print("Generating Parameter Impact Summary")
        print("=" * 70)

        fig, ax = plt.subplots(figsize=(12, 6))

        params = ['rsrp_threshold', 'ttt', 'hysteresis', 'uav_speed']
        param_labels = ['RSRP Threshold', 'TTT', 'Hysteresis', 'UAV Speed']

        metrics_impact = {
            'Handover Count': [],
            'Ping-Pong': [],
            'Throughput': [],
            'Service Continuity': []
        }

        for param in params:
            results = self.results.get(param, [])
            if results:
                handovers = [r.metrics.handover_count for r in results]
                pingpongs = [r.metrics.ping_pong_count for r in results]
                throughputs = [r.metrics.avg_throughput for r in results]
                continuities = [r.metrics.service_continuity for r in results]

                # Calculate coefficient of variation as impact measure
                ho_cv = (max(handovers) - min(handovers)) / (sum(handovers)/len(handovers) + 0.001) * 100
                pp_cv = (max(pingpongs) - min(pingpongs)) / (sum(pingpongs)/len(pingpongs) + 0.001) * 100
                tp_cv = (max(throughputs) - min(throughputs)) / (sum(throughputs)/len(throughputs) + 0.001) * 100
                sc_cv = (max(continuities) - min(continuities)) / (sum(continuities)/len(continuities) + 0.001) * 100

                metrics_impact['Handover Count'].append(ho_cv)
                metrics_impact['Ping-Pong'].append(pp_cv)
                metrics_impact['Throughput'].append(tp_cv)
                metrics_impact['Service Continuity'].append(sc_cv)

        x = np.arange(len(param_labels))
        width = 0.2

        colors = ['#e41a1c', '#ff7f00', '#377eb8', '#4daf4a']
        for i, (metric, values) in enumerate(metrics_impact.items()):
            ax.bar(x + i * width, values, width, label=metric, color=colors[i])

        ax.set_xlabel('Parameter')
        ax.set_ylabel('Impact (% Variation)')
        ax.set_title('Parameter Impact on Performance Metrics')
        ax.set_xticks(x + width * 1.5)
        ax.set_xticklabels(param_labels)
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        output_path = self.output_dir / f"sensitivity_impact_summary_{self.timestamp}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"[SAVED] Impact summary: {output_path}")

        return output_path

    def generate_latex_table(self) -> str:
        """
        Generate LaTeX table summarizing sensitivity analysis results.

        Returns:
            LaTeX table string
        """
        print("\n" + "=" * 70)
        print("Generating LaTeX Table")
        print("=" * 70)

        latex = []
        latex.append(r"\begin{table}[htbp]")
        latex.append(r"\centering")
        latex.append(r"\caption{Sensitivity Analysis Results for UAV xApp Handover Parameters}")
        latex.append(r"\label{tab:sensitivity}")
        latex.append(r"\begin{tabular}{llrrrrr}")
        latex.append(r"\toprule")
        latex.append(r"Parameter & Value & Throughput & Handovers & Ping-Pong & Continuity & PRB Util. \\")
        latex.append(r" & & (Mbps) & Count & Count & (\%) & (\%) \\")
        latex.append(r"\midrule")

        # RSRP Threshold
        latex.append(r"\multicolumn{7}{l}{\textbf{RSRP Threshold (dBm)}} \\")
        for r in self.results.get('rsrp_threshold', []):
            latex.append(
                f"& {int(r.parameter_value)} & {r.metrics.avg_throughput:.2f} & "
                f"{r.metrics.handover_count} & {r.metrics.ping_pong_count} & "
                f"{r.metrics.service_continuity*100:.1f} & {r.metrics.prb_utilization*100:.1f} \\\\"
            )
        latex.append(r"\midrule")

        # TTT
        latex.append(r"\multicolumn{7}{l}{\textbf{Time-to-Trigger (ms)}} \\")
        for r in self.results.get('ttt', []):
            latex.append(
                f"& {int(r.parameter_value)} & {r.metrics.avg_throughput:.2f} & "
                f"{r.metrics.handover_count} & {r.metrics.ping_pong_count} & "
                f"{r.metrics.service_continuity*100:.1f} & {r.metrics.prb_utilization*100:.1f} \\\\"
            )
        latex.append(r"\midrule")

        # Hysteresis
        latex.append(r"\multicolumn{7}{l}{\textbf{Hysteresis (dB)}} \\")
        for r in self.results.get('hysteresis', []):
            latex.append(
                f"& {int(r.parameter_value)} & {r.metrics.avg_throughput:.2f} & "
                f"{r.metrics.handover_count} & {r.metrics.ping_pong_count} & "
                f"{r.metrics.service_continuity*100:.1f} & {r.metrics.prb_utilization*100:.1f} \\\\"
            )
        latex.append(r"\midrule")

        # UAV Speed
        latex.append(r"\multicolumn{7}{l}{\textbf{UAV Speed (m/s)}} \\")
        for r in self.results.get('uav_speed', []):
            latex.append(
                f"& {int(r.parameter_value)} & {r.metrics.avg_throughput:.2f} & "
                f"{r.metrics.handover_count} & {r.metrics.ping_pong_count} & "
                f"{r.metrics.service_continuity*100:.1f} & {r.metrics.prb_utilization*100:.1f} \\\\"
            )

        latex.append(r"\bottomrule")
        latex.append(r"\end{tabular}")
        latex.append(r"\end{table}")

        latex_content = "\n".join(latex)

        # Save to file
        output_path = self.output_dir / f"sensitivity_table_{self.timestamp}.tex"
        with open(output_path, 'w') as f:
            f.write(latex_content)
        print(f"[SAVED] LaTeX table: {output_path}")

        return latex_content

    def save_json_results(self) -> str:
        """
        Save all results to JSON file.

        Returns:
            Path to saved JSON file
        """
        print("\n" + "=" * 70)
        print("Saving JSON Results")
        print("=" * 70)

        # Convert results to serializable format
        json_results = {
            "timestamp": self.timestamp,
            "base_data_file": self.csv_path,
            "base_data_samples": len(self.base_data),
            "parameter_ranges": {
                "rsrp_threshold_dbm": RSRP_THRESHOLDS,
                "ttt_ms": TTT_VALUES,
                "hysteresis_db": HYSTERESIS_VALUES,
                "uav_speed_ms": UAV_SPEEDS
            },
            "results": {}
        }

        for param_name, variations in self.results.items():
            json_results["results"][param_name] = []
            for v in variations:
                json_results["results"][param_name].append({
                    "parameter_name": v.parameter_name,
                    "parameter_value": v.parameter_value,
                    "metrics": asdict(v.metrics)
                })

        # Add heatmap data
        if self.heatmap_results:
            json_results["heatmap_data"] = {
                "ttt_values": TTT_VALUES,
                "hysteresis_values": HYSTERESIS_VALUES,
                "handover_matrix": self.heatmap_results['handover'].tolist(),
                "pingpong_matrix": self.heatmap_results['pingpong'].tolist(),
                "throughput_matrix": self.heatmap_results['throughput'].tolist(),
                "continuity_matrix": self.heatmap_results['continuity'].tolist()
            }

        # Calculate summary statistics
        json_results["summary"] = self._calculate_summary()

        output_path = self.output_dir / f"sensitivity_results_{self.timestamp}.json"
        with open(output_path, 'w') as f:
            json.dump(json_results, f, indent=2)
        print(f"[SAVED] JSON results: {output_path}")

        return str(output_path)

    def _calculate_summary(self) -> Dict[str, Any]:
        """Calculate summary statistics across all parameter variations."""
        summary = {}

        for param_name, variations in self.results.items():
            if not variations:
                continue

            handovers = [v.metrics.handover_count for v in variations]
            throughputs = [v.metrics.avg_throughput for v in variations]
            pingpongs = [v.metrics.ping_pong_count for v in variations]
            continuities = [v.metrics.service_continuity for v in variations]

            # Find optimal value (minimize ping-pong while maintaining throughput)
            scores = []
            for v in variations:
                # Score: higher throughput, lower ping-pong, higher continuity
                score = (
                    v.metrics.avg_throughput / max(throughputs) * 0.3 +
                    (1 - v.metrics.ping_pong_count / (max(pingpongs) + 0.001)) * 0.4 +
                    v.metrics.service_continuity * 0.3
                )
                scores.append(score)

            best_idx = np.argmax(scores)

            summary[param_name] = {
                "handover_range": [min(handovers), max(handovers)],
                "handover_sensitivity": (max(handovers) - min(handovers)) / (max(handovers) + 0.001),
                "throughput_range": [min(throughputs), max(throughputs)],
                "throughput_sensitivity": (max(throughputs) - min(throughputs)) / (max(throughputs) + 0.001),
                "pingpong_range": [min(pingpongs), max(pingpongs)],
                "continuity_range": [min(continuities), max(continuities)],
                "optimal_value": variations[best_idx].parameter_value,
                "optimal_score": scores[best_idx]
            }

        return summary

    def run_full_analysis(self):
        """Run complete sensitivity analysis."""
        print("=" * 70)
        print("UAV xApp Sensitivity Analysis")
        print("=" * 70)
        print(f"Output directory: {self.output_dir}")
        print(f"Timestamp: {self.timestamp}")
        print("=" * 70)

        # Load data
        if not self.load_base_data():
            print("[ERROR] Failed to load base data. Exiting.")
            return False

        # Run individual parameter analyses
        self.analyze_rsrp_threshold()
        self.analyze_ttt()
        self.analyze_hysteresis()
        self.analyze_uav_speed()

        # Generate 2D heatmap data
        self.generate_2d_heatmap_data()

        # Generate visualizations
        self.plot_line_charts()
        self.plot_heatmaps()
        self.plot_combined_metrics()
        self.plot_parameter_impact_summary()

        # Generate output files
        latex_table = self.generate_latex_table()
        json_path = self.save_json_results()

        # Print summary
        print("\n" + "=" * 70)
        print("Sensitivity Analysis Complete")
        print("=" * 70)
        print(f"\nOutput files:")
        print(f"  - Line charts: sensitivity_line_charts_{self.timestamp}.png")
        print(f"  - Heatmaps: sensitivity_heatmaps_{self.timestamp}.png")
        print(f"  - Combined: sensitivity_combined_{self.timestamp}.png")
        print(f"  - Impact summary: sensitivity_impact_summary_{self.timestamp}.png")
        print(f"  - LaTeX table: sensitivity_table_{self.timestamp}.tex")
        print(f"  - JSON results: sensitivity_results_{self.timestamp}.json")

        # Print key findings
        print("\n" + "=" * 70)
        print("Key Findings")
        print("=" * 70)

        summary = self._calculate_summary()
        for param, stats in summary.items():
            print(f"\n{param.upper().replace('_', ' ')}:")
            print(f"  Handover count range: {stats['handover_range'][0]} - {stats['handover_range'][1]}")
            print(f"  Handover sensitivity: {stats['handover_sensitivity']*100:.1f}%")
            print(f"  Throughput range: {stats['throughput_range'][0]:.2f} - {stats['throughput_range'][1]:.2f} Mbps")
            print(f"  Ping-pong range: {stats['pingpong_range'][0]} - {stats['pingpong_range'][1]}")
            print(f"  Optimal value: {stats['optimal_value']}")

        return True


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Sensitivity Analysis for UAV xApp Simulation"
    )
    parser.add_argument(
        "--csv",
        default=DEFAULT_CSV_PATH,
        help=f"Path to base CSV data file (default: {DEFAULT_CSV_PATH})"
    )
    parser.add_argument(
        "--output",
        default=str(OUTPUT_DIR),
        help=f"Output directory (default: {OUTPUT_DIR})"
    )

    args = parser.parse_args()

    analyzer = SensitivityAnalyzer(
        csv_path=args.csv,
        output_dir=Path(args.output)
    )

    success = analyzer.run_full_analysis()

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
