#!/usr/bin/env python3
"""
Integrated xApp-Controlled UAV Simulation Test

This script runs the full integration test:
1. Start the UAV Policy xApp server
2. Start the E2 HTTP Bridge
3. Run the UAV simulator in xApp-controlled mode
4. Compare results with baseline

Author: Research Team
Date: 2025-11-21
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

XAPP_DIR = "/home/thc1006/dev/uav-rc-xapp-with-algorithms/xapps/uav-policy"
BRIDGE_DIR = "/home/thc1006/dev/oran-ric-platform/xapp-e2-adapter"
SIM_DIR = "/home/thc1006/dev/oran-ric-platform/ns3-uav-simulation"
RESULTS_DIR = "/home/thc1006/dev/oran-ric-platform/ns3-uav-simulation/results/xapp-controlled"


def ensure_dirs():
    """Ensure result directories exist"""
    Path(RESULTS_DIR).mkdir(parents=True, exist_ok=True)


def check_port_available(port):
    """Check if a port is available"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result != 0


def wait_for_server(url, timeout=30):
    """Wait for server to be ready"""
    import requests
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
    return False


def run_baseline_test():
    """Run baseline test without xApp control"""
    print("\n" + "="*60)
    print("Phase 6: Running Baseline Test (no xApp control)")
    print("="*60)

    from uav_simulator import UavSimulator

    sim = UavSimulator(
        sim_time=75.0,
        time_step=0.5,
        xapp_url=None  # No xApp control
    )

    results = sim.run()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    baseline_dir = Path(SIM_DIR) / "results" / "baseline"
    baseline_dir.mkdir(parents=True, exist_ok=True)

    # Save results
    summary_file = baseline_dir / f"baseline_summary_{timestamp}.json"
    with open(summary_file, 'w') as f:
        json.dump({
            "simulation_config": {
                "sim_time": 75.0,
                "time_step": 0.5,
                "xapp_url": None,
                "enb_count": 3
            },
            "results": results,
            "timestamp": timestamp
        }, f, indent=2)

    print(f"\nBaseline Results:")
    print(f"  Total Handovers: {results['total_handovers']}")
    print(f"  Avg RSRP: {results['avg_rsrp_dbm']:.2f} dBm")
    print(f"  Avg Throughput: {results['avg_throughput_mbps']:.2f} Mbps")
    print(f"  Results saved to: {summary_file}")

    return results


def run_xapp_controlled_test(xapp_url="http://localhost:5000"):
    """Run test with xApp control"""
    print("\n" + "="*60)
    print("Phase 7: Running xApp-Controlled Test")
    print("="*60)

    from uav_simulator import UavSimulator

    sim = UavSimulator(
        sim_time=75.0,
        time_step=0.5,
        xapp_url=xapp_url
    )

    results = sim.run()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    xapp_dir = Path(RESULTS_DIR)
    xapp_dir.mkdir(parents=True, exist_ok=True)

    # Save results
    summary_file = xapp_dir / f"xapp_summary_{timestamp}.json"
    with open(summary_file, 'w') as f:
        json.dump({
            "simulation_config": {
                "sim_time": 75.0,
                "time_step": 0.5,
                "xapp_url": xapp_url,
                "enb_count": 3
            },
            "results": results,
            "timestamp": timestamp
        }, f, indent=2)

    print(f"\nxApp-Controlled Results:")
    print(f"  Total Handovers: {results['total_handovers']}")
    print(f"  Avg RSRP: {results['avg_rsrp_dbm']:.2f} dBm")
    print(f"  Avg Throughput: {results['avg_throughput_mbps']:.2f} Mbps")
    print(f"  Results saved to: {summary_file}")

    return results


def compare_results(baseline, xapp_controlled):
    """Compare baseline and xApp-controlled results"""
    print("\n" + "="*60)
    print("Phase 8: Results Comparison Analysis")
    print("="*60)

    analysis = {
        "baseline": baseline,
        "xapp_controlled": xapp_controlled,
        "improvements": {}
    }

    # Calculate improvements
    ho_diff = xapp_controlled['total_handovers'] - baseline['total_handovers']
    rsrp_diff = xapp_controlled['avg_rsrp_dbm'] - baseline['avg_rsrp_dbm']
    tp_diff = xapp_controlled['avg_throughput_mbps'] - baseline['avg_throughput_mbps']
    tp_pct = (tp_diff / baseline['avg_throughput_mbps'] * 100) if baseline['avg_throughput_mbps'] > 0 else 0

    analysis['improvements'] = {
        'handover_diff': ho_diff,
        'rsrp_improvement_db': rsrp_diff,
        'throughput_improvement_mbps': tp_diff,
        'throughput_improvement_pct': tp_pct
    }

    print("\n" + "-"*60)
    print("| Metric                  | Baseline    | xApp       | Delta     |")
    print("-"*60)
    print(f"| Handovers               | {baseline['total_handovers']:>11} | {xapp_controlled['total_handovers']:>10} | {ho_diff:>+9} |")
    print(f"| Avg RSRP (dBm)          | {baseline['avg_rsrp_dbm']:>11.2f} | {xapp_controlled['avg_rsrp_dbm']:>10.2f} | {rsrp_diff:>+9.2f} |")
    print(f"| Avg Throughput (Mbps)   | {baseline['avg_throughput_mbps']:>11.2f} | {xapp_controlled['avg_throughput_mbps']:>10.2f} | {tp_diff:>+9.2f} |")
    print("-"*60)

    print(f"\nThroughput Improvement: {tp_pct:+.2f}%")

    # Save analysis
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    analysis_dir = Path(SIM_DIR) / "results" / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    analysis_file = analysis_dir / f"comparison_{timestamp}.json"
    with open(analysis_file, 'w') as f:
        json.dump(analysis, f, indent=2)

    print(f"\nAnalysis saved to: {analysis_file}")

    return analysis


def main():
    """Main test runner"""
    print("="*60)
    print("UAV Policy xApp Simulation Validation")
    print("="*60)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    ensure_dirs()

    # Check if xApp server is running
    xapp_url = "http://localhost:5000"

    print("\nChecking xApp server status...")
    if wait_for_server(f"{xapp_url}/health", timeout=5):
        print("xApp server is running")
    else:
        print("xApp server not running. Starting server...")
        # Start xApp server in background
        xapp_process = subprocess.Popen(
            ["python3", "-m", "uav_policy.main"],
            cwd=XAPP_DIR,
            env={**os.environ, "PYTHONPATH": f"{XAPP_DIR}/src:{os.environ.get('PYTHONPATH', '')}"},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(3)

        if not wait_for_server(f"{xapp_url}/health", timeout=10):
            print("ERROR: Failed to start xApp server")
            xapp_process.terminate()
            return 1

        print("xApp server started successfully")

    try:
        # Run baseline test
        baseline_results = run_baseline_test()

        # Run xApp-controlled test
        xapp_results = run_xapp_controlled_test(xapp_url)

        # Compare results
        analysis = compare_results(baseline_results, xapp_results)

        print("\n" + "="*60)
        print("Simulation Validation Complete")
        print("="*60)

        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
