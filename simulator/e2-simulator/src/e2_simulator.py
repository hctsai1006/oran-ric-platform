#!/usr/bin/env python3
"""
E2 Simulator for O-RAN RIC Platform
作者: 蔡秀吉 (thc1006)
日期: 2025-11-15

Purpose: Generate realistic E2 traffic to test xApp metrics
"""

import json
import time
import random
import logging
import requests
from datetime import datetime
from typing import Dict, List
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class E2Simulator:
    """Simulates E2 Node sending indications to xApps"""

    def __init__(self):
        self.running = False
        self.config = {
            'xapps': {
                'kpimon': {
                    'host': 'kpimon.ricxapp.svc.cluster.local',
                    'port': 8081,  # Flask server port
                    'endpoint': '/e2/indication'
                },
                'traffic-steering': {
                    'host': 'traffic-steering.ricxapp.svc.cluster.local',
                    'port': 8081,
                    'endpoint': '/e2/indication'
                },
                'qoe-predictor': {
                    'host': 'qoe-predictor.ricxapp.svc.cluster.local',
                    'port': 8090,  # Flask health server
                    'endpoint': '/e2/indication'
                },
                'ran-control': {
                    'host': 'ran-control.ricxapp.svc.cluster.local',
                    'port': 8100,  # Flask health server
                    'endpoint': '/e2/indication'
                }
            },
            'cells': ['cell_001', 'cell_002', 'cell_003'],
            'ues': list(range(1, 21)),  # 20 UEs
            'interval': 5  # Send indications every 5 seconds
        }

    def generate_kpi_indication(self) -> Dict:
        """Generate E2SM-KPM indication with realistic KPI values"""
        cell_id = random.choice(self.config['cells'])
        ue_id = f"ue_{random.choice(self.config['ues']):03d}"

        # Generate realistic KPI values
        measurements = [
            {
                'name': 'DRB.PacketLossDl',
                'value': random.uniform(0.1, 5.0)  # 0.1% - 5%
            },
            {
                'name': 'DRB.PacketLossUl',
                'value': random.uniform(0.1, 5.0)
            },
            {
                'name': 'DRB.UEThpDl',
                'value': random.uniform(10.0, 100.0)  # 10-100 Mbps
            },
            {
                'name': 'DRB.UEThpUl',
                'value': random.uniform(5.0, 50.0)   # 5-50 Mbps
            },
            {
                'name': 'RRU.PrbUsedDl',
                'value': random.uniform(30.0, 85.0)  # 30-85% PRB usage
            },
            {
                'name': 'RRU.PrbUsedUl',
                'value': random.uniform(20.0, 70.0)
            },
            {
                'name': 'UE.RSRP',
                'value': random.uniform(-120.0, -80.0)  # -120 to -80 dBm
            },
            {
                'name': 'UE.RSRQ',
                'value': random.uniform(-15.0, -5.0)    # -15 to -5 dB
            },
            {
                'name': 'UE.SINR',
                'value': random.uniform(5.0, 25.0)      # 5-25 dB
            },
            {
                'name': 'RRC.ConnEstabSucc',
                'value': random.uniform(95.0, 99.9)     # 95-99.9% success rate
            }
        ]

        return {
            'timestamp': datetime.now().isoformat(),
            'cell_id': cell_id,
            'ue_id': ue_id,
            'measurements': measurements,
            'indication_sn': int(time.time() * 1000),
            'indication_type': 'report'
        }

    def generate_handover_event(self) -> Dict:
        """Generate handover event for Traffic Steering"""
        source_cell = random.choice(self.config['cells'])
        target_cell = random.choice([c for c in self.config['cells'] if c != source_cell])
        ue_id = f"ue_{random.choice(self.config['ues']):03d}"

        return {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'handover_request',
            'ue_id': ue_id,
            'source_cell': source_cell,
            'target_cell': target_cell,
            'rsrp': random.uniform(-120.0, -80.0),
            'rsrq': random.uniform(-15.0, -5.0),
            'trigger': 'A3_event'  # Coverage-based handover
        }

    def generate_qoe_metrics(self) -> Dict:
        """Generate QoE metrics"""
        ue_id = f"ue_{random.choice(self.config['ues']):03d}"

        # Generate QoE metrics
        video_bitrate = random.uniform(2.0, 10.0)  # Mbps
        packet_loss = random.uniform(0.0, 2.0)     # %
        latency = random.uniform(10.0, 100.0)      # ms
        jitter = random.uniform(1.0, 20.0)         # ms

        # Calculate QoE score (0-100)
        qoe_score = 100.0
        qoe_score -= packet_loss * 5.0  # Penalize packet loss
        qoe_score -= max(0, (latency - 50.0) / 2.0)  # Penalize high latency
        qoe_score -= jitter * 2.0  # Penalize jitter
        qoe_score = max(0.0, min(100.0, qoe_score))

        return {
            'timestamp': datetime.now().isoformat(),
            'ue_id': ue_id,
            'cell_id': random.choice(self.config['cells']),
            'metrics': {
                'video_bitrate_mbps': video_bitrate,
                'packet_loss_percent': packet_loss,
                'latency_ms': latency,
                'jitter_ms': jitter,
                'qoe_score': qoe_score
            }
        }

    def generate_control_event(self) -> Dict:
        """Generate control event for RC xApp"""
        return {
            'timestamp': datetime.now().isoformat(),
            'cell_id': random.choice(self.config['cells']),
            'event_type': random.choice(['load_balancing', 'interference_mitigation', 'power_control']),
            'trigger_condition': {
                'prb_usage': random.uniform(70.0, 95.0),
                'active_ues': random.randint(10, 50)
            }
        }

    def send_to_xapp(self, xapp_name: str, data: Dict) -> bool:
        """Send indication to xApp via HTTP"""
        try:
            xapp_config = self.config['xapps'].get(xapp_name)
            if not xapp_config:
                logger.error(f"Unknown xApp: {xapp_name}")
                return False

            # In Kubernetes, use service name
            url = f"http://{xapp_config['host']}:{xapp_config['port']}{xapp_config['endpoint']}"

            response = requests.post(
                url,
                json=data,
                timeout=5,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                logger.debug(f"Successfully sent data to {xapp_name}")
                return True
            else:
                logger.warning(f"Failed to send to {xapp_name}: HTTP {response.status_code}")
                return False

        except requests.exceptions.ConnectionError:
            logger.debug(f"Connection error for {xapp_name} (xApp may not have REST endpoint yet)")
            return False
        except Exception as e:
            logger.error(f"Error sending to {xapp_name}: {e}")
            return False

    def simulation_loop(self):
        """Main simulation loop"""
        logger.info("Starting E2 Simulator...")

        iteration = 0
        while self.running:
            iteration += 1
            logger.info(f"=== Simulation Iteration {iteration} ===")

            # Generate and send KPI indications to KPIMON
            kpi_data = self.generate_kpi_indication()
            self.send_to_xapp('kpimon', kpi_data)
            logger.info(f"Generated KPI indication for {kpi_data['cell_id']}/{kpi_data['ue_id']}")

            # Randomly trigger handover events (30% chance)
            if random.random() < 0.3:
                ho_event = self.generate_handover_event()
                self.send_to_xapp('traffic-steering', ho_event)
                logger.info(f"Generated handover event: {ho_event['source_cell']} -> {ho_event['target_cell']}")

            # Generate QoE metrics
            qoe_data = self.generate_qoe_metrics()
            self.send_to_xapp('qoe-predictor', qoe_data)
            logger.info(f"Generated QoE metrics for {qoe_data['ue_id']}: QoE={qoe_data['metrics']['qoe_score']:.1f}")

            # Randomly trigger control events (20% chance)
            if random.random() < 0.2:
                control_event = self.generate_control_event()
                self.send_to_xapp('ran-control', control_event)
                logger.info(f"Generated control event: {control_event['event_type']}")

            logger.info(f"Waiting {self.config['interval']} seconds...")
            time.sleep(self.config['interval'])

    def start(self):
        """Start the simulator"""
        self.running = True

        logger.info("="*60)
        logger.info("E2 Simulator for O-RAN RIC Platform")
        logger.info("作者: 蔡秀吉 (thc1006)")
        logger.info("="*60)
        logger.info(f"Configuration:")
        logger.info(f"  - Cells: {self.config['cells']}")
        logger.info(f"  - UEs: {len(self.config['ues'])}")
        logger.info(f"  - Interval: {self.config['interval']}s")
        logger.info(f"  - Target xApps: {', '.join(self.config['xapps'].keys())}")
        logger.info("="*60)

        # Start simulation in separate thread
        sim_thread = threading.Thread(target=self.simulation_loop)
        sim_thread.daemon = True
        sim_thread.start()

        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down E2 Simulator...")
            self.running = False
            time.sleep(2)
            logger.info("E2 Simulator stopped")


if __name__ == '__main__':
    simulator = E2Simulator()
    simulator.start()
