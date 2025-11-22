#!/usr/bin/env python3
"""
TRACTOR Dataset Processor for O-RAN xApp Validation

This script processes the TRACTOR (Traffic Collection for Analysis and Training
in O-RAN) dataset to extract KPM metrics and validate xApp handover decisions
against real-world O-RAN deployment data.

Dataset source: https://dataverse.harvard.edu/dataverse/tractor
"""

import os
import sys
import csv
import json
import glob
import zipfile
import requests
import logging
import argparse
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
TRACTOR_DATA_DIR = "/home/thc1006/dev/tractor-data"
DATASET_ZIP_DIR = "/home/thc1006/dev/dataset"
OUTPUT_DIR = "/home/thc1006/dev/oran-ric-platform/ns3-uav-simulation/results/tractor"
XAPP_URL = "http://localhost:5000"


@dataclass
class UEMetrics:
    """UE-level KPM metrics from TRACTOR dataset"""
    timestamp: float
    ue_id: str
    pci: int
    earfcn: int
    rsrp: float
    pathloss: float
    cfo: float
    dl_mcs: float
    dl_snr: float
    dl_brate: float
    dl_bler: float
    ul_mcs: float
    ul_brate: float
    ul_bler: float
    is_attached: bool


@dataclass
class BSMetrics:
    """Base station level KPM metrics from TRACTOR dataset"""
    timestamp: int
    num_ues: int
    imsi: str
    rnti: int
    slicing_enabled: bool
    slice_id: int
    slice_prb: int
    scheduling_policy: int
    dl_mcs: float
    tx_brate_dl_mbps: float
    tx_pkts_dl: int
    tx_errors_dl_pct: float
    dl_cqi: float
    ul_mcs: float
    rx_brate_ul_mbps: float
    rx_pkts_ul: int
    rx_errors_ul_pct: float
    ul_rssi: float
    ul_sinr: float
    phr: float


@dataclass
class ENBMetrics:
    """eNB aggregate metrics from TRACTOR dataset"""
    timestamp: int
    num_ues: int
    dl_brate: float
    ul_brate: float


@dataclass
class MgenFlow:
    """Traffic flow metrics from MGEN"""
    recv_time: float
    send_time: float
    latency_ms: float
    flow_id: int
    seq_no: int
    payload_size: int


class TractorDataDiscovery:
    """Discover and catalog available TRACTOR data"""

    def __init__(self, data_dir: str = TRACTOR_DATA_DIR, zip_dir: str = DATASET_ZIP_DIR):
        self.data_dir = Path(data_dir)
        self.zip_dir = Path(zip_dir)

    def scan_extracted_data(self) -> Dict:
        """Scan for extracted TRACTOR data"""
        result = {
            "kpm_dir": None,
            "logs_dir": None,
            "clusters": [],
            "reservations": [],
            "ue_metrics_files": [],
            "bs_metrics_files": [],
            "enb_metrics_files": [],
            "mgen_files": [],
            "total_csv_files": 0,
            "total_size_mb": 0
        }

        if not self.data_dir.exists():
            logger.warning(f"Data directory not found: {self.data_dir}")
            return result

        # Check for KPM and logs directories
        kpm_dir = self.data_dir / "kpm"
        logs_dir = self.data_dir / "logs"

        if kpm_dir.exists():
            result["kpm_dir"] = str(kpm_dir)
        if logs_dir.exists():
            result["logs_dir"] = str(logs_dir)

        # Find all CSV files
        csv_files = list(self.data_dir.rglob("*.csv"))
        result["total_csv_files"] = len(csv_files)

        # Calculate total size
        total_size = sum(f.stat().st_size for f in csv_files if f.exists())
        result["total_size_mb"] = round(total_size / (1024 * 1024), 2)

        # Categorize files
        clusters = set()
        reservations = set()

        for csv_file in csv_files:
            parts = csv_file.parts

            # Extract cluster and reservation info from path
            for i, part in enumerate(parts):
                if part.startswith("cluster_"):
                    clusters.add(part)
                if part.startswith("RESERVATION-"):
                    reservations.add(part)

            # Categorize by file type
            filename = csv_file.name
            if filename == "ue_metrics.csv":
                result["ue_metrics_files"].append(str(csv_file))
            elif filename == "enb_metrics.csv":
                result["enb_metrics_files"].append(str(csv_file))
            elif filename.endswith("_metrics.csv") and "bs" in str(csv_file):
                result["bs_metrics_files"].append(str(csv_file))
            elif filename == "mgen.csv":
                result["mgen_files"].append(str(csv_file))

        result["clusters"] = sorted(list(clusters))
        result["reservations"] = sorted(list(reservations))

        return result

    def scan_zip_files(self) -> Dict:
        """Scan for available ZIP archives"""
        result = {
            "zip_files": [],
            "total_size_gb": 0
        }

        if not self.zip_dir.exists():
            logger.warning(f"ZIP directory not found: {self.zip_dir}")
            return result

        zip_files = list(self.zip_dir.glob("*.zip"))
        total_size = 0

        for zf in zip_files:
            size_gb = zf.stat().st_size / (1024 ** 3)
            total_size += size_gb
            result["zip_files"].append({
                "name": zf.name,
                "path": str(zf),
                "size_gb": round(size_gb, 2)
            })

        result["total_size_gb"] = round(total_size, 2)
        return result

    def generate_summary(self) -> Dict:
        """Generate complete data discovery summary"""
        extracted = self.scan_extracted_data()
        zipped = self.scan_zip_files()

        return {
            "discovery_time": datetime.now().isoformat(),
            "extracted_data": extracted,
            "zip_archives": zipped,
            "data_availability": {
                "has_extracted_kpm": extracted["kpm_dir"] is not None,
                "has_extracted_logs": extracted["logs_dir"] is not None,
                "has_zip_archives": len(zipped["zip_files"]) > 0,
                "ue_metrics_count": len(extracted["ue_metrics_files"]),
                "bs_metrics_count": len(extracted["bs_metrics_files"]),
                "mgen_flow_count": len(extracted["mgen_files"])
            }
        }


class TractorDataProcessor:
    """Process TRACTOR KPM data for xApp validation"""

    def __init__(self, data_dir: str = TRACTOR_DATA_DIR):
        self.data_dir = Path(data_dir)
        self.kpm_dir = self.data_dir / "kpm"

    def parse_ue_metrics(self, file_path: str, limit: int = None) -> List[UEMetrics]:
        """Parse UE metrics CSV file (semicolon separated)"""
        metrics = []

        try:
            with open(file_path, 'r') as f:
                # UE metrics use semicolon separator
                reader = csv.DictReader(f, delimiter=';')

                for i, row in enumerate(reader):
                    if limit and i >= limit:
                        break

                    try:
                        metric = UEMetrics(
                            timestamp=float(row.get('time', 0)),
                            ue_id=os.path.basename(os.path.dirname(file_path)),
                            pci=int(float(row.get('pci', 0))),
                            earfcn=int(float(row.get('earfcn', 0))),
                            rsrp=float(row.get('rsrp', 0)),
                            pathloss=float(row.get('pl', 0)),
                            cfo=float(row.get('cfo', 0)),
                            dl_mcs=float(row.get('dl_mcs', 0)),
                            dl_snr=float(row.get('dl_snr', 0)),
                            dl_brate=float(row.get('dl_brate', 0)),
                            dl_bler=float(row.get('dl_bler', 0)),
                            ul_mcs=float(row.get('ul_mcs', 0)),
                            ul_brate=float(row.get('ul_brate', 0)),
                            ul_bler=float(row.get('ul_bler', 0)),
                            is_attached=float(row.get('is_attached', 0)) == 1.0
                        )
                        metrics.append(metric)
                    except (ValueError, KeyError) as e:
                        logger.debug(f"Skipping row due to parse error: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error parsing UE metrics from {file_path}: {e}")

        return metrics

    def parse_bs_metrics(self, file_path: str, limit: int = None) -> List[BSMetrics]:
        """Parse BS metrics CSV file (comma separated)"""
        metrics = []

        try:
            with open(file_path, 'r') as f:
                reader = csv.DictReader(f)

                for i, row in enumerate(reader):
                    if limit and i >= limit:
                        break

                    try:
                        metric = BSMetrics(
                            timestamp=int(row.get('Timestamp', 0)),
                            num_ues=int(row.get('num_ues', 0)),
                            imsi=row.get('IMSI', ''),
                            rnti=int(row.get('RNTI', 0)),
                            slicing_enabled=row.get('slicing_enabled', '0') == '1',
                            slice_id=int(row.get('slice_id', 0)),
                            slice_prb=int(row.get('slice_prb', 0)),
                            scheduling_policy=int(row.get('scheduling_policy', 0)),
                            dl_mcs=float(row.get('dl_mcs', 0)),
                            tx_brate_dl_mbps=float(row.get('tx_brate downlink [Mbps]', 0)),
                            tx_pkts_dl=int(float(row.get('tx_pkts downlink', 0))),
                            tx_errors_dl_pct=float(row.get('tx_errors downlink (%)', 0)),
                            dl_cqi=float(row.get('dl_cqi', 0)),
                            ul_mcs=float(row.get('ul_mcs', 0)),
                            rx_brate_ul_mbps=float(row.get('rx_brate uplink [Mbps]', 0)),
                            rx_pkts_ul=int(float(row.get('rx_pkts uplink', 0))),
                            rx_errors_ul_pct=float(row.get('rx_errors uplink (%)', 0)),
                            ul_rssi=float(row.get('ul_rssi', 0)),
                            ul_sinr=float(row.get('ul_sinr', 0)),
                            phr=float(row.get('phr', 0))
                        )
                        metrics.append(metric)
                    except (ValueError, KeyError) as e:
                        logger.debug(f"Skipping row due to parse error: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error parsing BS metrics from {file_path}: {e}")

        return metrics

    def parse_enb_metrics(self, file_path: str, limit: int = None) -> List[ENBMetrics]:
        """Parse eNB aggregate metrics CSV file"""
        metrics = []

        try:
            with open(file_path, 'r') as f:
                reader = csv.DictReader(f)

                for i, row in enumerate(reader):
                    if limit and i >= limit:
                        break

                    try:
                        metric = ENBMetrics(
                            timestamp=int(row.get('time', 0)),
                            num_ues=int(row.get('nof_ue', 0)),
                            dl_brate=float(row.get('dl_brate', 0)),
                            ul_brate=float(row.get('ul_brate', 0))
                        )
                        metrics.append(metric)
                    except (ValueError, KeyError) as e:
                        logger.debug(f"Skipping row due to parse error: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error parsing eNB metrics from {file_path}: {e}")

        return metrics

    def parse_mgen_flow(self, file_path: str, limit: int = None) -> List[MgenFlow]:
        """Parse MGEN traffic flow CSV file"""
        flows = []

        try:
            with open(file_path, 'r') as f:
                reader = csv.DictReader(f)

                for i, row in enumerate(reader):
                    if limit and i >= limit:
                        break

                    try:
                        recv_time = float(row.get('Received Time', 0))
                        send_time = float(row.get('Sent Time', 0))

                        flow = MgenFlow(
                            recv_time=recv_time,
                            send_time=send_time,
                            latency_ms=(recv_time - send_time) * 1000,
                            flow_id=int(row.get('Flow ID', 0)),
                            seq_no=int(row.get('Sequence No.', 0)),
                            payload_size=int(row.get('Protocol Payload Size', 0))
                        )
                        flows.append(flow)
                    except (ValueError, KeyError) as e:
                        logger.debug(f"Skipping row due to parse error: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error parsing MGEN flow from {file_path}: {e}")

        return flows

    def convert_to_ns3_format(self, ue_metrics: List[UEMetrics]) -> List[Dict]:
        """Convert TRACTOR UE metrics to ns-3 compatible format"""
        ns3_data = []

        for m in ue_metrics:
            # Skip non-attached or invalid measurements
            if not m.is_attached or m.rsrp == 0:
                continue

            ns3_record = {
                "time": m.timestamp / 1000.0,  # Convert ms to seconds
                "cell_id": m.pci,
                "rsrp_dbm": m.rsrp,
                "rsrq_db": m.dl_snr,  # Use SNR as RSRQ proxy
                "sinr_db": m.dl_snr,
                "ue_id": m.ue_id,
                "dl_throughput_bps": m.dl_brate,
                "ul_throughput_bps": m.ul_brate,
                "dl_mcs": m.dl_mcs,
                "ul_mcs": m.ul_mcs,
                "earfcn": m.earfcn,
                "source": "tractor"
            }
            ns3_data.append(ns3_record)

        return ns3_data

    def compute_statistics(self, ue_metrics: List[UEMetrics]) -> Dict:
        """Compute statistics from UE metrics"""
        if not ue_metrics:
            return {}

        # Filter valid measurements
        valid = [m for m in ue_metrics if m.is_attached and m.rsrp != 0]

        if not valid:
            return {"error": "No valid measurements found"}

        rsrp_values = [m.rsrp for m in valid]
        snr_values = [m.dl_snr for m in valid]
        dl_brate_values = [m.dl_brate for m in valid]
        ul_brate_values = [m.ul_brate for m in valid]

        def safe_stats(values):
            if not values:
                return {"min": 0, "max": 0, "avg": 0, "count": 0}
            return {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "count": len(values)
            }

        return {
            "rsrp": safe_stats(rsrp_values),
            "snr": safe_stats(snr_values),
            "dl_throughput_bps": safe_stats(dl_brate_values),
            "ul_throughput_bps": safe_stats(ul_brate_values),
            "total_samples": len(ue_metrics),
            "valid_samples": len(valid),
            "attached_ratio": len(valid) / len(ue_metrics) if ue_metrics else 0
        }


class XAppValidator:
    """Validate xApp decisions using TRACTOR data"""

    def __init__(self, xapp_url: str = XAPP_URL):
        self.xapp_url = xapp_url
        self.results = []

    def check_health(self) -> bool:
        """Check if xApp is running"""
        try:
            resp = requests.get(f"{self.xapp_url}/health", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def send_indication(self, ue_id: str, cell_id: int, rsrp: float,
                       sinr: float, timestamp: float) -> Optional[Dict]:
        """Send E2 indication to xApp and get decision"""
        payload = {
            "uav_id": ue_id,
            "position": {"x": 100, "y": 100, "z": 50},  # Default position
            "path_position": 0.5,
            "slice_id": "embb",
            "radio_snapshot": {
                "serving_cell_id": str(cell_id),
                "neighbor_cell_ids": ["1", "2", "3"],
                "rsrp_serving": rsrp,
                "rsrp_best_neighbor": rsrp - 6,  # Assume 6 dB difference
                "prb_utilization_serving": 0.5,
                "prb_utilization_slice": 0.3
            }
        }

        try:
            resp = requests.post(
                f"{self.xapp_url}/e2/indication",
                json=payload,
                timeout=5
            )
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"error": resp.text, "status_code": resp.status_code}
        except Exception as e:
            return {"error": str(e)}

    def validate_with_tractor_data(self, ns3_format_data: List[Dict],
                                    sample_interval: float = 1.0) -> Dict:
        """Validate xApp using TRACTOR data converted to ns-3 format"""

        if not self.check_health():
            logger.warning("xApp is not available, skipping validation")
            return {"error": "xApp not available", "validated": False}

        results = {
            "start_time": datetime.now().isoformat(),
            "total_samples": 0,
            "xapp_decisions": [],
            "handover_recommendations": 0,
            "maintain_decisions": 0,
            "avg_rsrp": 0,
            "decision_distribution": defaultdict(int)
        }

        last_time = -sample_interval
        rsrp_sum = 0
        sample_count = 0

        for record in ns3_format_data:
            sim_time = record["time"]

            # Sample at interval
            if sim_time - last_time < sample_interval:
                continue

            last_time = sim_time
            cell_id = record["cell_id"]
            rsrp = record["rsrp_dbm"]
            sinr = record["sinr_db"]
            ue_id = record.get("ue_id", "tractor-ue")

            decision = self.send_indication(ue_id, cell_id, rsrp, sinr, sim_time)

            if decision and "error" not in decision:
                target_cell = decision.get("target_cell_id", str(cell_id))
                action = "HANDOVER" if target_cell != str(cell_id) else "MAINTAIN"

                if action == "HANDOVER":
                    results["handover_recommendations"] += 1
                else:
                    results["maintain_decisions"] += 1

                results["decision_distribution"][action] += 1
                results["xapp_decisions"].append({
                    "time": sim_time,
                    "cell_id": cell_id,
                    "rsrp": rsrp,
                    "sinr": sinr,
                    "action": action,
                    "prb_quota": decision.get("prb_quota", "N/A")
                })

            rsrp_sum += rsrp
            sample_count += 1

        results["total_samples"] = sample_count
        results["avg_rsrp"] = rsrp_sum / sample_count if sample_count > 0 else 0
        results["end_time"] = datetime.now().isoformat()
        results["decision_distribution"] = dict(results["decision_distribution"])

        return results


def run_data_discovery():
    """Run data discovery and print summary"""
    print("=" * 70)
    print("TRACTOR Dataset Discovery")
    print("=" * 70)

    discovery = TractorDataDiscovery()
    summary = discovery.generate_summary()

    print(f"\nDiscovery Time: {summary['discovery_time']}")

    # Extracted data
    extracted = summary["extracted_data"]
    print(f"\n[Extracted Data]")
    print(f"  KPM Directory: {extracted['kpm_dir'] or 'Not found'}")
    print(f"  Logs Directory: {extracted['logs_dir'] or 'Not found'}")
    print(f"  Total CSV Files: {extracted['total_csv_files']}")
    print(f"  Total Size: {extracted['total_size_mb']} MB")
    print(f"  Clusters: {', '.join(extracted['clusters']) or 'None'}")
    print(f"  Reservations: {len(extracted['reservations'])} found")

    # File counts
    print(f"\n[File Counts]")
    print(f"  UE Metrics Files: {len(extracted['ue_metrics_files'])}")
    print(f"  BS Metrics Files: {len(extracted['bs_metrics_files'])}")
    print(f"  eNB Metrics Files: {len(extracted['enb_metrics_files'])}")
    print(f"  MGEN Flow Files: {len(extracted['mgen_files'])}")

    # ZIP archives
    zipped = summary["zip_archives"]
    print(f"\n[ZIP Archives]")
    print(f"  Total Archives: {len(zipped['zip_files'])}")
    print(f"  Total Size: {zipped['total_size_gb']} GB")
    for zf in zipped["zip_files"]:
        print(f"    - {zf['name']}: {zf['size_gb']} GB")

    print("=" * 70)

    return summary


def run_sample_processing(limit: int = 1000):
    """Process sample TRACTOR data"""
    print("\n" + "=" * 70)
    print("TRACTOR Sample Data Processing")
    print("=" * 70)

    processor = TractorDataProcessor()
    discovery = TractorDataDiscovery()
    summary = discovery.generate_summary()

    results = {
        "processing_time": datetime.now().isoformat(),
        "sample_limit": limit,
        "ue_metrics": [],
        "bs_metrics": [],
        "enb_metrics": [],
        "ns3_format_data": [],
        "statistics": {}
    }

    # Process UE metrics
    ue_files = summary["extracted_data"]["ue_metrics_files"]
    if ue_files:
        print(f"\nProcessing UE metrics from: {ue_files[0]}")
        ue_metrics = processor.parse_ue_metrics(ue_files[0], limit=limit)
        results["ue_metrics_count"] = len(ue_metrics)

        # Convert to ns-3 format
        ns3_data = processor.convert_to_ns3_format(ue_metrics)
        results["ns3_format_count"] = len(ns3_data)
        results["ns3_format_data"] = ns3_data[:100]  # Keep first 100 for results

        # Compute statistics
        stats = processor.compute_statistics(ue_metrics)
        results["statistics"]["ue"] = stats

        print(f"  Parsed {len(ue_metrics)} records")
        print(f"  Valid attached records: {stats.get('valid_samples', 0)}")
        if "rsrp" in stats:
            print(f"  RSRP range: {stats['rsrp']['min']:.1f} to {stats['rsrp']['max']:.1f} dBm")
            print(f"  Average RSRP: {stats['rsrp']['avg']:.2f} dBm")
        if "dl_throughput_bps" in stats:
            avg_mbps = stats['dl_throughput_bps']['avg'] / 1e6
            print(f"  Average DL throughput: {avg_mbps:.2f} Mbps")

    # Process BS metrics
    bs_files = summary["extracted_data"]["bs_metrics_files"]
    if bs_files:
        print(f"\nProcessing BS metrics from: {bs_files[0]}")
        bs_metrics = processor.parse_bs_metrics(bs_files[0], limit=limit)
        results["bs_metrics_count"] = len(bs_metrics)

        if bs_metrics:
            # Compute BS statistics
            sinr_values = [m.ul_sinr for m in bs_metrics if m.ul_sinr > 0]
            cqi_values = [m.dl_cqi for m in bs_metrics if m.dl_cqi > 0]

            results["statistics"]["bs"] = {
                "total_samples": len(bs_metrics),
                "avg_ul_sinr": sum(sinr_values) / len(sinr_values) if sinr_values else 0,
                "avg_dl_cqi": sum(cqi_values) / len(cqi_values) if cqi_values else 0,
                "unique_ues": len(set(m.imsi for m in bs_metrics))
            }

            print(f"  Parsed {len(bs_metrics)} records")
            print(f"  Unique UEs: {results['statistics']['bs']['unique_ues']}")
            print(f"  Average UL SINR: {results['statistics']['bs']['avg_ul_sinr']:.2f} dB")

    # Process eNB metrics
    enb_files = summary["extracted_data"]["enb_metrics_files"]
    if enb_files:
        print(f"\nProcessing eNB metrics from: {enb_files[0]}")
        enb_metrics = processor.parse_enb_metrics(enb_files[0], limit=limit)
        results["enb_metrics_count"] = len(enb_metrics)

        if enb_metrics:
            active = [m for m in enb_metrics if m.num_ues > 0]
            results["statistics"]["enb"] = {
                "total_samples": len(enb_metrics),
                "active_samples": len(active),
                "max_concurrent_ues": max(m.num_ues for m in enb_metrics) if enb_metrics else 0
            }

            print(f"  Parsed {len(enb_metrics)} records")
            print(f"  Max concurrent UEs: {results['statistics']['enb']['max_concurrent_ues']}")

    print("=" * 70)

    return results


def run_xapp_validation(ns3_data: List[Dict], sample_interval: float = 1.0):
    """Validate xApp with TRACTOR data"""
    print("\n" + "=" * 70)
    print("xApp Validation with TRACTOR Data")
    print("=" * 70)

    validator = XAppValidator()

    if not validator.check_health():
        print("\nWARNING: xApp is not running at", XAPP_URL)
        print("Please start the xApp to enable validation.")
        return {"error": "xApp not available", "validated": False}

    print(f"\nxApp Status: HEALTHY")
    print(f"Sample Interval: {sample_interval}s")
    print(f"Total Records: {len(ns3_data)}")

    results = validator.validate_with_tractor_data(ns3_data, sample_interval)

    print(f"\n[Validation Results]")
    print(f"  Total Samples Sent: {results['total_samples']}")
    print(f"  Average RSRP: {results['avg_rsrp']:.2f} dBm")
    print(f"  Handover Recommendations: {results['handover_recommendations']}")
    print(f"  Maintain Decisions: {results['maintain_decisions']}")

    if results["xapp_decisions"]:
        print(f"\n[Sample Decisions]")
        for d in results["xapp_decisions"][:5]:
            print(f"    t={d['time']:.2f}s | Cell={d['cell_id']} | "
                  f"RSRP={d['rsrp']:.1f} dBm | Action={d['action']}")

    print("=" * 70)

    return results


def compare_with_simulation(tractor_stats: Dict, sim_data_path: str = None):
    """Compare TRACTOR data statistics with simulation data"""
    print("\n" + "=" * 70)
    print("TRACTOR vs Simulation Data Comparison")
    print("=" * 70)

    comparison = {
        "tractor": tractor_stats,
        "simulation": None,
        "comparison": {}
    }

    # Try to load simulation data
    if sim_data_path and Path(sim_data_path).exists():
        try:
            with open(sim_data_path, 'r') as f:
                sim_data = json.load(f)
            comparison["simulation"] = sim_data
        except Exception as e:
            logger.warning(f"Could not load simulation data: {e}")

    # Generate comparison metrics
    if "ue" in tractor_stats:
        ue_stats = tractor_stats["ue"]
        print("\n[TRACTOR UE Metrics]")
        print(f"  RSRP: {ue_stats.get('rsrp', {}).get('avg', 0):.2f} dBm "
              f"(range: {ue_stats.get('rsrp', {}).get('min', 0):.1f} to "
              f"{ue_stats.get('rsrp', {}).get('max', 0):.1f})")
        print(f"  Valid samples: {ue_stats.get('valid_samples', 0)}")

        # Typical ns-3 LTE simulation ranges for comparison
        print("\n[Typical ns-3 LTE Simulation Ranges]")
        print("  RSRP: -100 to -60 dBm (urban macro)")
        print("  SINR: 0 to 30 dB")

        comparison["comparison"]["rsrp_in_realistic_range"] = (
            -120 <= ue_stats.get("rsrp", {}).get("avg", -999) <= -40
        )

    print("=" * 70)

    return comparison


def save_results(results: Dict, filename: str):
    """Save results to JSON file"""
    output_path = Path(OUTPUT_DIR) / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"Results saved to: {output_path}")
    return str(output_path)


def export_ns3_csv(ns3_data: List[Dict], filename: str):
    """Export ns-3 format data to CSV"""
    output_path = Path(OUTPUT_DIR) / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not ns3_data:
        logger.warning("No data to export")
        return None

    fieldnames = ["time", "cell_id", "rsrp_dbm", "rsrq_db", "sinr_db",
                  "ue_id", "dl_throughput_bps", "ul_throughput_bps"]

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(ns3_data)

    logger.info(f"CSV exported to: {output_path}")
    return str(output_path)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="TRACTOR Dataset Processor for O-RAN xApp Validation"
    )
    parser.add_argument(
        "--discover", action="store_true",
        help="Run data discovery only"
    )
    parser.add_argument(
        "--process", action="store_true",
        help="Process sample data"
    )
    parser.add_argument(
        "--validate", action="store_true",
        help="Validate xApp with TRACTOR data"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Run all operations"
    )
    parser.add_argument(
        "--limit", type=int, default=1000,
        help="Sample limit for processing (default: 1000)"
    )
    parser.add_argument(
        "--interval", type=float, default=1.0,
        help="xApp validation sample interval in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--output-dir", type=str, default=OUTPUT_DIR,
        help=f"Output directory (default: {OUTPUT_DIR})"
    )

    args = parser.parse_args()

    # Update output directory if specified
    output_dir = args.output_dir

    # Default to --all if no specific action
    if not any([args.discover, args.process, args.validate, args.all]):
        args.all = True

    all_results = {
        "run_time": datetime.now().isoformat(),
        "config": {
            "limit": args.limit,
            "interval": args.interval,
            "output_dir": output_dir
        }
    }

    # Step 1: Data Discovery
    if args.discover or args.all:
        discovery_results = run_data_discovery()
        all_results["discovery"] = discovery_results
        save_results(discovery_results, "discovery_summary.json")

    # Step 2: Sample Processing
    ns3_data = []
    if args.process or args.all:
        processing_results = run_sample_processing(limit=args.limit)
        all_results["processing"] = processing_results
        ns3_data = processing_results.get("ns3_format_data", [])

        # Export ns-3 format CSV
        if ns3_data:
            export_ns3_csv(ns3_data, "tractor_ns3_format.csv")

        save_results(processing_results, "processing_results.json")

    # Step 3: xApp Validation
    if args.validate or args.all:
        # Use processed data or load from previous run
        if not ns3_data:
            ns3_csv_path = Path(output_dir) / "tractor_ns3_format.csv"
            if ns3_csv_path.exists():
                with open(ns3_csv_path, 'r') as f:
                    reader = csv.DictReader(f)
                    ns3_data = [
                        {k: float(v) if k != "ue_id" else v
                         for k, v in row.items()}
                        for row in reader
                    ]

        if ns3_data:
            validation_results = run_xapp_validation(ns3_data, args.interval)
            all_results["validation"] = validation_results
            save_results(validation_results, "xapp_validation.json")
        else:
            print("\nNo ns-3 format data available for validation.")
            print("Run with --process first to generate data.")

    # Step 4: Comparison
    if args.all and "processing" in all_results:
        stats = all_results["processing"].get("statistics", {})
        comparison_results = compare_with_simulation(stats)
        all_results["comparison"] = comparison_results
        save_results(comparison_results, "comparison_results.json")

    # Save complete results
    save_results(all_results, "complete_results.json")

    print(f"\n[Output Files]")
    print(f"  Results saved to: {output_dir}")

    return all_results


if __name__ == "__main__":
    main()
