#!/usr/bin/env python3
"""
Multi-UAV Scenario Simulation Script

Simulates multiple UAV scenarios with different configurations:
1. 2 UAV Coordination - Different trajectories, shared resources
2. 3 UAV Formation - Formation flight, centralized load
3. 5 UAV Dense - Resource competition, congestion testing

Each scenario generates multi-UAV trajectories based on original CSV data,
calls xApp API for each UAV decision, calculates total PRB utilization
and interference, and collects QoS metrics per UAV.

xApp API: http://localhost:5000/e2/indication
Output: results/multi_uav/
"""

import csv
import json
import math
import requests
import argparse
import statistics
import time as time_module
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


# =============================================================================
# Configuration
# =============================================================================

XAPP_URL = "http://localhost:5000"
DEFAULT_CSV_PATH = "/tmp/ns3-uav-full.csv"
RESULTS_DIR = Path("/home/thc1006/dev/oran-ric-platform/ns3-uav-simulation/results/multi_uav")

# Resource constraints
TOTAL_PRB = 100  # Total PRBs available in cell
MAX_PRB_PER_UAV = 25  # Maximum PRB allocation per UAV
MIN_PRB_PER_UAV = 3   # Minimum PRB allocation per UAV

# QoS thresholds
RSRP_GOOD_THRESHOLD = -100  # dBm
RSRP_ACCEPTABLE_THRESHOLD = -110  # dBm
RSRP_CRITICAL_THRESHOLD = -120  # dBm
SINR_GOOD_THRESHOLD = 15  # dB
SINR_ACCEPTABLE_THRESHOLD = 5  # dB

# Interference parameters
INTERFERENCE_DISTANCE_THRESHOLD = 100  # meters
INTERFERENCE_FACTOR = 0.15  # PRB interference factor when UAVs are close

# Base waypoints (single UAV reference trajectory)
BASE_WAYPOINTS = [
    (0, 100, 100, 100),
    (15, 250, 250, 100),
    (30, 400, 400, 100),
    (45, 550, 550, 100),
    (60, 700, 350, 100),
    (75, 850, 200, 100),
]


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class UAVConfig:
    """Configuration for a single UAV"""
    uav_id: str
    trajectory_offset: Tuple[float, float, float]  # (x, y, z) offset from base
    time_delay: float  # Time delay in seconds (negative = ahead)
    priority: int  # 1=high, 2=medium, 3=low
    slice_id: str = "embb"
    description: str = ""


@dataclass
class UAVState:
    """Current state of a UAV"""
    uav_id: str
    time: float
    position: Dict[str, float]
    cell_id: int
    rsrp: float
    sinr: float
    prb_allocated: int = 0
    throughput_mbps: float = 0.0
    interference_level: float = 0.0
    qos_satisfied: bool = True


@dataclass
class ScenarioConfig:
    """Configuration for a multi-UAV scenario"""
    name: str
    description: str
    uav_configs: List[UAVConfig]
    sample_interval: float = 1.0
    simulation_duration: float = 75.0


@dataclass
class UAVMetrics:
    """QoS metrics for a single UAV"""
    uav_id: str
    total_samples: int = 0
    avg_rsrp: float = 0.0
    min_rsrp: float = 0.0
    max_rsrp: float = 0.0
    std_rsrp: float = 0.0
    avg_sinr: float = 0.0
    avg_throughput_mbps: float = 0.0
    avg_prb_allocated: float = 0.0
    handover_count: int = 0
    maintain_count: int = 0
    error_count: int = 0
    qos_satisfaction_rate: float = 0.0
    samples_below_threshold: int = 0
    avg_interference: float = 0.0


@dataclass
class ScenarioResult:
    """Results from a multi-UAV scenario"""
    scenario_name: str
    description: str
    num_uavs: int
    total_samples: int
    simulation_duration: float
    timestamp: str

    # Aggregate metrics
    total_prb_utilization: float = 0.0
    avg_prb_utilization: float = 0.0
    peak_prb_utilization: float = 0.0
    total_interference_events: int = 0
    avg_system_throughput_mbps: float = 0.0

    # Per-UAV metrics
    uav_metrics: List[UAVMetrics] = field(default_factory=list)

    # Time series data
    prb_utilization_timeline: List[Dict] = field(default_factory=list)
    interference_timeline: List[Dict] = field(default_factory=list)


# =============================================================================
# Multi-UAV Scenarios Definition
# =============================================================================

SCENARIOS = {
    "2uav_coordination": ScenarioConfig(
        name="2uav_coordination",
        description="2 UAV Coordination - Different trajectories, shared resources",
        uav_configs=[
            UAVConfig(
                uav_id="uav-001",
                trajectory_offset=(0, 0, 0),
                time_delay=0,
                priority=1,
                description="Primary UAV - base trajectory"
            ),
            UAVConfig(
                uav_id="uav-002",
                trajectory_offset=(150, -100, 20),
                time_delay=10,
                priority=2,
                description="Secondary UAV - offset trajectory, delayed start"
            ),
        ],
        sample_interval=1.0,
        simulation_duration=75.0
    ),

    "3uav_formation": ScenarioConfig(
        name="3uav_formation",
        description="3 UAV Formation Flight - Triangle formation, centralized load",
        uav_configs=[
            UAVConfig(
                uav_id="uav-lead",
                trajectory_offset=(0, 0, 0),
                time_delay=0,
                priority=1,
                description="Formation leader"
            ),
            UAVConfig(
                uav_id="uav-wing1",
                trajectory_offset=(-50, -50, 10),
                time_delay=0,
                priority=2,
                description="Left wing UAV"
            ),
            UAVConfig(
                uav_id="uav-wing2",
                trajectory_offset=(50, -50, 10),
                time_delay=0,
                priority=2,
                description="Right wing UAV"
            ),
        ],
        sample_interval=1.0,
        simulation_duration=75.0
    ),

    "5uav_dense": ScenarioConfig(
        name="5uav_dense",
        description="5 UAV Dense Deployment - Resource competition, congestion testing",
        uav_configs=[
            UAVConfig(
                uav_id="uav-alpha",
                trajectory_offset=(0, 0, 0),
                time_delay=0,
                priority=1,
                slice_id="embb",
                description="High priority surveillance UAV"
            ),
            UAVConfig(
                uav_id="uav-beta",
                trajectory_offset=(80, 60, 15),
                time_delay=5,
                priority=2,
                slice_id="embb",
                description="Medium priority delivery UAV 1"
            ),
            UAVConfig(
                uav_id="uav-gamma",
                trajectory_offset=(-80, 60, 15),
                time_delay=10,
                priority=2,
                slice_id="urllc",
                description="Medium priority delivery UAV 2"
            ),
            UAVConfig(
                uav_id="uav-delta",
                trajectory_offset=(40, -80, 20),
                time_delay=15,
                priority=3,
                slice_id="embb",
                description="Low priority inspection UAV 1"
            ),
            UAVConfig(
                uav_id="uav-epsilon",
                trajectory_offset=(-40, -80, 20),
                time_delay=20,
                priority=3,
                slice_id="miot",
                description="Low priority inspection UAV 2"
            ),
        ],
        sample_interval=0.5,  # Higher sampling rate for dense scenario
        simulation_duration=75.0
    ),
}


# =============================================================================
# Helper Functions
# =============================================================================

def interpolate_position(sim_time: float, waypoints: List[Tuple],
                         offset: Tuple[float, float, float] = (0, 0, 0)) -> Dict[str, float]:
    """Interpolate UAV position based on waypoints with offset"""
    for i in range(len(waypoints) - 1):
        t1, x1, y1, z1 = waypoints[i]
        t2, x2, y2, z2 = waypoints[i + 1]
        if t1 <= sim_time <= t2:
            ratio = (sim_time - t1) / (t2 - t1) if t2 != t1 else 0
            return {
                "x": x1 + ratio * (x2 - x1) + offset[0],
                "y": y1 + ratio * (y2 - y1) + offset[1],
                "z": z1 + ratio * (z2 - z1) + offset[2]
            }
    # After last waypoint, stay at final position
    return {
        "x": waypoints[-1][1] + offset[0],
        "y": waypoints[-1][2] + offset[1],
        "z": waypoints[-1][3] + offset[2]
    }


def calculate_distance(pos1: Dict[str, float], pos2: Dict[str, float]) -> float:
    """Calculate 3D Euclidean distance between two positions"""
    return math.sqrt(
        (pos1["x"] - pos2["x"]) ** 2 +
        (pos1["y"] - pos2["y"]) ** 2 +
        (pos1["z"] - pos2["z"]) ** 2
    )


def calculate_interference(uav_states: List[UAVState], current_uav_id: str) -> float:
    """
    Calculate interference level for a UAV based on proximity to other UAVs.
    Returns interference factor (0.0 - 1.0)
    """
    current_uav = next((u for u in uav_states if u.uav_id == current_uav_id), None)
    if not current_uav:
        return 0.0

    interference = 0.0
    for other_uav in uav_states:
        if other_uav.uav_id == current_uav_id:
            continue

        distance = calculate_distance(current_uav.position, other_uav.position)
        if distance < INTERFERENCE_DISTANCE_THRESHOLD:
            # Interference increases as distance decreases
            proximity_factor = 1.0 - (distance / INTERFERENCE_DISTANCE_THRESHOLD)
            # Same cell increases interference
            cell_factor = 1.5 if other_uav.cell_id == current_uav.cell_id else 1.0
            interference += proximity_factor * cell_factor * INTERFERENCE_FACTOR

    return min(1.0, interference)  # Cap at 1.0


def calculate_throughput(sinr: float, prb: int, interference: float = 0.0) -> float:
    """
    Calculate estimated throughput using Shannon capacity.
    C = B * log2(1 + SINR / (1 + I))
    """
    if prb <= 0:
        return 0.0

    sinr_linear = 10 ** (sinr / 10)
    effective_sinr = sinr_linear / (1 + interference)
    spectral_efficiency = math.log2(1 + effective_sinr)
    bandwidth_hz = prb * 180 * 1000  # 180 kHz per PRB
    throughput_mbps = (bandwidth_hz * spectral_efficiency) / 1e6

    return throughput_mbps


def check_qos_satisfaction(rsrp: float, sinr: float, throughput: float,
                           priority: int) -> bool:
    """Check if QoS requirements are satisfied based on priority"""
    if priority == 1:  # High priority - strict requirements
        return rsrp >= RSRP_ACCEPTABLE_THRESHOLD and sinr >= SINR_ACCEPTABLE_THRESHOLD
    elif priority == 2:  # Medium priority
        return rsrp >= RSRP_CRITICAL_THRESHOLD and sinr >= 0
    else:  # Low priority
        return rsrp >= RSRP_CRITICAL_THRESHOLD


def allocate_prb_fair(uav_states: List[UAVState], total_available: int) -> Dict[str, int]:
    """
    Fair PRB allocation considering priority and channel conditions.
    Higher priority and worse channel conditions get more PRBs.
    """
    if not uav_states:
        return {}

    allocations = {}

    # Calculate weights based on priority and channel quality
    weights = {}
    total_weight = 0

    for uav in uav_states:
        # Priority weight (higher priority = higher weight)
        priority_weight = 4 - uav.priority if hasattr(uav, 'priority') else 1

        # Channel quality weight (worse channel = higher weight)
        if uav.rsrp < RSRP_CRITICAL_THRESHOLD:
            channel_weight = 2.0
        elif uav.rsrp < RSRP_ACCEPTABLE_THRESHOLD:
            channel_weight = 1.5
        else:
            channel_weight = 1.0

        weights[uav.uav_id] = priority_weight * channel_weight
        total_weight += weights[uav.uav_id]

    # Allocate PRBs proportionally
    remaining_prb = total_available
    for uav in uav_states:
        if total_weight > 0:
            share = int((weights[uav.uav_id] / total_weight) * total_available)
            allocated = max(MIN_PRB_PER_UAV, min(MAX_PRB_PER_UAV, share))
            allocated = min(allocated, remaining_prb)
            allocations[uav.uav_id] = allocated
            remaining_prb -= allocated
        else:
            allocations[uav.uav_id] = MIN_PRB_PER_UAV

    return allocations


# =============================================================================
# xApp Communication
# =============================================================================

class XAppClient:
    """Thread-safe xApp API client"""

    def __init__(self, base_url: str = XAPP_URL, timeout: float = 5.0):
        self.base_url = base_url
        self.timeout = timeout
        self._lock = threading.Lock()
        self._session = requests.Session()

    def check_health(self) -> bool:
        """Check if xApp is running"""
        try:
            resp = self._session.get(f"{self.base_url}/health", timeout=self.timeout)
            return resp.status_code == 200
        except Exception:
            return False

    def send_indication(self, uav_id: str, cell_id: int, rsrp: float, sinr: float,
                        timestamp: float, position: Dict[str, float],
                        prb_utilization: float, slice_id: str = "embb",
                        num_uavs: int = 1) -> Optional[Dict[str, Any]]:
        """Send E2 indication to xApp and get decision"""

        # Calculate neighbor cell info
        neighbor_rsrp = []
        for neighbor_id in [1, 2, 3]:
            if neighbor_id != cell_id:
                neighbor_rsrp.append(rsrp - 5 - (neighbor_id * 2))

        best_neighbor_rsrp = max(neighbor_rsrp) if neighbor_rsrp else rsrp - 10

        payload = {
            "uav_id": uav_id,
            "position": position,
            "path_position": min(1.0, timestamp / 75.0),
            "slice_id": slice_id,
            "radio_snapshot": {
                "serving_cell_id": str(cell_id),
                "neighbor_cell_ids": [str(i) for i in [1, 2, 3] if i != cell_id],
                "rsrp_serving": rsrp,
                "rsrp_best_neighbor": best_neighbor_rsrp,
                "prb_utilization_serving": prb_utilization,
                "prb_utilization_slice": prb_utilization * 0.6
            },
            # Multi-UAV context
            "multi_uav_context": {
                "total_uavs": num_uavs,
                "congestion_level": min(1.0, prb_utilization * num_uavs / 2)
            }
        }

        try:
            with self._lock:
                resp = self._session.post(
                    f"{self.base_url}/e2/indication",
                    json=payload,
                    timeout=self.timeout
                )

            if resp.status_code == 200:
                return resp.json()
            else:
                return {"error": resp.text, "status_code": resp.status_code}
        except Exception as e:
            return {"error": str(e)}


# =============================================================================
# CSV Data Loader
# =============================================================================

class CSVDataLoader:
    """Load and sample CSV simulation data"""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.data = self._load_data()

    def _load_data(self) -> List[Dict]:
        """Load all CSV data into memory"""
        data = []
        with open(self.csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append({
                    "time": float(row['time']),
                    "cell_id": int(row['cell_id']),
                    "rsrp": float(row['rsrp_dbm']),
                    "sinr": float(row['rsrq_db'])  # Actually SINR in this format
                })
        return data

    def get_sample_at_time(self, target_time: float, time_delay: float = 0.0) -> Optional[Dict]:
        """Get the closest sample to the target time with optional delay"""
        effective_time = target_time - time_delay
        if effective_time < 0:
            return None

        # Find closest sample
        closest = None
        min_diff = float('inf')

        for sample in self.data:
            diff = abs(sample['time'] - effective_time)
            if diff < min_diff:
                min_diff = diff
                closest = sample

        return closest

    def get_max_time(self) -> float:
        """Get maximum simulation time in data"""
        return max(s['time'] for s in self.data) if self.data else 0.0


# =============================================================================
# Multi-UAV Simulator
# =============================================================================

class MultiUAVSimulator:
    """Simulate multiple UAVs with xApp integration"""

    def __init__(self, csv_path: str, xapp_client: XAppClient, verbose: bool = False):
        self.csv_loader = CSVDataLoader(csv_path)
        self.xapp_client = xapp_client
        self.verbose = verbose

    def run_scenario(self, scenario: ScenarioConfig) -> ScenarioResult:
        """Run a complete multi-UAV scenario"""

        print(f"\n{'='*80}")
        print(f"SCENARIO: {scenario.name}")
        print(f"Description: {scenario.description}")
        print(f"Number of UAVs: {len(scenario.uav_configs)}")
        print(f"Sample Interval: {scenario.sample_interval}s")
        print(f"{'='*80}")

        # Initialize result
        result = ScenarioResult(
            scenario_name=scenario.name,
            description=scenario.description,
            num_uavs=len(scenario.uav_configs),
            total_samples=0,
            simulation_duration=scenario.simulation_duration,
            timestamp=datetime.now().isoformat(),
            uav_metrics=[
                UAVMetrics(uav_id=uav.uav_id)
                for uav in scenario.uav_configs
            ]
        )

        # Tracking variables
        uav_data = {uav.uav_id: {
            "config": uav,
            "rsrp_samples": [],
            "sinr_samples": [],
            "throughput_samples": [],
            "prb_samples": [],
            "interference_samples": [],
            "qos_satisfied_count": 0,
            "handover_count": 0,
            "maintain_count": 0,
            "error_count": 0,
            "last_cell": None
        } for uav in scenario.uav_configs}

        prb_timeline = []
        interference_timeline = []
        total_samples = 0

        # Simulation loop
        current_time = 0.0
        while current_time <= scenario.simulation_duration:
            # Collect current state for all UAVs
            uav_states = []

            for uav_config in scenario.uav_configs:
                # Get CSV sample for this UAV (considering time delay)
                csv_sample = self.csv_loader.get_sample_at_time(
                    current_time,
                    uav_config.time_delay
                )

                if csv_sample is None:
                    continue

                # Calculate position with offset
                position = interpolate_position(
                    current_time - uav_config.time_delay,
                    BASE_WAYPOINTS,
                    uav_config.trajectory_offset
                )

                # Apply spatial variation to radio measurements
                offset_distance = math.sqrt(
                    uav_config.trajectory_offset[0]**2 +
                    uav_config.trajectory_offset[1]**2
                )
                rsrp_variation = -offset_distance * 0.02  # RSRP degrades with offset
                sinr_variation = -offset_distance * 0.01

                state = UAVState(
                    uav_id=uav_config.uav_id,
                    time=current_time,
                    position=position,
                    cell_id=csv_sample['cell_id'],
                    rsrp=csv_sample['rsrp'] + rsrp_variation,
                    sinr=csv_sample['sinr'] + sinr_variation
                )
                uav_states.append(state)

            if not uav_states:
                current_time += scenario.sample_interval
                continue

            # Calculate interference for each UAV
            for state in uav_states:
                state.interference_level = calculate_interference(uav_states, state.uav_id)

            # Calculate system PRB utilization (estimate before allocation)
            base_prb_utilization = 0.3 + (len(uav_states) * 0.1)  # Base + UAV load

            # Fair PRB allocation
            prb_allocations = allocate_prb_fair(uav_states, TOTAL_PRB)

            # Process each UAV through xApp
            for state in uav_states:
                uav_id = state.uav_id
                data = uav_data[uav_id]
                config = data["config"]

                # Update PRB allocation
                state.prb_allocated = prb_allocations.get(uav_id, MIN_PRB_PER_UAV)

                # Calculate throughput with interference
                state.throughput_mbps = calculate_throughput(
                    state.sinr,
                    state.prb_allocated,
                    state.interference_level
                )

                # Check QoS satisfaction
                state.qos_satisfied = check_qos_satisfaction(
                    state.rsrp,
                    state.sinr,
                    state.throughput_mbps,
                    config.priority
                )

                # Send to xApp
                decision = self.xapp_client.send_indication(
                    uav_id=uav_id,
                    cell_id=state.cell_id,
                    rsrp=state.rsrp,
                    sinr=state.sinr,
                    timestamp=current_time,
                    position=state.position,
                    prb_utilization=base_prb_utilization,
                    slice_id=config.slice_id,
                    num_uavs=len(uav_states)
                )

                # Process decision
                if decision and "error" not in decision:
                    target_cell = decision.get("target_cell_id", str(state.cell_id))

                    # Detect handover
                    if data["last_cell"] is not None and target_cell != str(data["last_cell"]):
                        data["handover_count"] += 1
                        action = "HANDOVER"
                    else:
                        data["maintain_count"] += 1
                        action = "MAINTAIN"

                    data["last_cell"] = target_cell

                    if self.verbose:
                        print(f"  t={current_time:6.1f}s | {uav_id:<12} | Cell={state.cell_id} | "
                              f"RSRP={state.rsrp:7.2f} | PRB={state.prb_allocated:2d} | "
                              f"Int={state.interference_level:.2f} | {action}")
                else:
                    data["error_count"] += 1
                    if self.verbose:
                        err = decision.get("error", "Unknown") if decision else "No response"
                        print(f"  t={current_time:6.1f}s | {uav_id:<12} | ERROR: {err}")

                # Record samples
                data["rsrp_samples"].append(state.rsrp)
                data["sinr_samples"].append(state.sinr)
                data["throughput_samples"].append(state.throughput_mbps)
                data["prb_samples"].append(state.prb_allocated)
                data["interference_samples"].append(state.interference_level)
                if state.qos_satisfied:
                    data["qos_satisfied_count"] += 1

            # Record timeline data
            total_prb_used = sum(s.prb_allocated for s in uav_states)
            prb_timeline.append({
                "time": current_time,
                "total_prb_used": total_prb_used,
                "utilization": total_prb_used / TOTAL_PRB,
                "per_uav": {s.uav_id: s.prb_allocated for s in uav_states}
            })

            total_interference = sum(s.interference_level for s in uav_states)
            interference_timeline.append({
                "time": current_time,
                "total_interference": total_interference,
                "per_uav": {s.uav_id: s.interference_level for s in uav_states}
            })

            total_samples += len(uav_states)
            current_time += scenario.sample_interval

        # Calculate final metrics
        result.total_samples = total_samples
        result.prb_utilization_timeline = prb_timeline
        result.interference_timeline = interference_timeline

        # Aggregate PRB metrics
        if prb_timeline:
            utilizations = [p["utilization"] for p in prb_timeline]
            result.avg_prb_utilization = statistics.mean(utilizations)
            result.peak_prb_utilization = max(utilizations)
            result.total_prb_utilization = sum(p["total_prb_used"] for p in prb_timeline)

        # Count interference events
        result.total_interference_events = sum(
            1 for i in interference_timeline if i["total_interference"] > 0.3
        )

        # Per-UAV metrics
        system_throughputs = []
        for idx, uav_config in enumerate(scenario.uav_configs):
            data = uav_data[uav_config.uav_id]
            metrics = result.uav_metrics[idx]

            if data["rsrp_samples"]:
                metrics.total_samples = len(data["rsrp_samples"])
                metrics.avg_rsrp = statistics.mean(data["rsrp_samples"])
                metrics.min_rsrp = min(data["rsrp_samples"])
                metrics.max_rsrp = max(data["rsrp_samples"])
                metrics.std_rsrp = statistics.stdev(data["rsrp_samples"]) if len(data["rsrp_samples"]) > 1 else 0
                metrics.avg_sinr = statistics.mean(data["sinr_samples"])
                metrics.avg_throughput_mbps = statistics.mean(data["throughput_samples"])
                metrics.avg_prb_allocated = statistics.mean(data["prb_samples"])
                metrics.avg_interference = statistics.mean(data["interference_samples"])
                metrics.handover_count = data["handover_count"]
                metrics.maintain_count = data["maintain_count"]
                metrics.error_count = data["error_count"]
                metrics.qos_satisfaction_rate = (
                    data["qos_satisfied_count"] / metrics.total_samples
                    if metrics.total_samples > 0 else 0
                )
                metrics.samples_below_threshold = sum(
                    1 for r in data["rsrp_samples"] if r < RSRP_ACCEPTABLE_THRESHOLD
                )

                system_throughputs.extend(data["throughput_samples"])

        result.avg_system_throughput_mbps = statistics.mean(system_throughputs) if system_throughputs else 0

        # Print summary
        self._print_scenario_summary(result)

        return result

    def _print_scenario_summary(self, result: ScenarioResult):
        """Print scenario summary"""
        print(f"\n{'='*80}")
        print(f"SCENARIO SUMMARY: {result.scenario_name}")
        print(f"{'='*80}")
        print(f"Total Samples: {result.total_samples}")
        print(f"Simulation Duration: {result.simulation_duration}s")
        print(f"Average PRB Utilization: {result.avg_prb_utilization*100:.1f}%")
        print(f"Peak PRB Utilization: {result.peak_prb_utilization*100:.1f}%")
        print(f"Interference Events: {result.total_interference_events}")
        print(f"System Avg Throughput: {result.avg_system_throughput_mbps:.2f} Mbps")

        print(f"\n{'UAV Metrics':^80}")
        print("-" * 80)
        header = f"{'UAV ID':<14} | {'Samples':>7} | {'Avg RSRP':>10} | {'Avg SINR':>9} | " \
                 f"{'Throughput':>10} | {'QoS Rate':>8} | {'HO':>3}"
        print(header)
        print("-" * 80)

        for m in result.uav_metrics:
            row = f"{m.uav_id:<14} | {m.total_samples:>7} | {m.avg_rsrp:>10.2f} | " \
                  f"{m.avg_sinr:>9.2f} | {m.avg_throughput_mbps:>10.2f} | " \
                  f"{m.qos_satisfaction_rate*100:>7.1f}% | {m.handover_count:>3}"
            print(row)

        print("=" * 80)


# =============================================================================
# Results Management
# =============================================================================

def save_results(results: List[ScenarioResult], output_dir: Path):
    """Save all results to files"""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\nSaving results to: {output_dir}")

    # Save individual scenario results
    for result in results:
        # Full JSON with all data
        json_path = output_dir / f"{result.scenario_name}_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(asdict(result), f, indent=2)
        print(f"  Saved: {json_path}")

    # Save comparison summary
    summary = {
        "timestamp": timestamp,
        "scenarios_compared": len(results),
        "scenarios": []
    }

    for result in results:
        scenario_summary = {
            "name": result.scenario_name,
            "description": result.description,
            "num_uavs": result.num_uavs,
            "total_samples": result.total_samples,
            "avg_prb_utilization": result.avg_prb_utilization,
            "peak_prb_utilization": result.peak_prb_utilization,
            "avg_system_throughput_mbps": result.avg_system_throughput_mbps,
            "total_interference_events": result.total_interference_events,
            "uav_summary": [
                {
                    "uav_id": m.uav_id,
                    "avg_rsrp": m.avg_rsrp,
                    "avg_throughput_mbps": m.avg_throughput_mbps,
                    "qos_satisfaction_rate": m.qos_satisfaction_rate,
                    "handover_count": m.handover_count
                }
                for m in result.uav_metrics
            ]
        }
        summary["scenarios"].append(scenario_summary)

    summary_path = output_dir / f"multi_uav_comparison_{timestamp}.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"  Saved summary: {summary_path}")

    # Save CSV summary
    csv_path = output_dir / f"multi_uav_summary_{timestamp}.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Scenario", "NumUAVs", "TotalSamples", "AvgPRBUtil", "PeakPRBUtil",
            "AvgSystemThroughput", "InterferenceEvents"
        ])
        for result in results:
            writer.writerow([
                result.scenario_name,
                result.num_uavs,
                result.total_samples,
                f"{result.avg_prb_utilization:.4f}",
                f"{result.peak_prb_utilization:.4f}",
                f"{result.avg_system_throughput_mbps:.2f}",
                result.total_interference_events
            ])
    print(f"  Saved CSV: {csv_path}")

    return summary_path


def print_comparison_table(results: List[ScenarioResult]):
    """Print performance comparison across all scenarios"""
    print("\n" + "=" * 100)
    print("MULTI-UAV SCENARIO PERFORMANCE COMPARISON")
    print("=" * 100)

    # Header
    print(f"\n{'Scenario':<20} | {'UAVs':>5} | {'Samples':>8} | {'PRB Util':>9} | "
          f"{'Peak PRB':>9} | {'Throughput':>11} | {'Interference':>12}")
    print("-" * 100)

    for r in results:
        print(f"{r.scenario_name:<20} | {r.num_uavs:>5} | {r.total_samples:>8} | "
              f"{r.avg_prb_utilization*100:>8.1f}% | {r.peak_prb_utilization*100:>8.1f}% | "
              f"{r.avg_system_throughput_mbps:>10.2f} | {r.total_interference_events:>12}")

    print("=" * 100)

    # Analysis
    print("\nKEY OBSERVATIONS:")
    print("-" * 50)

    if len(results) >= 2:
        # Compare 2-UAV vs 5-UAV scenarios if available
        two_uav = next((r for r in results if r.num_uavs == 2), None)
        five_uav = next((r for r in results if r.num_uavs == 5), None)

        if two_uav and five_uav:
            prb_increase = ((five_uav.avg_prb_utilization - two_uav.avg_prb_utilization)
                           / two_uav.avg_prb_utilization * 100) if two_uav.avg_prb_utilization > 0 else 0
            tput_change = ((five_uav.avg_system_throughput_mbps - two_uav.avg_system_throughput_mbps)
                          / two_uav.avg_system_throughput_mbps * 100) if two_uav.avg_system_throughput_mbps > 0 else 0

            print(f"  - PRB utilization increase (2->5 UAVs): {prb_increase:+.1f}%")
            print(f"  - Per-UAV throughput change: {tput_change:+.1f}%")
            print(f"  - Interference events (5 UAV): {five_uav.total_interference_events}")

    # QoS satisfaction analysis
    print("\nQoS SATISFACTION BY SCENARIO:")
    print("-" * 50)
    for r in results:
        avg_qos = statistics.mean([m.qos_satisfaction_rate for m in r.uav_metrics]) if r.uav_metrics else 0
        print(f"  {r.scenario_name}: {avg_qos*100:.1f}% average QoS satisfaction")

    print("=" * 100)


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Multi-UAV Scenario Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Scenarios:
  - 2uav_coordination: 2 UAVs with different trajectories, testing resource sharing
  - 3uav_formation:    3 UAVs in formation flight, centralized load
  - 5uav_dense:        5 UAVs testing resource competition and congestion

Examples:
  python multi_uav_simulation.py
  python multi_uav_simulation.py --scenarios 2uav_coordination 3uav_formation
  python multi_uav_simulation.py --csv /path/to/data.csv --verbose
        """
    )

    parser.add_argument(
        "--csv",
        default=DEFAULT_CSV_PATH,
        help=f"Path to ns-3 CSV output (default: {DEFAULT_CSV_PATH})"
    )
    parser.add_argument(
        "--output",
        default=str(RESULTS_DIR),
        help=f"Output directory for results (default: {RESULTS_DIR})"
    )
    parser.add_argument(
        "--scenarios",
        nargs="+",
        choices=list(SCENARIOS.keys()),
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
    parser.add_argument(
        "--xapp-url",
        default=XAPP_URL,
        help=f"xApp API URL (default: {XAPP_URL})"
    )

    args = parser.parse_args()

    # Verify CSV exists
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}")
        print("Please provide a valid CSV file path.")
        return 1

    # Initialize xApp client
    xapp_client = XAppClient(base_url=args.xapp_url)

    print("=" * 80)
    print("MULTI-UAV SCENARIO SIMULATION")
    print("=" * 80)
    print(f"CSV Input: {csv_path}")
    print(f"Output Dir: {args.output}")
    print(f"xApp URL: {args.xapp_url}")

    # Check xApp health
    print("\nChecking xApp connectivity...")
    if not xapp_client.check_health():
        print(f"WARNING: xApp is not running at {args.xapp_url}")
        print("Simulation will continue but decisions may fail.")
    else:
        print(f"xApp Status: HEALTHY")

    # Select scenarios
    scenarios_to_run = list(SCENARIOS.values())
    if args.scenarios:
        scenarios_to_run = [SCENARIOS[s] for s in args.scenarios]

    print(f"\nRunning {len(scenarios_to_run)} scenario(s)...")

    # Initialize simulator
    simulator = MultiUAVSimulator(
        csv_path=str(csv_path),
        xapp_client=xapp_client,
        verbose=args.verbose
    )

    # Run all scenarios
    results = []
    for scenario in scenarios_to_run:
        try:
            result = simulator.run_scenario(scenario)
            results.append(result)
        except Exception as e:
            print(f"ERROR running scenario {scenario.name}: {e}")
            import traceback
            traceback.print_exc()
            continue

    if not results:
        print("ERROR: No scenarios completed successfully")
        return 1

    # Print comparison
    print_comparison_table(results)

    # Save results
    if not args.no_save:
        output_dir = Path(args.output)
        summary_path = save_results(results, output_dir)
        print(f"\nResults saved to: {output_dir}")
        print(f"Summary file: {summary_path}")

    print("\nMulti-UAV simulation complete!")
    return 0


if __name__ == "__main__":
    exit(main())
