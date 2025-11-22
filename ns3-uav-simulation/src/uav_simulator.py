#!/usr/bin/env python3
"""
UAV LTE/5G Simulation for xApp Validation

This module simulates a UAV flying over multiple eNBs and generates
realistic radio metrics for xApp validation.

The simulation can run in two modes:
1. Baseline: No xApp control, uses A2-A4 RSRQ handover algorithm
2. xApp-Controlled: Sends metrics to xApp via HTTP and receives control commands

Author: Research Team
Date: 2025-11-21
"""

import math
import time
import json
import logging
import argparse
import requests
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import random

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Position:
    """3D Position in meters"""
    x: float
    y: float
    z: float

    def distance_to(self, other: 'Position') -> float:
        return math.sqrt(
            (self.x - other.x)**2 +
            (self.y - other.y)**2 +
            (self.z - other.z)**2
        )

    def distance_2d(self, other: 'Position') -> float:
        return math.sqrt(
            (self.x - other.x)**2 +
            (self.y - other.y)**2
        )


@dataclass
class EnbConfig:
    """eNB Configuration"""
    cell_id: int
    position: Position
    tx_power_dbm: float = 46.0  # dBm
    frequency_mhz: float = 2600.0  # Band 7
    bandwidth_prbs: int = 100  # 20 MHz
    antenna_height_m: float = 30.0

    def calculate_rsrp(self, ue_position: Position, los_probability: float = 0.8) -> float:
        """
        Calculate RSRP using simplified path loss model.
        Based on 3GPP Urban Macro model with LOS/NLOS consideration.
        """
        distance_3d = self.position.distance_to(ue_position)
        distance_2d = self.position.distance_2d(ue_position)

        if distance_3d < 10:
            distance_3d = 10  # Minimum distance

        # Free space path loss (reference)
        fspl = 20 * math.log10(distance_3d) + 20 * math.log10(self.frequency_mhz) - 27.55

        # Height difference factor (UAV specific)
        height_diff = abs(ue_position.z - self.antenna_height_m)
        height_factor = 0.5 * math.log10(1 + height_diff / 100)

        # LOS/NLOS adjustment
        is_los = random.random() < los_probability
        if is_los:
            # LOS: Lower path loss
            path_loss = fspl + 10 * height_factor
        else:
            # NLOS: Additional 20-30 dB loss
            nlos_extra = random.uniform(20, 30)
            path_loss = fspl + nlos_extra + 15 * height_factor

        # Add small-scale fading (log-normal shadowing)
        shadowing = random.gauss(0, 4)  # 4 dB standard deviation

        rsrp = self.tx_power_dbm - path_loss + shadowing

        # Clamp to realistic values
        return max(-140, min(-40, rsrp))


@dataclass
class UavState:
    """UAV State at a given time"""
    timestamp: float
    position: Position
    velocity: Tuple[float, float, float]
    serving_cell_id: int
    rsrp_serving: float
    rsrq_serving: float
    neighbor_cells: List[Dict]  # [{cell_id, rsrp, rsrq}]
    prb_utilization: float
    allocated_prbs: int
    throughput_mbps: float


@dataclass
class Waypoint:
    """UAV flight waypoint"""
    time: float
    position: Position


class UavSimulator:
    """UAV LTE/5G Simulation Engine"""

    def __init__(
        self,
        sim_time: float = 100.0,
        time_step: float = 0.5,
        xapp_url: Optional[str] = None,
        output_dir: str = "./results"
    ):
        self.sim_time = sim_time
        self.time_step = time_step
        self.xapp_url = xapp_url
        self.output_dir = output_dir
        self.current_time = 0.0

        # Initialize eNBs (based on plan: 3 eNBs in triangle)
        self.enbs = [
            EnbConfig(cell_id=1, position=Position(200, 200, 30)),
            EnbConfig(cell_id=2, position=Position(500, 500, 30)),
            EnbConfig(cell_id=3, position=Position(800, 200, 30)),
        ]

        # Initialize UAV waypoints (based on plan)
        self.waypoints = [
            Waypoint(time=0.0, position=Position(100, 100, 100)),
            Waypoint(time=20.0, position=Position(300, 300, 100)),
            Waypoint(time=40.0, position=Position(500, 500, 100)),
            Waypoint(time=60.0, position=Position(700, 700, 100)),
            Waypoint(time=75.0, position=Position(900, 900, 100)),
            Waypoint(time=100.0, position=Position(900, 900, 100)),
        ]

        # Simulation state
        self.serving_cell_id = 1
        self.allocated_prbs = 45
        self.handover_count = 0
        self.metrics_log: List[UavState] = []

        # PRB utilization per cell (simulated load)
        self.cell_load = {1: 0.3, 2: 0.5, 3: 0.4}

    def get_uav_position(self, t: float) -> Position:
        """Interpolate UAV position at time t"""
        # Find waypoint interval
        prev_wp = self.waypoints[0]
        next_wp = self.waypoints[-1]

        for i in range(len(self.waypoints) - 1):
            if self.waypoints[i].time <= t <= self.waypoints[i + 1].time:
                prev_wp = self.waypoints[i]
                next_wp = self.waypoints[i + 1]
                break

        # Linear interpolation
        if next_wp.time == prev_wp.time:
            alpha = 0
        else:
            alpha = (t - prev_wp.time) / (next_wp.time - prev_wp.time)

        return Position(
            x=prev_wp.position.x + alpha * (next_wp.position.x - prev_wp.position.x),
            y=prev_wp.position.y + alpha * (next_wp.position.y - prev_wp.position.y),
            z=prev_wp.position.z + alpha * (next_wp.position.z - prev_wp.position.z)
        )

    def get_uav_velocity(self, t: float) -> Tuple[float, float, float]:
        """Calculate UAV velocity at time t"""
        dt = 0.1
        pos1 = self.get_uav_position(max(0, t - dt))
        pos2 = self.get_uav_position(min(self.sim_time, t + dt))

        return (
            (pos2.x - pos1.x) / (2 * dt),
            (pos2.y - pos1.y) / (2 * dt),
            (pos2.z - pos1.z) / (2 * dt)
        )

    def calculate_rsrq(self, rsrp: float, interference: float = -100) -> float:
        """Calculate RSRQ from RSRP and interference"""
        # RSRQ = N * RSRP / RSSI, where RSSI includes signal and interference
        # Simplified: RSRQ depends on SINR
        sinr = rsrp - interference
        rsrq = max(-20, min(-3, -10 + sinr / 5))
        return rsrq

    def calculate_throughput(self, rsrp: float, allocated_prbs: int) -> float:
        """Estimate throughput based on RSRP and PRBs"""
        # Simplified Shannon-based estimate
        bandwidth_per_prb = 0.18  # MHz per PRB
        total_bw = allocated_prbs * bandwidth_per_prb

        # SINR from RSRP (simplified)
        sinr_db = rsrp + 100  # Assuming -100 dBm noise floor
        sinr_linear = 10 ** (sinr_db / 10)

        # Shannon capacity
        capacity_bps = total_bw * 1e6 * math.log2(1 + sinr_linear)
        return capacity_bps / 1e6  # Mbps

    def check_handover_condition(
        self,
        rsrp_serving: float,
        neighbor_cells: List[Dict],
        xapp_decision: Optional[Dict] = None
    ) -> Optional[int]:
        """
        Check if handover should occur.

        Baseline: A2-A4 RSRQ algorithm
        xApp-Controlled: Use xApp decision if available
        """
        if xapp_decision and xapp_decision.get('handover'):
            target_cell = xapp_decision.get('target_cell_id')
            if target_cell:
                return target_cell

        # Baseline A2-A4 algorithm
        # A2: Serving becomes worse than threshold
        # A4: Neighbor becomes better than threshold
        serving_threshold = -110  # dBm
        neighbor_offset = 3  # dB

        if rsrp_serving < serving_threshold:
            # Find best neighbor
            best_neighbor = max(neighbor_cells, key=lambda x: x['rsrp'])
            if best_neighbor['rsrp'] > rsrp_serving + neighbor_offset:
                return best_neighbor['cell_id']

        return None

    def send_kpm_indication(self, state: UavState) -> Optional[Dict]:
        """Send KPM indication to xApp and get control decision"""
        if not self.xapp_url:
            return None

        kpm_data = {
            "timestamp": state.timestamp,
            "ue_id": "UAV-001",
            "serving_cell_id": state.serving_cell_id,
            "rsrp_serving": state.rsrp_serving,
            "rsrq_serving": state.rsrq_serving,
            "neighbor_cells": state.neighbor_cells,
            "prb_utilization": state.prb_utilization,
            "position": asdict(state.position),
            "velocity": state.velocity
        }

        try:
            response = requests.post(
                f"{self.xapp_url}/api/v1/kpm/indication",
                json=kpm_data,
                timeout=1.0
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning(f"Failed to send KPM indication: {e}")

        return None

    def step(self) -> UavState:
        """Execute one simulation step"""
        # Get UAV position and velocity
        position = self.get_uav_position(self.current_time)
        velocity = self.get_uav_velocity(self.current_time)

        # Calculate RSRP for all cells
        all_rsrp = {}
        for enb in self.enbs:
            # UAV has higher LOS probability
            los_prob = 0.8 if position.z > 50 else 0.5
            rsrp = enb.calculate_rsrp(position, los_prob)
            all_rsrp[enb.cell_id] = rsrp

        # Serving cell metrics
        rsrp_serving = all_rsrp[self.serving_cell_id]
        rsrq_serving = self.calculate_rsrq(rsrp_serving)

        # Neighbor cells (excluding serving)
        neighbor_cells = []
        for cell_id, rsrp in all_rsrp.items():
            if cell_id != self.serving_cell_id:
                neighbor_cells.append({
                    "cell_id": cell_id,
                    "rsrp": rsrp,
                    "rsrq": self.calculate_rsrq(rsrp)
                })

        # Update cell load (random walk)
        for cell_id in self.cell_load:
            self.cell_load[cell_id] = max(0.1, min(0.9,
                self.cell_load[cell_id] + random.gauss(0, 0.05)))

        prb_utilization = self.cell_load[self.serving_cell_id]

        # Calculate throughput
        throughput = self.calculate_throughput(rsrp_serving, self.allocated_prbs)

        # Create state
        state = UavState(
            timestamp=self.current_time,
            position=position,
            velocity=velocity,
            serving_cell_id=self.serving_cell_id,
            rsrp_serving=rsrp_serving,
            rsrq_serving=rsrq_serving,
            neighbor_cells=neighbor_cells,
            prb_utilization=prb_utilization,
            allocated_prbs=self.allocated_prbs,
            throughput_mbps=throughput
        )

        # Send to xApp and get decision
        xapp_decision = self.send_kpm_indication(state)

        # Apply xApp PRB allocation if provided
        if xapp_decision and 'allocated_prbs' in xapp_decision:
            self.allocated_prbs = xapp_decision['allocated_prbs']
            logger.info(f"xApp allocated PRBs: {self.allocated_prbs}")

        # Check handover condition
        target_cell = self.check_handover_condition(
            rsrp_serving, neighbor_cells, xapp_decision)

        if target_cell and target_cell != self.serving_cell_id:
            logger.info(f"t={self.current_time:.1f}s: Handover "
                       f"{self.serving_cell_id} -> {target_cell}")
            self.serving_cell_id = target_cell
            self.handover_count += 1

        self.metrics_log.append(state)
        return state

    def run(self) -> Dict:
        """Run the complete simulation"""
        logger.info("=" * 50)
        logger.info("UAV LTE Simulation Starting")
        logger.info("=" * 50)
        logger.info(f"Simulation time: {self.sim_time}s")
        logger.info(f"Time step: {self.time_step}s")
        logger.info(f"xApp URL: {self.xapp_url or 'None (Baseline mode)'}")

        start_time = time.time()

        while self.current_time <= self.sim_time:
            state = self.step()

            # Log progress every 10 seconds
            if int(self.current_time) % 10 == 0 and self.current_time > 0:
                logger.info(f"t={self.current_time:.0f}s | "
                           f"Cell={state.serving_cell_id} | "
                           f"RSRP={state.rsrp_serving:.1f}dBm | "
                           f"Throughput={state.throughput_mbps:.1f}Mbps | "
                           f"Handovers={self.handover_count}")

            self.current_time += self.time_step

        elapsed = time.time() - start_time

        # Calculate summary statistics
        avg_rsrp = sum(s.rsrp_serving for s in self.metrics_log) / len(self.metrics_log)
        avg_throughput = sum(s.throughput_mbps for s in self.metrics_log) / len(self.metrics_log)

        summary = {
            "simulation_time": self.sim_time,
            "elapsed_time": elapsed,
            "total_handovers": self.handover_count,
            "avg_rsrp_dbm": avg_rsrp,
            "avg_throughput_mbps": avg_throughput,
            "samples_collected": len(self.metrics_log),
            "xapp_controlled": self.xapp_url is not None
        }

        logger.info("=" * 50)
        logger.info("Simulation Complete")
        logger.info("=" * 50)
        logger.info(f"Total Handovers: {self.handover_count}")
        logger.info(f"Avg RSRP: {avg_rsrp:.1f} dBm")
        logger.info(f"Avg Throughput: {avg_throughput:.1f} Mbps")
        logger.info(f"Elapsed Time: {elapsed:.2f}s")

        return summary

    def save_results(self, filename_prefix: str = "sim"):
        """Save simulation results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save metrics CSV
        metrics_file = f"{self.output_dir}/{filename_prefix}_metrics_{timestamp}.csv"
        with open(metrics_file, 'w') as f:
            f.write("time,x,y,z,serving_cell,rsrp_serving,rsrq_serving,"
                   "prb_util,allocated_prbs,throughput_mbps\n")
            for state in self.metrics_log:
                f.write(f"{state.timestamp:.2f},{state.position.x:.1f},"
                       f"{state.position.y:.1f},{state.position.z:.1f},"
                       f"{state.serving_cell_id},{state.rsrp_serving:.2f},"
                       f"{state.rsrq_serving:.2f},{state.prb_utilization:.3f},"
                       f"{state.allocated_prbs},{state.throughput_mbps:.2f}\n")

        logger.info(f"Metrics saved to: {metrics_file}")

        # Save summary JSON
        summary_file = f"{self.output_dir}/{filename_prefix}_summary_{timestamp}.json"
        summary = {
            "simulation_config": {
                "sim_time": self.sim_time,
                "time_step": self.time_step,
                "xapp_url": self.xapp_url,
                "enb_count": len(self.enbs)
            },
            "results": {
                "total_handovers": self.handover_count,
                "avg_rsrp_dbm": sum(s.rsrp_serving for s in self.metrics_log) / len(self.metrics_log),
                "avg_throughput_mbps": sum(s.throughput_mbps for s in self.metrics_log) / len(self.metrics_log),
                "samples": len(self.metrics_log)
            },
            "timestamp": timestamp
        }

        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Summary saved to: {summary_file}")

        return metrics_file, summary_file


def main():
    parser = argparse.ArgumentParser(description="UAV LTE Simulation")
    parser.add_argument("--sim-time", type=float, default=100.0,
                       help="Simulation time in seconds")
    parser.add_argument("--time-step", type=float, default=0.5,
                       help="Time step in seconds")
    parser.add_argument("--xapp-url", type=str, default=None,
                       help="xApp HTTP URL (e.g., http://localhost:8080)")
    parser.add_argument("--output-dir", type=str,
                       default="/home/thc1006/dev/oran-ric-platform/ns3-uav-simulation/results/baseline",
                       help="Output directory for results")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run simulation
    simulator = UavSimulator(
        sim_time=args.sim_time,
        time_step=args.time_step,
        xapp_url=args.xapp_url,
        output_dir=args.output_dir
    )

    summary = simulator.run()
    simulator.save_results("baseline" if not args.xapp_url else "xapp_controlled")

    return summary


if __name__ == "__main__":
    main()
