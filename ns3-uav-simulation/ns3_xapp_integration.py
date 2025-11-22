#!/usr/bin/env python3
"""
ns-3 UAV LTE Simulation with xApp Integration Test

This script reads ns-3 simulation output and sends it to the UAV Policy xApp
for handover decision making, simulating a closed-loop O-RAN control.
"""

import csv
import json
import requests
import argparse
from datetime import datetime
from pathlib import Path

XAPP_URL = "http://localhost:5000"

# UAV waypoints from ns-3 simulation (time, x, y, z)
WAYPOINTS = [
    (0, 100, 100, 100),
    (15, 250, 250, 100),
    (30, 400, 400, 100),
    (45, 550, 550, 100),
    (60, 700, 350, 100),
    (75, 850, 200, 100),
]

def interpolate_position(sim_time: float) -> dict:
    """Interpolate UAV position based on waypoints"""
    # Find the two waypoints to interpolate between
    for i in range(len(WAYPOINTS) - 1):
        t1, x1, y1, z1 = WAYPOINTS[i]
        t2, x2, y2, z2 = WAYPOINTS[i + 1]
        if t1 <= sim_time <= t2:
            # Linear interpolation
            ratio = (sim_time - t1) / (t2 - t1) if t2 != t1 else 0
            return {
                "x": x1 + ratio * (x2 - x1),
                "y": y1 + ratio * (y2 - y1),
                "z": z1 + ratio * (z2 - z1)
            }
    # Default to last position
    return {"x": WAYPOINTS[-1][1], "y": WAYPOINTS[-1][2], "z": WAYPOINTS[-1][3]}

def check_xapp_health():
    """Check if xApp is running"""
    try:
        resp = requests.get(f"{XAPP_URL}/health", timeout=5)
        return resp.status_code == 200
    except:
        return False

def send_indication(ue_id: str, cell_id: int, rsrp: float, sinr: float, timestamp: float):
    """Send E2 indication to xApp with proper format"""
    position = interpolate_position(timestamp)

    # Calculate neighbor cell RSRP (simulated based on distance)
    neighbor_rsrp = []
    for neighbor_id in [1, 2, 3]:
        if neighbor_id != cell_id:
            # Neighbor cells have slightly worse RSRP
            neighbor_rsrp.append(rsrp - 5 - (neighbor_id * 2))

    best_neighbor_rsrp = max(neighbor_rsrp) if neighbor_rsrp else rsrp - 10

    payload = {
        "uav_id": ue_id,
        "position": position,
        "path_position": timestamp / 75.0,  # Normalized path progress
        "slice_id": "embb",
        "radio_snapshot": {
            "serving_cell_id": str(cell_id),
            "neighbor_cell_ids": [str(i) for i in [1, 2, 3] if i != cell_id],
            "rsrp_serving": rsrp,
            "rsrp_best_neighbor": best_neighbor_rsrp,
            "prb_utilization_serving": 0.5,  # 50% default utilization
            "prb_utilization_slice": 0.3
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

def run_integration_test(csv_path: str, sample_interval: float = 1.0):
    """Run integration test with ns-3 data"""

    print("=" * 70)
    print("ns-3 UAV LTE + UAV Policy xApp Integration Test")
    print("=" * 70)

    # Check xApp
    if not check_xapp_health():
        print("ERROR: xApp is not running at", XAPP_URL)
        return None
    print(f"xApp Status: HEALTHY")
    print(f"CSV Input: {csv_path}")
    print(f"Sample Interval: {sample_interval}s")
    print("=" * 70)

    # Results tracking
    results = {
        "start_time": datetime.now().isoformat(),
        "csv_path": csv_path,
        "total_samples": 0,
        "xapp_decisions": [],
        "handover_recommendations": 0,
        "maintain_decisions": 0,
        "avg_rsrp": 0,
        "rsrp_samples": []
    }

    last_time = -1
    total_rsrp = 0
    sample_count = 0

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            sim_time = float(row['time'])
            cell_id = int(row['cell_id'])
            rsrp = float(row['rsrp_dbm'])
            sinr = float(row['rsrq_db'])  # Actually SINR in our format

            # Sample at interval
            if sim_time - last_time >= sample_interval:
                last_time = sim_time

                # Send to xApp
                decision = send_indication("uav-001", cell_id, rsrp, sinr, sim_time)

                if decision and "error" not in decision:
                    results["xapp_decisions"].append({
                        "time": sim_time,
                        "cell_id": cell_id,
                        "rsrp": rsrp,
                        "sinr": sinr,
                        "decision": decision
                    })

                    # Count decision types
                    target_cell = decision.get("target_cell_id", str(cell_id))
                    if target_cell != str(cell_id):
                        results["handover_recommendations"] += 1
                        action = "HANDOVER"
                    else:
                        results["maintain_decisions"] += 1
                        action = "MAINTAIN"

                    prb = decision.get("prb_quota", "N/A")
                    print(f"t={sim_time:6.2f}s | Cell={cell_id} | RSRP={rsrp:7.2f} dBm | "
                          f"Action: {action:8s} | PRB: {prb}")
                else:
                    err = decision.get("error", "Unknown") if decision else "No response"
                    print(f"t={sim_time:6.2f}s | Cell={cell_id} | RSRP={rsrp:7.2f} dBm | "
                          f"Error: {err}")

                total_rsrp += rsrp
                sample_count += 1
                results["rsrp_samples"].append({"time": sim_time, "rsrp": rsrp})

    results["total_samples"] = sample_count
    results["avg_rsrp"] = total_rsrp / sample_count if sample_count > 0 else 0
    results["end_time"] = datetime.now().isoformat()

    print("=" * 70)
    print("Integration Test Complete")
    print("=" * 70)
    print(f"Total Samples Sent:        {results['total_samples']}")
    print(f"Average RSRP:              {results['avg_rsrp']:.2f} dBm")
    print(f"Handover Recommendations:  {results['handover_recommendations']}")
    print(f"Maintain Decisions:        {results['maintain_decisions']}")
    print("=" * 70)

    return results

def main():
    parser = argparse.ArgumentParser(description="ns-3 + xApp Integration Test")
    parser.add_argument("--csv", default="/tmp/ns3-uav-full.csv",
                       help="Path to ns-3 CSV output")
    parser.add_argument("--interval", type=float, default=1.0,
                       help="Sample interval in seconds")
    parser.add_argument("--output", default=None,
                       help="Output JSON file path")
    args = parser.parse_args()

    results = run_integration_test(args.csv, args.interval)

    if results and args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to: {args.output}")

    return results

if __name__ == "__main__":
    main()
