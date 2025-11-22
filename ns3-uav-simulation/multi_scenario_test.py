#!/usr/bin/env python3
"""
Multi-Scenario UAV Simulation Test

This script runs multiple scenarios to compare xApp performance under different conditions:
- Fast UAV (20 m/s): Waypoints time interval halved
- Slow UAV (5 m/s): Waypoints time interval doubled
- High Load: PRB utilization set to 0.8

Uses existing ns-3 simulation data and adjusts sampling intervals to simulate different speeds.
"""

import csv
import json
import requests
import argparse
import os
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any
import statistics


# Configuration
XAPP_URL = "http://localhost:5000"
DEFAULT_CSV_PATH = "/tmp/ns3-uav-full.csv"
RESULTS_DIR = "/home/thc1006/dev/oran-ric-platform/ns3-uav-simulation/results/scenarios"


@dataclass
class ScenarioConfig:
    """Configuration for a simulation scenario"""
    name: str
    description: str
    time_scale: float  # Time scaling factor (0.5 = twice as fast, 2.0 = twice as slow)
    prb_utilization: float  # PRB utilization for serving cell
    sample_interval: float  # Sample interval in seconds


@dataclass
class ScenarioResult:
    """Results from a single scenario run"""
    scenario_name: str
    total_samples: int
    avg_rsrp: float
    min_rsrp: float
    max_rsrp: float
    rsrp_std: float
    handover_count: int
    maintain_count: int
    error_count: int
    handover_rate: float
    simulation_duration: float
    decisions: List[Dict[str, Any]]


# Define test scenarios
SCENARIOS = [
    ScenarioConfig(
        name="baseline",
        description="Baseline scenario (10 m/s, normal PRB)",
        time_scale=1.0,
        prb_utilization=0.5,
        sample_interval=1.0
    ),
    ScenarioConfig(
        name="fast_uav",
        description="Fast UAV (20 m/s) - time interval halved",
        time_scale=0.5,  # Time passes twice as fast
        prb_utilization=0.5,
        sample_interval=0.5  # Sample twice as often to match speed
    ),
    ScenarioConfig(
        name="slow_uav",
        description="Slow UAV (5 m/s) - time interval doubled",
        time_scale=2.0,  # Time passes twice as slow
        prb_utilization=0.5,
        sample_interval=2.0  # Sample half as often to match speed
    ),
    ScenarioConfig(
        name="high_load",
        description="High load scenario (PRB utilization 0.8)",
        time_scale=1.0,
        prb_utilization=0.8,
        sample_interval=1.0
    ),
]


# Waypoints from original simulation (time, x, y, z) - baseline 10 m/s
BASE_WAYPOINTS = [
    (0, 100, 100, 100),
    (15, 250, 250, 100),
    (30, 400, 400, 100),
    (45, 550, 550, 100),
    (60, 700, 350, 100),
    (75, 850, 200, 100),
]


def get_scaled_waypoints(time_scale: float) -> List[tuple]:
    """Get waypoints with scaled time intervals"""
    return [(t * time_scale, x, y, z) for t, x, y, z in BASE_WAYPOINTS]


def interpolate_position(sim_time: float, waypoints: List[tuple]) -> Dict[str, float]:
    """Interpolate UAV position based on waypoints"""
    for i in range(len(waypoints) - 1):
        t1, x1, y1, z1 = waypoints[i]
        t2, x2, y2, z2 = waypoints[i + 1]
        if t1 <= sim_time <= t2:
            ratio = (sim_time - t1) / (t2 - t1) if t2 != t1 else 0
            return {
                "x": x1 + ratio * (x2 - x1),
                "y": y1 + ratio * (y2 - y1),
                "z": z1 + ratio * (z2 - z1)
            }
    return {"x": waypoints[-1][1], "y": waypoints[-1][2], "z": waypoints[-1][3]}


def check_xapp_health() -> bool:
    """Check if xApp is running"""
    try:
        resp = requests.get(f"{XAPP_URL}/health", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def send_indication(
    ue_id: str,
    cell_id: int,
    rsrp: float,
    sinr: float,
    timestamp: float,
    waypoints: List[tuple],
    prb_utilization: float
) -> Optional[Dict[str, Any]]:
    """Send E2 indication to xApp with proper format"""
    position = interpolate_position(timestamp, waypoints)
    max_time = waypoints[-1][0] if waypoints else 75.0

    # Calculate neighbor cell RSRP (simulated based on distance)
    neighbor_rsrp = []
    for neighbor_id in [1, 2, 3]:
        if neighbor_id != cell_id:
            neighbor_rsrp.append(rsrp - 5 - (neighbor_id * 2))

    best_neighbor_rsrp = max(neighbor_rsrp) if neighbor_rsrp else rsrp - 10

    payload = {
        "uav_id": ue_id,
        "position": position,
        "path_position": timestamp / max_time if max_time > 0 else 0,
        "slice_id": "embb",
        "radio_snapshot": {
            "serving_cell_id": str(cell_id),
            "neighbor_cell_ids": [str(i) for i in [1, 2, 3] if i != cell_id],
            "rsrp_serving": rsrp,
            "rsrp_best_neighbor": best_neighbor_rsrp,
            "prb_utilization_serving": prb_utilization,
            "prb_utilization_slice": prb_utilization * 0.6
        }
    }

    try:
        resp = requests.post(f"{XAPP_URL}/e2/indication", json=payload, timeout=5)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": resp.text, "status_code": resp.status_code}
    except Exception as e:
        return {"error": str(e)}


def run_scenario(config: ScenarioConfig, csv_path: str, verbose: bool = False) -> ScenarioResult:
    """Run a single scenario and collect results"""

    print(f"\n{'='*70}")
    print(f"Running Scenario: {config.name}")
    print(f"Description: {config.description}")
    print(f"Time Scale: {config.time_scale}x | PRB Utilization: {config.prb_utilization}")
    print(f"Sample Interval: {config.sample_interval}s")
    print(f"{'='*70}")

    waypoints = get_scaled_waypoints(config.time_scale)
    max_sim_time = waypoints[-1][0]

    # Results tracking
    rsrp_samples = []
    decisions = []
    handover_count = 0
    maintain_count = 0
    error_count = 0

    last_time = -1

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Scale the simulation time
            original_time = float(row['time'])
            sim_time = original_time * config.time_scale

            # Skip if beyond our scaled simulation duration
            if sim_time > max_sim_time:
                break

            cell_id = int(row['cell_id'])
            rsrp = float(row['rsrp_dbm'])
            sinr = float(row['rsrq_db'])

            # Sample at scaled interval
            if sim_time - last_time >= config.sample_interval:
                last_time = sim_time

                # Send to xApp
                decision = send_indication(
                    "uav-001",
                    cell_id,
                    rsrp,
                    sinr,
                    sim_time,
                    waypoints,
                    config.prb_utilization
                )

                rsrp_samples.append(rsrp)

                if decision and "error" not in decision:
                    target_cell = decision.get("target_cell_id", str(cell_id))
                    if target_cell != str(cell_id):
                        handover_count += 1
                        action = "HANDOVER"
                    else:
                        maintain_count += 1
                        action = "MAINTAIN"

                    decisions.append({
                        "time": sim_time,
                        "cell_id": cell_id,
                        "rsrp": rsrp,
                        "sinr": sinr,
                        "action": action,
                        "target_cell": target_cell,
                        "prb_quota": decision.get("prb_quota", "N/A"),
                        "confidence": decision.get("confidence", "N/A")
                    })

                    if verbose:
                        print(f"  t={sim_time:6.2f}s | Cell={cell_id} | RSRP={rsrp:7.2f} dBm | "
                              f"Action: {action:8s} | Target: {target_cell}")
                else:
                    error_count += 1
                    err = decision.get("error", "Unknown") if decision else "No response"
                    if verbose:
                        print(f"  t={sim_time:6.2f}s | Cell={cell_id} | RSRP={rsrp:7.2f} dBm | "
                              f"Error: {err}")

    # Calculate statistics
    total_samples = len(rsrp_samples)
    avg_rsrp = statistics.mean(rsrp_samples) if rsrp_samples else 0
    min_rsrp = min(rsrp_samples) if rsrp_samples else 0
    max_rsrp = max(rsrp_samples) if rsrp_samples else 0
    rsrp_std = statistics.stdev(rsrp_samples) if len(rsrp_samples) > 1 else 0
    total_decisions = handover_count + maintain_count
    handover_rate = handover_count / total_decisions if total_decisions > 0 else 0

    result = ScenarioResult(
        scenario_name=config.name,
        total_samples=total_samples,
        avg_rsrp=avg_rsrp,
        min_rsrp=min_rsrp,
        max_rsrp=max_rsrp,
        rsrp_std=rsrp_std,
        handover_count=handover_count,
        maintain_count=maintain_count,
        error_count=error_count,
        handover_rate=handover_rate,
        simulation_duration=max_sim_time,
        decisions=decisions
    )

    # Print summary
    print(f"\n--- {config.name} Summary ---")
    print(f"  Samples: {total_samples}")
    print(f"  Avg RSRP: {avg_rsrp:.2f} dBm (min: {min_rsrp:.2f}, max: {max_rsrp:.2f})")
    print(f"  RSRP Std Dev: {rsrp_std:.2f}")
    print(f"  Handovers: {handover_count} | Maintain: {maintain_count} | Errors: {error_count}")
    print(f"  Handover Rate: {handover_rate*100:.1f}%")

    return result


def print_comparison_table(results: List[ScenarioResult]):
    """Print a comparison table of all scenario results"""
    print("\n" + "="*90)
    print("MULTI-SCENARIO COMPARISON SUMMARY")
    print("="*90)

    # Header
    header = f"{'Scenario':<15} | {'Samples':>8} | {'Avg RSRP':>10} | {'RSRP Std':>8} | {'Handover':>8} | {'Maintain':>8} | {'HO Rate':>8}"
    print(header)
    print("-"*90)

    # Data rows
    for r in results:
        row = f"{r.scenario_name:<15} | {r.total_samples:>8} | {r.avg_rsrp:>10.2f} | {r.rsrp_std:>8.2f} | {r.handover_count:>8} | {r.maintain_count:>8} | {r.handover_rate*100:>7.1f}%"
        print(row)

    print("="*90)

    # Analysis
    print("\nANALYSIS:")

    # Find baseline for comparison
    baseline = next((r for r in results if r.scenario_name == "baseline"), None)

    if baseline:
        for r in results:
            if r.scenario_name != "baseline":
                rsrp_diff = r.avg_rsrp - baseline.avg_rsrp
                ho_diff = r.handover_count - baseline.handover_count
                print(f"  {r.scenario_name} vs baseline:")
                print(f"    - RSRP difference: {rsrp_diff:+.2f} dBm")
                print(f"    - Handover count difference: {ho_diff:+d}")
                print(f"    - Samples ratio: {r.total_samples/baseline.total_samples:.2f}x")


def save_results(results: List[ScenarioResult], output_dir: str):
    """Save results to JSON files"""
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save individual scenario results
    for result in results:
        result_dict = asdict(result)
        filename = os.path.join(output_dir, f"{result.scenario_name}_{timestamp}.json")
        with open(filename, 'w') as f:
            json.dump(result_dict, f, indent=2)
        print(f"  Saved: {filename}")

    # Save summary comparison
    summary = {
        "timestamp": timestamp,
        "scenarios": [
            {
                "name": r.scenario_name,
                "total_samples": r.total_samples,
                "avg_rsrp": r.avg_rsrp,
                "min_rsrp": r.min_rsrp,
                "max_rsrp": r.max_rsrp,
                "rsrp_std": r.rsrp_std,
                "handover_count": r.handover_count,
                "maintain_count": r.maintain_count,
                "error_count": r.error_count,
                "handover_rate": r.handover_rate,
                "simulation_duration": r.simulation_duration
            }
            for r in results
        ]
    }

    summary_file = os.path.join(output_dir, f"comparison_summary_{timestamp}.json")
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"  Saved summary: {summary_file}")

    return summary_file


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Scenario UAV Simulation Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Scenarios:
  - baseline:   Normal speed (10 m/s), normal PRB utilization (0.5)
  - fast_uav:   Fast UAV (20 m/s), waypoint intervals halved
  - slow_uav:   Slow UAV (5 m/s), waypoint intervals doubled
  - high_load:  High PRB utilization (0.8)

Examples:
  python multi_scenario_test.py
  python multi_scenario_test.py --scenarios baseline fast_uav
  python multi_scenario_test.py --csv /path/to/data.csv --verbose
        """
    )
    parser.add_argument(
        "--csv",
        default=DEFAULT_CSV_PATH,
        help=f"Path to ns-3 CSV output (default: {DEFAULT_CSV_PATH})"
    )
    parser.add_argument(
        "--output",
        default=RESULTS_DIR,
        help=f"Output directory for results (default: {RESULTS_DIR})"
    )
    parser.add_argument(
        "--scenarios",
        nargs="+",
        choices=["baseline", "fast_uav", "slow_uav", "high_load"],
        default=None,
        help="Specific scenarios to run (default: all)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed output for each sample"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not save results to files"
    )

    args = parser.parse_args()

    # Verify CSV file exists
    if not os.path.exists(args.csv):
        print(f"ERROR: CSV file not found: {args.csv}")
        return 1

    # Check xApp health
    print("Checking xApp connectivity...")
    if not check_xapp_health():
        print(f"ERROR: xApp is not running at {XAPP_URL}")
        print("Please start the xApp server first.")
        return 1
    print(f"xApp Status: HEALTHY at {XAPP_URL}")

    # Filter scenarios if specified
    scenarios_to_run = SCENARIOS
    if args.scenarios:
        scenarios_to_run = [s for s in SCENARIOS if s.name in args.scenarios]

    print(f"\nRunning {len(scenarios_to_run)} scenario(s)...")
    print(f"CSV Input: {args.csv}")

    # Run all scenarios
    results = []
    for config in scenarios_to_run:
        try:
            result = run_scenario(config, args.csv, args.verbose)
            results.append(result)
        except Exception as e:
            print(f"ERROR running scenario {config.name}: {e}")
            continue

    if not results:
        print("ERROR: No scenarios completed successfully")
        return 1

    # Print comparison table
    print_comparison_table(results)

    # Save results
    if not args.no_save:
        print(f"\nSaving results to: {args.output}")
        summary_file = save_results(results, args.output)
        print(f"\nResults saved successfully!")
        print(f"Summary file: {summary_file}")

    return 0


if __name__ == "__main__":
    exit(main())
