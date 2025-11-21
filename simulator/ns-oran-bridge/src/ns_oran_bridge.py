#!/usr/bin/env python3
"""
ns-O-RAN Bridge for E2-Simulator Integration
Purpose: Translate ns-O-RAN events to E2 indication format and send to E2-simulator
Maintains compatibility with existing kpimon integration
"""

import json
import logging
import requests
import time
import threading
from datetime import datetime
from typing import Dict, Optional
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NSOraNBridge:
    """Bridge between ns-O-RAN and E2-simulator"""

    def __init__(self, e2_simulator_host: str = 'localhost', e2_simulator_port: int = 8080):
        """Initialize the bridge"""
        self.e2_simulator_host = e2_simulator_host
        self.e2_simulator_port = e2_simulator_port
        self.base_url = f"http://{e2_simulator_host}:{e2_simulator_port}"

        self.flask_app = Flask(__name__)
        self._register_routes()

        # Statistics
        self.stats = {
            'events_received': 0,
            'events_processed': 0,
            'events_failed': 0,
            'last_event': None
        }

    def _register_routes(self):
        """Register Flask HTTP routes"""
        bridge = self

        @self.flask_app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            try:
                resp = requests.get(f"{bridge.base_url}/health", timeout=2)
                e2sim_healthy = resp.status_code == 200
            except Exception:
                e2sim_healthy = False

            return jsonify({
                'status': 'healthy',
                'e2_simulator_connected': e2sim_healthy,
                'timestamp': datetime.now().isoformat()
            }), 200

        @self.flask_app.route('/stats', methods=['GET'])
        def get_stats():
            """Get bridge statistics"""
            return jsonify(bridge.stats), 200

        @self.flask_app.route('/ns-oran/event', methods=['POST'])
        def handle_ns_oran_event():
            """Handle incoming ns-O-RAN events"""
            try:
                event = request.get_json()
                bridge.stats['events_received'] += 1
                bridge.stats['last_event'] = datetime.now().isoformat()

                event_type = event.get('event_type', 'unknown')
                logger.info(f"Received ns-O-RAN event: {event_type}")

                if event_type == 'uav_position_update':
                    success = bridge._handle_uav_position_update(event)
                elif event_type == 'uav_mission':
                    success = bridge._handle_uav_mission(event)
                elif event_type == 'network_config':
                    success = bridge._handle_network_config(event)
                else:
                    logger.warning(f"Unknown event type: {event_type}")
                    success = False

                if success:
                    bridge.stats['events_processed'] += 1
                    return jsonify({'status': 'processed', 'event_type': event_type}), 200
                else:
                    bridge.stats['events_failed'] += 1
                    return jsonify({'status': 'failed', 'event_type': event_type}), 400

            except Exception as e:
                logger.exception(f"Error handling ns-O-RAN event: {e}")
                bridge.stats['events_failed'] += 1
                return jsonify({'error': str(e)}), 400

        @self.flask_app.route('/simulator/command', methods=['POST'])
        def send_simulator_command():
            """Send direct command to E2-simulator"""
            try:
                cmd = request.get_json()
                result = bridge.send_to_simulator(cmd)

                if result:
                    return jsonify({'status': 'sent', 'command': cmd.get('command_type')}), 200
                else:
                    return jsonify({'error': 'Failed to send command'}), 500

            except Exception as e:
                logger.exception(f"Error sending simulator command: {e}")
                return jsonify({'error': str(e)}), 400

    def send_to_simulator(self, data: Dict) -> bool:
        """Send data to E2-simulator"""
        try:
            endpoint = data.pop('endpoint', '/ns-oran/control')
            url = f"{self.base_url}{endpoint}"

            response = requests.post(
                url,
                json=data,
                timeout=5,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code in [200, 201]:
                logger.debug(f"Successfully sent data to E2-simulator: {endpoint}")
                return True
            else:
                logger.warning(f"Failed to send to E2-simulator: HTTP {response.status_code}")
                return False

        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error to E2-simulator at {self.base_url}")
            return False
        except Exception as e:
            logger.error(f"Error sending to E2-simulator: {e}")
            return False

    def _handle_uav_position_update(self, event: Dict) -> bool:
        """Handle UAV position update from ns-O-RAN"""
        try:
            uav_id = event.get('uav_id')
            position = event.get('position')  # {x, y, z}
            velocity = event.get('velocity')  # {vx, vy, vz}

            if not uav_id:
                logger.error("Missing uav_id in position update")
                return False

            # Send control command to E2-simulator
            control_cmd = {
                'command_type': 'uav_update',
                'uav_id': uav_id,
                'endpoint': '/ns-oran/control'
            }

            if position:
                control_cmd['position'] = position
            if velocity:
                control_cmd['velocity'] = velocity

            success = self.send_to_simulator(control_cmd)
            if success:
                logger.info(f"Updated UAV {uav_id} position in E2-simulator")
            return success

        except Exception as e:
            logger.exception(f"Error handling UAV position update: {e}")
            return False

    def _handle_uav_mission(self, event: Dict) -> bool:
        """Handle UAV mission configuration from ns-O-RAN"""
        try:
            uav_id = event.get('uav_id')
            mission_type = event.get('mission_type')  # e.g., 'coverage', 'surveillance'
            target_area = event.get('target_area')  # {x_min, x_max, y_min, y_max, altitude}

            if not uav_id or not mission_type:
                logger.error("Missing uav_id or mission_type in mission event")
                return False

            logger.info(f"Processing UAV {uav_id} mission: {mission_type}")

            # Configure UAV for mission
            config_data = {
                'uav_id': uav_id,
                'mission_type': mission_type,
                'endpoint': '/config/uav'
            }

            if target_area:
                # Set initial position at center of target area
                config_data['position'] = {
                    'x': (target_area['x_min'] + target_area['x_max']) / 2,
                    'y': (target_area['y_min'] + target_area['y_max']) / 2,
                    'z': target_area.get('altitude', 100)
                }

            success = self.send_to_simulator(config_data)
            if success:
                logger.info(f"Configured UAV {uav_id} for {mission_type} mission")
            return success

        except Exception as e:
            logger.exception(f"Error handling UAV mission: {e}")
            return False

    def _handle_network_config(self, event: Dict) -> bool:
        """Handle network configuration from ns-O-RAN"""
        try:
            config_update = {}

            if 'indication_interval' in event:
                config_update['interval'] = event['indication_interval']

            if 'uav_enabled' in event:
                config_update['uav_enabled'] = event['uav_enabled']

            if not config_update:
                logger.warning("No recognized config fields in network_config event")
                return False

            config_update['command_type'] = 'config'
            config_update['endpoint'] = '/ns-oran/control'

            success = self.send_to_simulator(config_update)
            if success:
                logger.info(f"Updated network configuration: {config_update}")
            return success

        except Exception as e:
            logger.exception(f"Error handling network configuration: {e}")
            return False

    def start(self):
        """Start the bridge"""
        logger.info("="*60)
        logger.info("ns-O-RAN Bridge for E2-Simulator")
        logger.info("="*60)
        logger.info(f"E2-Simulator: {self.base_url}")
        logger.info("="*60)

        # Start Flask HTTP server
        self.flask_app.run(host='0.0.0.0', port=5000, debug=False)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='ns-O-RAN Bridge')
    parser.add_argument('--e2-host', default='localhost', help='E2-simulator host')
    parser.add_argument('--e2-port', type=int, default=8080, help='E2-simulator port')
    args = parser.parse_args()

    bridge = NSOraNBridge(e2_simulator_host=args.e2_host, e2_simulator_port=args.e2_port)
    bridge.start()


if __name__ == '__main__':
    main()
