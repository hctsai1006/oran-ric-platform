#!/usr/bin/env python3
"""
KPIMON xApp - KPI Monitoring Application
O-RAN Release J compliant implementation with dual-path redundancy (RMR + HTTP)
Version: 1.1.0
"""

import sys
import os
import json
import time
import logging
import threading
from typing import Dict, List, Any
from datetime import datetime
import redis
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS

# Add common library path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../common'))

from ricxappframe.xapp_frame import rmr
from ricxappframe.xapp_sdl import SDLWrapper
from mdclogpy import Logger
from prometheus_client import Counter, Gauge, Histogram, start_http_server
from flask import Flask, jsonify, request
import numpy as np

# Import dual-path messenger
from dual_path_messenger import DualPathMessenger, EndpointConfig, CommunicationPath

# Import beam query API
from beam_query_api import beam_api, init_beam_service

# Configure logging
logger = Logger(name="KPIMON")
logger.set_level(logging.INFO)

# Prometheus metrics
MESSAGES_RECEIVED = Counter('kpimon_messages_received_total', 'Total number of messages received')
MESSAGES_PROCESSED = Counter('kpimon_messages_processed_total', 'Total number of messages processed')
KPI_VALUES = Gauge('kpimon_kpi_value', 'Current KPI values', ['kpi_type', 'cell_id', 'beam_id'])
PROCESSING_TIME = Histogram('kpimon_processing_time_seconds', 'Time spent processing messages')

# E2SM-KPM v3.0 Message Types (O-RAN Release J)
RIC_INDICATION = 12050
RIC_SUB_REQ = 12010
RIC_SUB_RESP = 12011
RIC_SUB_DEL_REQ = 12012
RIC_SUB_DEL_RESP = 12013

class KPIMonitor:
    """
    KPI Monitor xApp implementation - O-RAN Release J
    Collects and analyzes KPIs from E2 nodes via E2SM-KPM v3.0
    Features:
    - Dual-path communication (RMR primary, HTTP fallback)
    - Automatic failover and recovery
    - Comprehensive monitoring and logging
    """

    def __init__(self, config_path: str = "/app/config/config.json"):
        """Initialize KPIMON xApp"""
        self.config = self._load_config(config_path)
        self.sdl = SDLWrapper(use_fake_sdl=False)
        self.running = False
        self.subscriptions = {}
        self.kpi_buffer = []

        # Initialize dual-path messenger
        self.messenger = DualPathMessenger(
            xapp_name="kpimon",
            rmr_port=self.config.get('rmr_port', 4560),
            message_handler=self._handle_message_internal,
            config=self.config.get('dual_path', {})
        )

        # Register HTTP fallback endpoints
        self._register_endpoints()

        # Initialize data stores
        self._init_redis()
        self._init_influxdb()
        
        # KPI definitions for O-RAN Release J
        self.kpi_definitions = {
            "DRB.UEThpDl": {"id": 1, "type": "throughput", "unit": "Mbps"},
            "DRB.UEThpUl": {"id": 2, "type": "throughput", "unit": "Mbps"},
            "DRB.RlcSduDelayDl": {"id": 3, "type": "latency", "unit": "ms"},
            "DRB.PacketLossDl": {"id": 4, "type": "loss", "unit": "percentage"},
            "RRU.PrbUsedDl": {"id": 5, "type": "resource", "unit": "percentage"},
            "RRU.PrbUsedUl": {"id": 6, "type": "resource", "unit": "percentage"},
            "DRB.MeanActiveUeDl": {"id": 7, "type": "load", "unit": "count"},
            "DRB.MeanActiveUeUl": {"id": 8, "type": "load", "unit": "count"},
            "RRC.ConnMax": {"id": 9, "type": "connection", "unit": "count"},
            "RRC.ConnMean": {"id": 10, "type": "connection", "unit": "count"},
            "RRC.ConnEstabSucc": {"id": 11, "type": "success_rate", "unit": "percentage"},
            "HO.AttOutInterEnbN1": {"id": 12, "type": "handover", "unit": "count"},
            "HO.SuccOutInterEnbN1": {"id": 13, "type": "handover", "unit": "count"},
            "PDCP.BytesTransmittedDl": {"id": 14, "type": "volume", "unit": "bytes"},
            "PDCP.BytesTransmittedUl": {"id": 15, "type": "volume", "unit": "bytes"},
            "UE.RSRP": {"id": 16, "type": "signal", "unit": "dBm"},
            "UE.RSRQ": {"id": 17, "type": "signal", "unit": "dB"},
            "UE.SINR": {"id": 18, "type": "signal", "unit": "dB"},
            "QoS.DlPktDelayPerQCI": {"id": 19, "type": "qos", "unit": "ms"},
            "QoS.UlPktDelayPerQCI": {"id": 20, "type": "qos", "unit": "ms"},
            # Beam-specific KPIs (5G NR beamforming)
            "L1-RSRP.beam": {"id": 21, "type": "beam_signal", "unit": "dBm", "beam_specific": True},
            "L1-SINR.beam": {"id": 22, "type": "beam_signal", "unit": "dB", "beam_specific": True}
        }

        # Initialize Flask app for health checks and beam query API
        self.flask_app = Flask(__name__)
        self._setup_health_routes()

        # Register beam query API blueprint
        self.flask_app.register_blueprint(beam_api)

        logger.info(f"KPIMON xApp initialized with dual-path communication")

    def _register_endpoints(self):
        """Register HTTP fallback endpoints"""
        # Register E2 Term endpoint
        self.messenger.register_endpoint(EndpointConfig(
            service_name="service-ricplt-e2term-rmr-alpha",
            namespace="ricplt",
            http_port=38000,
            rmr_port=38000
        ))

        logger.info("Registered HTTP fallback endpoints")

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            # Return default config
            return {
                "xapp_name": "kpimon",
                "version": "1.0.0",
                "rmr_port": 4560,
                "http_port": 8080,
                "redis": {
                    "host": "redis-service.ricplt",
                    "port": 6379,
                    "db": 0
                },
                "influxdb": {
                    "url": "http://influxdb-service.ricplt:8086",
                    "token": "my-token",
                    "org": "oran",
                    "bucket": "kpimon"
                },
                "subscription": {
                    "report_period": 1000,  # ms
                    "granularity_period": 1000,  # ms
                    "max_measurements": 20
                }
            }
    
    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=self.config['redis']['host'],
                port=self.config['redis']['port'],
                db=self.config['redis']['db'],
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    def _init_influxdb(self):
        """Initialize InfluxDB connection"""
        try:
            self.influx_client = influxdb_client.InfluxDBClient(
                url=self.config['influxdb']['url'],
                token=self.config['influxdb']['token'],
                org=self.config['influxdb']['org']
            )
            self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
            logger.info("InfluxDB connection established")
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            self.influx_client = None

    def _setup_health_routes(self):
        """Setup Flask routes for health checks and E2 indications"""
        @self.flask_app.route('/health/alive', methods=['GET'])
        def health_alive():
            return jsonify({"status": "alive"}), 200

        @self.flask_app.route('/health/ready', methods=['GET'])
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

        @self.flask_app.route('/health/paths', methods=['GET'])
        def health_paths():
            """Detailed communication path health status"""
            return jsonify(self.messenger.get_health_summary()), 200

        @self.flask_app.route('/e2/indication', methods=['POST'])
        def e2_indication():
            """Receive E2 indications from simulator (for testing)"""
            try:
                # Increment received counter
                MESSAGES_RECEIVED.inc()

                data = request.get_json()
                if not data:
                    return jsonify({"error": "No data provided"}), 400

                # Process the indication
                self._handle_indication(json.dumps(data))

                # Increment processed counter
                MESSAGES_PROCESSED.inc()

                return jsonify({
                    "status": "success",
                    "message": "Indication processed"
                }), 200

            except Exception as e:
                logger.error(f"Error processing E2 indication: {e}")
                return jsonify({"error": str(e)}), 500

    def start(self):
        """Start the xApp with dual-path communication"""
        logger.info("Starting KPIMON xApp (Release J - Dual-Path)...")
        self.running = True

        # Initialize beam query service
        init_beam_service(
            self.redis_client,
            self.influx_client,
            self.config['influxdb']['org'],
            self.config['influxdb']['bucket']
        )
        logger.info("Beam Query Service initialized")

        # Start Prometheus metrics server
        start_http_server(8080)
        logger.info("Prometheus metrics server started on port 8080")

        # Start Flask server on port 8081 (health checks + beam query API)
        flask_thread = threading.Thread(target=lambda: self.flask_app.run(
            host='0.0.0.0',
            port=8081,
            debug=False,
            use_reloader=False
        ))
        flask_thread.daemon = True
        flask_thread.start()
        logger.info("Flask server started on port 8081 (health checks + beam query API)")

        # Initialize RMR through DualPathMessenger
        rmr_initialized = self.messenger.initialize_rmr(use_fake_sdl=False)

        if not rmr_initialized:
            logger.warning(
                "RMR initialization failed, will rely on HTTP fallback path"
            )

        # Start dual-path messenger
        self.messenger.start()

        # Start subscription thread
        sub_thread = threading.Thread(target=self._subscription_manager)
        sub_thread.daemon = True
        sub_thread.start()

        # Start KPI processor thread
        processor_thread = threading.Thread(target=self._kpi_processor)
        processor_thread.daemon = True
        processor_thread.start()

        # Run the xApp
        logger.info("KPIMON xApp started successfully")

        # Start RMR message loop if available
        if self.messenger.rmr_xapp:
            logger.info("Starting RMR message loop")
            self.messenger.rmr_xapp.run(thread=True)
        else:
            logger.info("Running in HTTP-only mode")

        # Keep main thread alive
        while self.running:
            time.sleep(1)
    
    def _handle_message_internal(self, xapp, summary, sbuf):
        """Internal message handler for DualPathMessenger"""
        MESSAGES_RECEIVED.inc()

        msg_type = summary.get(rmr.RMR_MS_MSG_TYPE, summary.get('message type', 0))
        logger.debug(f"Received message type: {msg_type}")

        # Extract payload from buffer
        if sbuf:
            payload_bytes = rmr.get_payload(sbuf)
            payload = payload_bytes.decode('utf-8') if payload_bytes else ""
        else:
            payload = summary.get('payload', '{}')

        try:
            with PROCESSING_TIME.time():
                if msg_type == RIC_INDICATION:
                    self._handle_indication(payload)
                elif msg_type == RIC_SUB_RESP:
                    self._handle_subscription_response(payload)
                elif msg_type == RIC_SUB_DEL_RESP:
                    self._handle_subscription_delete_response(payload)
                else:
                    logger.warning(f"Unknown message type: {msg_type}")

            MESSAGES_PROCESSED.inc()

        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    def _handle_indication(self, payload):
        """Handle RIC Indication messages containing KPIs with beam_id support"""
        try:
            # Parse E2SM-KPM v3.0 indication
            indication = json.loads(payload)

            # Extract KPI data (with backward compatibility)
            cell_id = indication.get('cell_id')
            ue_id = indication.get('ue_id')
            beam_id = indication.get('beam_id', 'n/a')  # NEW: Extract beam_id (SSB Index)
            timestamp = indication.get('timestamp', datetime.now().isoformat())
            measurements = indication.get('measurements', [])

            logger.debug(f"Received {len(measurements)} measurements from cell {cell_id}, beam {beam_id}")

            # Process each measurement
            for measurement in measurements:
                kpi_name = measurement.get('name')
                kpi_value = measurement.get('value')
                # Beam-specific measurements may have beam_id in the measurement itself
                measurement_beam_id = measurement.get('beam_id', beam_id)

                if kpi_name in self.kpi_definitions:
                    kpi_def = self.kpi_definitions[kpi_name]
                    is_beam_specific = kpi_def.get('beam_specific', False)

                    kpi_data = {
                        'timestamp': timestamp,
                        'cell_id': cell_id,
                        'ue_id': ue_id,
                        'beam_id': measurement_beam_id,  # NEW: Include beam_id
                        'kpi_name': kpi_name,
                        'kpi_value': kpi_value,
                        'kpi_type': kpi_def['type'],
                        'unit': kpi_def['unit'],
                        'beam_specific': is_beam_specific
                    }

                    # Add to buffer for batch processing
                    self.kpi_buffer.append(kpi_data)

                    # Update Prometheus metrics with beam_id label
                    KPI_VALUES.labels(
                        kpi_type=kpi_name,
                        cell_id=cell_id,
                        beam_id=str(measurement_beam_id)
                    ).set(kpi_value)

                    # Store in Redis for real-time access
                    if self.redis_client:
                        # Store with beam_id in key for beam-specific KPIs
                        if is_beam_specific:
                            key = f"kpi:{cell_id}:{kpi_name}:beam_{measurement_beam_id}"
                        else:
                            key = f"kpi:{cell_id}:{kpi_name}"

                        self.redis_client.setex(key, 300, json.dumps(kpi_data))

                        # Additional beam-centric storage for beam query API
                        beam_key = f"kpi:beam:{measurement_beam_id}:cell:{cell_id}:{kpi_name}"
                        self.redis_client.setex(beam_key, 300, json.dumps(kpi_data))

                        # Update UE-beam association if ue_id present
                        if ue_id:
                            ue_beam_key = f"ue:beam:{measurement_beam_id}:cell:{cell_id}:{ue_id}"
                            self.redis_client.setex(ue_beam_key, 300, "1")

                        # Store in timeline (cell-level for backward compatibility)
                        self.redis_client.zadd(f"kpi:timeline:{cell_id}", {timestamp: kpi_value})

                        # NEW: Store beam-specific timeline
                        if is_beam_specific and measurement_beam_id != 'n/a':
                            beam_timeline_key = f"kpi:timeline:{cell_id}:beam_{measurement_beam_id}"
                            self.redis_client.zadd(beam_timeline_key, {timestamp: kpi_value})

            # Trigger anomaly detection
            self._detect_anomalies(cell_id, measurements, beam_id)

        except Exception as e:
            logger.error(f"Error handling indication: {e}")
    
    def _handle_subscription_response(self, payload):
        """Handle subscription response"""
        try:
            resp = json.loads(payload)
            req_id = resp.get('request_id')
            status = resp.get('status')
            
            if status == 'success':
                self.subscriptions[req_id] = {
                    'status': 'active',
                    'timestamp': datetime.now().isoformat()
                }
                logger.info(f"Subscription {req_id} activated successfully")
            else:
                logger.error(f"Subscription {req_id} failed: {resp.get('reason')}")
        except Exception as e:
            logger.error(f"Error handling subscription response: {e}")
    
    def _handle_subscription_delete_response(self, payload):
        """Handle subscription delete response"""
        try:
            resp = json.loads(payload)
            req_id = resp.get('request_id')
            
            if req_id in self.subscriptions:
                del self.subscriptions[req_id]
                logger.info(f"Subscription {req_id} deleted successfully")
        except Exception as e:
            logger.error(f"Error handling subscription delete response: {e}")
    
    def _subscription_manager(self):
        """Manage E2 subscriptions"""
        while self.running:
            try:
                # Create subscription request for E2SM-KPM v3.0
                sub_request = {
                    "request_id": f"kpimon_{int(time.time())}",
                    "ran_function_id": 2,  # E2SM-KPM
                    "event_trigger": {
                        "report_period": self.config['subscription']['report_period']
                    },
                    "actions": [
                        {
                            "action_id": 1,
                            "action_type": "report",
                            "measurements": list(self.kpi_definitions.keys()),
                            "granularity_period": self.config['subscription']['granularity_period']
                        }
                    ]
                }
                
                # Send subscription request
                self._send_message(RIC_SUB_REQ, json.dumps(sub_request))
                logger.info(f"Sent subscription request: {sub_request['request_id']}")
                
                # Wait before next subscription check
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in subscription manager: {e}")
                time.sleep(10)
    
    def _kpi_processor(self):
        """Process KPI buffer and store in InfluxDB with beam_id support"""
        while self.running:
            try:
                if len(self.kpi_buffer) >= 100:  # Batch size
                    batch = self.kpi_buffer[:100]
                    self.kpi_buffer = self.kpi_buffer[100:]

                    # Write to InfluxDB
                    if self.influx_client:
                        points = []
                        for kpi in batch:
                            # Create point with beam_id tag for filtering
                            point = influxdb_client.Point("kpi_measurement") \
                                .tag("cell_id", kpi['cell_id']) \
                                .tag("kpi_name", kpi['kpi_name']) \
                                .tag("kpi_type", kpi['kpi_type']) \
                                .tag("beam_id", str(kpi.get('beam_id', 'n/a'))) \
                                .field("value", float(kpi['kpi_value'])) \
                                .time(kpi['timestamp'])

                            # Add ue_id as field for better querying
                            if kpi.get('ue_id'):
                                point = point.tag("ue_id", kpi['ue_id'])

                            # Mark if beam-specific for easy filtering
                            if kpi.get('beam_specific', False):
                                point = point.tag("beam_specific", "true")

                            points.append(point)

                        self.write_api.write(
                            bucket=self.config['influxdb']['bucket'],
                            org=self.config['influxdb']['org'],
                            record=points
                        )
                        logger.debug(f"Wrote {len(points)} KPI points to InfluxDB")

                time.sleep(1)

            except Exception as e:
                logger.error(f"Error in KPI processor: {e}")
                time.sleep(5)
    
    def _detect_anomalies(self, cell_id: str, measurements: List[Dict], beam_id=None):
        """Detect anomalies in KPI data including beam-specific metrics"""
        try:
            # Simple threshold-based anomaly detection
            anomalies = []

            for measurement in measurements:
                kpi_name = measurement.get('name')
                kpi_value = measurement.get('value')
                measurement_beam_id = measurement.get('beam_id', beam_id)

                # Define thresholds
                thresholds = {
                    "DRB.PacketLossDl": 5.0,  # Alert if packet loss > 5%
                    "RRU.PrbUsedDl": 90.0,     # Alert if PRB usage > 90%
                    "RRU.PrbUsedUl": 90.0,     # Alert if PRB usage > 90%
                    "UE.RSRP": -110.0,         # Alert if RSRP < -110 dBm
                    "RRC.ConnEstabSucc": 95.0,  # Alert if success rate < 95%
                    # Beam-specific thresholds
                    "L1-RSRP.beam": -105.0,    # Alert if beam RSRP < -105 dBm
                    "L1-SINR.beam": 10.0       # Alert if beam SINR < 10 dB
                }

                if kpi_name in thresholds:
                    threshold = thresholds[kpi_name]

                    if kpi_name in ["UE.RSRP", "L1-RSRP.beam"]:
                        if kpi_value < threshold:
                            anomaly = {
                                'kpi': kpi_name,
                                'value': kpi_value,
                                'threshold': threshold,
                                'type': 'below_threshold'
                            }
                            if measurement_beam_id is not None:
                                anomaly['beam_id'] = measurement_beam_id
                            anomalies.append(anomaly)
                    elif kpi_name in ["RRC.ConnEstabSucc", "L1-SINR.beam"]:
                        if kpi_value < threshold:
                            anomaly = {
                                'kpi': kpi_name,
                                'value': kpi_value,
                                'threshold': threshold,
                                'type': 'below_threshold'
                            }
                            if measurement_beam_id is not None:
                                anomaly['beam_id'] = measurement_beam_id
                            anomalies.append(anomaly)
                    else:
                        if kpi_value > threshold:
                            anomaly = {
                                'kpi': kpi_name,
                                'value': kpi_value,
                                'threshold': threshold,
                                'type': 'above_threshold'
                            }
                            if measurement_beam_id is not None:
                                anomaly['beam_id'] = measurement_beam_id
                            anomalies.append(anomaly)

            if anomalies:
                self._raise_alarm(cell_id, anomalies, beam_id)

        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
    
    def _raise_alarm(self, cell_id: str, anomalies: List[Dict], beam_id=None):
        """Raise alarm for detected anomalies including beam-specific issues"""
        alarm = {
            'timestamp': datetime.now().isoformat(),
            'cell_id': cell_id,
            'beam_id': beam_id,
            'anomalies': anomalies,
            'severity': 'warning'
        }

        # Store alarm in Redis
        if self.redis_client:
            self.redis_client.rpush(f"alarms:{cell_id}", json.dumps(alarm))
            self.redis_client.expire(f"alarms:{cell_id}", 86400)  # 24 hours

            # Store beam-specific alarms separately for easier filtering
            if beam_id is not None and beam_id != 'n/a':
                beam_alarm_key = f"alarms:{cell_id}:beam_{beam_id}"
                self.redis_client.rpush(beam_alarm_key, json.dumps(alarm))
                self.redis_client.expire(beam_alarm_key, 86400)  # 24 hours

        logger.warning(f"Anomaly detected in cell {cell_id}, beam {beam_id}: {anomalies}")
    
    def _send_message(self, msg_type: int, payload: str, destination: str = None):
        """Send message via dual-path (RMR primary, HTTP fallback)"""
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
    
    def stop(self):
        """Stop the xApp"""
        logger.info("Stopping KPIMON xApp...")
        self.running = False
        if self.xapp:
            self.xapp.stop()
        if self.influx_client:
            self.influx_client.close()
        logger.info("KPIMON xApp stopped")


if __name__ == "__main__":
    # Create and start KPIMON xApp
    kpimon = KPIMonitor()
    
    try:
        kpimon.start()
    except KeyboardInterrupt:
        kpimon.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        kpimon.stop()
