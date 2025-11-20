#!/usr/bin/env python3
"""
Traffic Steering xApp - O-RAN SC Release J
Implements policy-based handover decisions with dual-path redundancy (RMR + HTTP)
"""

import sys
import os
import json
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from threading import Thread
from flask import Flask, jsonify, Response, request

# Add common library path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../common'))

from ricxappframe.xapp_frame import rmr
from ricxappframe.xapp_sdl import SDLWrapper
from mdclogpy import Logger
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Import dual-path messenger
from dual_path_messenger import DualPathMessenger, EndpointConfig, CommunicationPath

# Configure logging
logger = Logger(name="traffic_steering_xapp")
logger.set_level(logging.INFO)

# RMR Message Types
RIC_SUB_REQ = 12010
RIC_SUB_RESP = 12011
RIC_SUB_DEL_REQ = 12012
RIC_INDICATION = 12050
RIC_CONTROL_REQ = 12040
RIC_CONTROL_RESP = 12041
A1_POLICY_REQ = 20010
A1_POLICY_RESP = 20011

# E2SM Service Model IDs
E2SM_KPM_ID = 0
E2SM_RC_ID = 1

# Prometheus Metrics
ts_handover_decisions_total = Counter(
    'ts_handover_decisions_total',
    'Total number of handover decisions evaluated'
)
ts_handover_triggered_total = Counter(
    'ts_handover_triggered_total',
    'Total number of handovers triggered'
)
ts_active_ues = Gauge(
    'ts_active_ues',
    'Current number of active UEs being monitored'
)
ts_policy_updates_total = Counter(
    'ts_policy_updates_total',
    'Total number of A1 policy updates received'
)
ts_e2_indications_received_total = Counter(
    'ts_e2_indications_received_total',
    'Total number of E2 indications received'
)

@dataclass
class UEMetrics:
    """UE performance metrics from E2SM-KPM"""
    ue_id: str
    serving_cell: str
    rsrp: float  # Reference Signal Received Power
    rsrq: float  # Reference Signal Received Quality
    dl_throughput: float  # Downlink throughput (Mbps)
    ul_throughput: float  # Uplink throughput (Mbps)
    timestamp: float

@dataclass
class HandoverPolicy:
    """A1 policy for handover thresholds"""
    policy_id: str
    rsrp_threshold: float = -100.0  # dBm
    throughput_threshold: float = 10.0  # Mbps
    load_threshold: float = 0.8  # 80% cell load
    enabled: bool = True

class TrafficSteeringXapp:
    """
    Traffic Steering xApp implementation - O-RAN SC Release J
    Features:
    - Dual-path communication (RMR primary, HTTP fallback)
    - Automatic failover and recovery
    - Comprehensive monitoring and logging
    """

    def __init__(self, config_path: str = "/app/config/config.json"):
        """Initialize xApp"""
        self.config = self._load_config(config_path)
        self.running = False

        # Initialize dual-path messenger
        self.messenger = DualPathMessenger(
            xapp_name="traffic-steering",
            rmr_port=self.config.get('rmr_port', 4560),
            message_handler=self._handle_message_internal,
            config=self.config.get('dual_path', {})
        )

        # Register HTTP fallback endpoints for other xApps
        self._register_endpoints()

        # Initialize SDL
        self.sdl = SDLWrapper(use_fake_sdl=False)
        self.namespace = "ts_xapp"

        # State management
        self.ue_metrics: Dict[str, UEMetrics] = {}
        self.policies: Dict[str, HandoverPolicy] = {}
        self.subscriptions: Dict[int, Dict] = {}

        # Load default policy from config
        handover_config = self.config.get('handover', {})
        self.default_policy = HandoverPolicy(
            policy_id="default",
            rsrp_threshold=handover_config.get('rsrp_threshold', -100.0),
            throughput_threshold=handover_config.get('throughput_threshold', 10.0),
            load_threshold=handover_config.get('load_threshold', 0.8)
        )

        # Initialize Flask app for health checks
        self.app = Flask(__name__)
        self._setup_routes()

        logger.info("Traffic Steering xApp initialized with dual-path communication")

    def _register_endpoints(self):
        """Register HTTP fallback endpoints for peer xApps"""
        # Register QoE Predictor endpoint
        self.messenger.register_endpoint(EndpointConfig(
            service_name="qoe-predictor",
            namespace="ricxapp",
            http_port=8090,
            rmr_port=4570
        ))

        # Register RC xApp endpoint
        self.messenger.register_endpoint(EndpointConfig(
            service_name="ran-control",
            namespace="ricxapp",
            http_port=8100,
            rmr_port=4580
        ))

        # Register E2 Term endpoint
        self.messenger.register_endpoint(EndpointConfig(
            service_name="service-ricplt-e2term-rmr-alpha",
            namespace="ricplt",
            http_port=38000,
            rmr_port=38000
        ))

        logger.info("Registered HTTP fallback endpoints")

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return {
                'xapp_name': 'traffic-steering',
                'version': '1.0.0',
                'handover': {
                    'rsrp_threshold': -100.0,
                    'rsrq_threshold': -15.0,
                    'throughput_threshold': 10.0,
                    'load_threshold': 0.8
                }
            }

    def _setup_routes(self):
        """Setup Flask routes for health checks and metrics"""
        @self.app.route('/ric/v1/health/alive', methods=['GET'])
        def health_alive():
            return jsonify({"status": "alive"}), 200

        @self.app.route('/ric/v1/health/ready', methods=['GET'])
        def health_ready():
            # Include dual-path health in readiness
            health_summary = self.messenger.get_health_summary()
            rmr_healthy = health_summary['rmr']['status'] == 'healthy'
            http_available = health_summary['http']['status'] in ['healthy', 'degraded']

            ready = rmr_healthy or http_available

            return jsonify({
                "status": "ready" if ready else "not_ready",
                "communication_health": health_summary
            }), 200 if ready else 503

        @self.app.route('/ric/v1/health/paths', methods=['GET'])
        def health_paths():
            """Detailed communication path health status"""
            return jsonify(self.messenger.get_health_summary()), 200

        @self.app.route('/ric/v1/metrics', methods=['GET'])
        def metrics():
            return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

        @self.app.route('/e2/indication', methods=['POST'])
        def e2_indication():
            """Receive E2 indications from simulator (for testing)"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"error": "No data provided"}), 400

                # Process the indication using the same handler
                self._handle_indication_http(data)

                return jsonify({
                    "status": "success",
                    "message": "Indication processed"
                }), 200

            except Exception as e:
                logger.error(f"Error processing E2 indication: {e}")
                return jsonify({"error": str(e)}), 500

    def _handle_message_internal(self, xapp, summary: dict, sbuf):
        """Internal message handler for DualPathMessenger"""
        mtype = summary.get(rmr.RMR_MS_MSG_TYPE, summary.get('message type', 0))
        logger.debug(f"Received message type: {mtype}")

        try:
            if mtype == RIC_INDICATION:
                self._handle_indication(summary, sbuf)
            elif mtype == RIC_SUB_RESP:
                self._handle_subscription_response(summary, sbuf)
            elif mtype == A1_POLICY_REQ:
                self._handle_policy_request(summary, sbuf)
            else:
                logger.warning(f"Unhandled message type: {mtype}")

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def _handle_indication(self, summary: dict, sbuf):
        """Process E2 Indication messages"""

        # Increment E2 indication counter
        ts_e2_indications_received_total.inc()

        # Parse E2SM-KPM indication
        try:
            # Extract payload from RMR buffer
            if sbuf:
                payload_bytes = rmr.get_payload(sbuf)
                payload = json.loads(payload_bytes.decode('utf-8'))
            else:
                payload = json.loads(summary.get('payload', '{}'))
        except Exception as e:
            logger.error(f"Failed to parse indication payload: {e}")
            return

        # Extract UE metrics
        for ue_data in payload.get('ue_list', []):
            ue_metrics = UEMetrics(
                ue_id=ue_data['ue_id'],
                serving_cell=ue_data['serving_cell'],
                rsrp=ue_data['rsrp'],
                rsrq=ue_data['rsrq'],
                dl_throughput=ue_data['dl_throughput'],
                ul_throughput=ue_data['ul_throughput'],
                timestamp=time.time()
            )

            # Store metrics
            self.ue_metrics[ue_metrics.ue_id] = ue_metrics

            # Update active UEs gauge
            ts_active_ues.set(len(self.ue_metrics))

            # Store in SDL for persistence
            self.sdl.set(
                self.namespace,
                {f"ue_metrics:{ue_metrics.ue_id}": json.dumps(ue_data)}
            )

            # Evaluate handover decision
            self._evaluate_handover(ue_metrics)

    def _handle_indication_http(self, data: dict):
        """Process E2 Indication from HTTP endpoint (for testing)"""

        # Increment E2 indication counter
        ts_e2_indications_received_total.inc()

        # Extract UE metrics from the data
        # Expected format: {'cell_id': 'cell_001', 'ue_id': 'ue_001', 'measurements': [...]}
        try:
            cell_id = data.get('cell_id', 'unknown')
            ue_id = data.get('ue_id', 'unknown')
            measurements = data.get('measurements', [])

            # Parse measurements into UE metrics
            rsrp = -100.0
            rsrq = -15.0
            dl_throughput = 0.0
            ul_throughput = 0.0

            for measurement in measurements:
                name = measurement.get('name', '')
                value = measurement.get('value', 0.0)

                if 'RSRP' in name:
                    rsrp = value
                elif 'RSRQ' in name:
                    rsrq = value
                elif 'ThpDl' in name or 'UEThpDl' in name:
                    dl_throughput = value
                elif 'ThpUl' in name or 'UEThpUl' in name:
                    ul_throughput = value

            # Create UE metrics object
            ue_metrics = UEMetrics(
                ue_id=ue_id,
                serving_cell=cell_id,
                rsrp=rsrp,
                rsrq=rsrq,
                dl_throughput=dl_throughput,
                ul_throughput=ul_throughput,
                timestamp=time.time()
            )

            # Store metrics
            self.ue_metrics[ue_metrics.ue_id] = ue_metrics

            # Update active UEs gauge
            ts_active_ues.set(len(self.ue_metrics))

            # Store in SDL for persistence (best effort)
            try:
                self.sdl.set(
                    self.namespace,
                    {f"ue_metrics:{ue_metrics.ue_id}": json.dumps(data)}
                )
            except Exception as sdl_err:
                logger.debug(f"SDL storage failed (non-critical): {sdl_err}")

            # Evaluate handover decision
            self._evaluate_handover(ue_metrics)

            logger.debug(f"Processed HTTP indication for UE {ue_id} in cell {cell_id}")

        except Exception as e:
            logger.error(f"Error processing HTTP indication: {e}")
            raise

    def _evaluate_handover(self, metrics: UEMetrics):
        """Evaluate if handover is needed based on policy"""

        # Increment decision counter
        ts_handover_decisions_total.inc()

        # Get active policy
        policy = self.policies.get('active', self.default_policy)

        if not policy.enabled:
            return

        # Check handover criteria
        needs_handover = False
        reason = ""

        if metrics.rsrp < policy.rsrp_threshold:
            needs_handover = True
            reason = f"Low RSRP: {metrics.rsrp} dBm"

        if metrics.dl_throughput < policy.throughput_threshold:
            needs_handover = True
            reason = f"Low throughput: {metrics.dl_throughput} Mbps"

        if needs_handover:
            logger.info(f"Triggering handover for UE {metrics.ue_id}: {reason}")

            # Increment handover triggered counter
            ts_handover_triggered_total.inc()

            # Get target cell from QoE Predictor
            target_cell = self._get_target_cell(metrics)

            if target_cell:
                # Send control request to RC xApp
                self._send_handover_command(metrics.ue_id, target_cell)

    def _get_target_cell(self, metrics: UEMetrics) -> Optional[str]:
        """Query QoE Predictor for best target cell"""

        # Send message to QoE Predictor xApp (with HTTP fallback)
        request = {
            "ue_id": metrics.ue_id,
            "serving_cell": metrics.serving_cell,
            "timestamp": metrics.timestamp
        }

        # Message type for QoE prediction request
        QOE_PRED_REQ = 30000

        self._send_message(
            QOE_PRED_REQ,
            json.dumps(request),
            destination="qoe-predictor"
        )

        # For now, return a mock target cell
        # In production, this would parse the QoE Predictor response
        return "cell_02"

    def _send_handover_command(self, ue_id: str, target_cell: str):
        """Send handover command via RC xApp"""

        # Construct E2SM-RC control message
        control_msg = {
            "ue_id": ue_id,
            "target_cell": target_cell,
            "control_style": 3,  # UE-specific handover
            "action": "handover"
        }

        # Send to RC xApp (with HTTP fallback)
        RC_XAPP_REQ = 40000
        self._send_message(
            RC_XAPP_REQ,
            json.dumps(control_msg),
            destination="ran-control"
        )
        logger.info(f"Handover command sent for UE {ue_id} to {target_cell}")

    def _handle_subscription_response(self, summary: dict, sbuf):
        """Handle E2 subscription response"""

        try:
            payload = json.loads(summary['payload'])
        except:
            logger.error("Failed to parse subscription response")
            return

        sub_id = payload.get('subscription_id')

        if payload.get('status') == 'success':
            logger.info(f"Subscription {sub_id} established successfully")
            self.subscriptions[sub_id] = payload
        else:
            logger.error(f"Subscription {sub_id} failed: {payload.get('reason')}")

    def _handle_policy_request(self, summary: dict, sbuf):
        """Handle A1 policy updates"""

        try:
            payload = json.loads(summary['payload'])
        except:
            logger.error("Failed to parse policy request")
            return

        policy_data = payload.get('policy', {})

        # Create new policy
        policy = HandoverPolicy(
            policy_id=payload.get('policy_id'),
            rsrp_threshold=policy_data.get('rsrp_threshold', -100.0),
            throughput_threshold=policy_data.get('throughput_threshold', 10.0),
            load_threshold=policy_data.get('load_threshold', 0.8),
            enabled=policy_data.get('enabled', True)
        )

        # Store policy
        self.policies[policy.policy_id] = policy
        self.sdl.set(
            self.namespace,
            {f"policy:{policy.policy_id}": json.dumps(policy_data)}
        )

        # Increment policy update counter
        ts_policy_updates_total.inc()

        logger.info(f"Policy {policy.policy_id} updated")

        # Send acknowledgment
        self._send_policy_response(payload.get('policy_id'), 'success')

    def _send_policy_response(self, policy_id: str, status: str):
        """Send A1 policy response"""

        response = {
            "policy_id": policy_id,
            "status": status,
            "timestamp": time.time()
        }

        self._send_message(A1_POLICY_RESP, json.dumps(response))

    def _send_message(self, msg_type: int, payload: str, destination: Optional[str] = None):
        """
        Send message via dual-path (RMR primary, HTTP fallback)

        Args:
            msg_type: RMR message type
            payload: Message payload (JSON string or dict)
            destination: Destination service name (for HTTP fallback)
        """
        success = self.messenger.send_message(
            msg_type=msg_type,
            payload=payload,
            destination=destination
        )

        if not success:
            logger.error(
                f"Failed to send message type {msg_type} to {destination or 'routed'} "
                f"via both paths"
            )

    def create_subscriptions(self):
        """Create E2 subscriptions for KPM metrics"""

        # E2SM-KPM subscription for UE metrics
        kpm_subscription = {
            "subscription_id": 1001,
            "ran_function_id": E2SM_KPM_ID,
            "action_type": "report",
            "report_style": 4,  # UE-level measurements
            "granularity_period": 1000,  # 1 second
            "measurements": [
                "DRB.UEThpDl",
                "DRB.UEThpUl",
                "RRU.PrbTotDl",
                "RRU.PrbUsedDl"
            ]
        }

        # Send subscription request
        self._send_message(RIC_SUB_REQ, json.dumps(kpm_subscription))
        logger.info("E2 subscription request sent")

    def _health_check_loop(self):
        """Periodic health check"""

        while self.running:
            time.sleep(30)

            # Clean old metrics
            current_time = time.time()
            expired_ues = []

            for ue_id, metrics in self.ue_metrics.items():
                if current_time - metrics.timestamp > 60:  # 1 minute timeout
                    expired_ues.append(ue_id)

            for ue_id in expired_ues:
                del self.ue_metrics[ue_id]
                logger.debug(f"Removed stale metrics for UE {ue_id}")

            # Update active UEs gauge after cleanup
            ts_active_ues.set(len(self.ue_metrics))

            # Log status
            logger.info(f"Active UEs: {len(self.ue_metrics)}, Policies: {len(self.policies)}")

    def start(self):
        """Start the xApp with dual-path communication"""

        logger.info("Starting Traffic Steering xApp (Release J - Dual-Path)")
        self.running = True

        # Start Flask health check server in background thread
        http_port = self.config.get('http_port', 8081)
        flask_thread = Thread(
            target=lambda: self.app.run(host='0.0.0.0', port=http_port)
        )
        flask_thread.daemon = True
        flask_thread.start()

        # Initialize RMR through DualPathMessenger
        rmr_initialized = self.messenger.initialize_rmr(use_fake_sdl=False)

        if not rmr_initialized:
            logger.warning(
                "RMR initialization failed, will rely on HTTP fallback path"
            )

        # Start dual-path messenger (includes health checks)
        self.messenger.start()

        # Start health check thread
        health_thread = Thread(target=self._health_check_loop)
        health_thread.daemon = True
        health_thread.start()

        # Small delay to ensure messenger is ready
        time.sleep(2)

        # Create E2 subscriptions
        self.create_subscriptions()

        # Start RMR message loop if available
        if self.messenger.rmr_xapp:
            logger.info("Starting RMR message loop")
            self.messenger.rmr_xapp.run()
        else:
            logger.info("Running in HTTP-only mode")
            # Keep main thread alive
            while self.running:
                time.sleep(1)

    def stop(self):
        """Stop the xApp"""
        logger.info("Stopping Traffic Steering xApp...")
        self.running = False
        self.messenger.stop()
        logger.info("Traffic Steering xApp stopped")

def main():
    """Main entry point"""

    # Create and start xApp
    xapp = TrafficSteeringXapp()
    xapp.start()

if __name__ == "__main__":
    main()
