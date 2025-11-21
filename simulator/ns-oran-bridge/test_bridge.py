#!/usr/bin/env python3
"""
Test script for ns-O-RAN bridge
Verifies integration between ns-O-RAN events and E2-simulator
"""

import json
import requests
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BridgeTester:
    """Test ns-O-RAN bridge functionality"""

    def __init__(self, bridge_url: str = "http://localhost:5000"):
        self.bridge_url = bridge_url
        self.results = {
            'passed': [],
            'failed': []
        }

    def test_bridge_health(self) -> bool:
        """Test bridge health endpoint"""
        try:
            resp = requests.get(f"{self.bridge_url}/health", timeout=5)
            data = resp.json()

            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            assert data['status'] == 'healthy', "Status is not healthy"

            logger.info(f"Bridge health: PASSED")
            logger.info(f"  - E2-simulator connected: {data.get('e2_simulator_connected')}")

            self.results['passed'].append('bridge_health')
            return True

        except Exception as e:
            logger.error(f"Bridge health test FAILED: {e}")
            self.results['failed'].append(('bridge_health', str(e)))
            return False

    def test_bridge_stats(self) -> bool:
        """Test bridge statistics endpoint"""
        try:
            resp = requests.get(f"{self.bridge_url}/stats", timeout=5)
            data = resp.json()

            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            assert 'events_received' in data, "Missing events_received"
            assert 'events_processed' in data, "Missing events_processed"

            logger.info(f"Bridge stats: PASSED")
            logger.info(f"  - Events received: {data['events_received']}")
            logger.info(f"  - Events processed: {data['events_processed']}")

            self.results['passed'].append('bridge_stats')
            return True

        except Exception as e:
            logger.error(f"Bridge stats test FAILED: {e}")
            self.results['failed'].append(('bridge_stats', str(e)))
            return False

    def test_uav_position_update_event(self) -> bool:
        """Test handling of UAV position update events"""
        try:
            event = {
                'event_type': 'uav_position_update',
                'uav_id': 'uav_001',
                'position': {'x': 300.0, 'y': 400.0, 'z': 250.0},
                'velocity': {'vx': 3.0, 'vy': 4.0, 'vz': 1.0}
            }

            resp = requests.post(
                f"{self.bridge_url}/ns-oran/event",
                json=event,
                timeout=5
            )

            data = resp.json()
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            assert data['status'] == 'processed', "Event not processed"

            logger.info(f"UAV position update event: PASSED")
            self.results['passed'].append('uav_position_event')
            return True

        except Exception as e:
            logger.error(f"UAV position update test FAILED: {e}")
            self.results['failed'].append(('uav_position_event', str(e)))
            return False

    def test_uav_mission_event(self) -> bool:
        """Test handling of UAV mission events"""
        try:
            event = {
                'event_type': 'uav_mission',
                'uav_id': 'uav_002',
                'mission_type': 'coverage',
                'target_area': {
                    'x_min': 0.0,
                    'x_max': 500.0,
                    'y_min': 0.0,
                    'y_max': 500.0,
                    'altitude': 200.0
                }
            }

            resp = requests.post(
                f"{self.bridge_url}/ns-oran/event",
                json=event,
                timeout=5
            )

            data = resp.json()
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            assert data['status'] == 'processed', "Event not processed"

            logger.info(f"UAV mission event: PASSED")
            self.results['passed'].append('uav_mission_event')
            return True

        except Exception as e:
            logger.error(f"UAV mission event test FAILED: {e}")
            self.results['failed'].append(('uav_mission_event', str(e)))
            return False

    def test_network_config_event(self) -> bool:
        """Test handling of network configuration events"""
        try:
            event = {
                'event_type': 'network_config',
                'indication_interval': 3,
                'uav_enabled': True
            }

            resp = requests.post(
                f"{self.bridge_url}/ns-oran/event",
                json=event,
                timeout=5
            )

            data = resp.json()
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            assert data['status'] == 'processed', "Event not processed"

            logger.info(f"Network config event: PASSED")
            self.results['passed'].append('network_config_event')
            return True

        except Exception as e:
            logger.error(f"Network config event test FAILED: {e}")
            self.results['failed'].append(('network_config_event', str(e)))
            return False

    def test_invalid_event(self) -> bool:
        """Test handling of invalid events"""
        try:
            event = {
                'event_type': 'unknown_event_type',
                'data': 'some_data'
            }

            resp = requests.post(
                f"{self.bridge_url}/ns-oran/event",
                json=event,
                timeout=5
            )

            assert resp.status_code == 400, f"Expected 400 for invalid event, got {resp.status_code}"

            logger.info(f"Invalid event handling: PASSED")
            self.results['passed'].append('invalid_event_handling')
            return True

        except Exception as e:
            logger.error(f"Invalid event test FAILED: {e}")
            self.results['failed'].append(('invalid_event_handling', str(e)))
            return False

    def print_summary(self):
        """Print test summary"""
        total = len(self.results['passed']) + len(self.results['failed'])
        passed = len(self.results['passed'])
        failed = len(self.results['failed'])

        print("\n" + "="*60)
        print("ns-O-RAN Bridge Test Summary")
        print("="*60)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print("="*60)

        if self.results['passed']:
            print("\nPassed Tests:")
            for test in self.results['passed']:
                print(f"  [OK] {test}")

        if self.results['failed']:
            print("\nFailed Tests:")
            for test, error in self.results['failed']:
                print(f"  [FAIL] {test}")
                print(f"         Error: {error}")

        print("="*60 + "\n")

        return failed == 0

    def run_all_tests(self) -> bool:
        """Run all tests"""
        logger.info(f"Starting bridge tests against {self.bridge_url}")

        # Wait for service to be ready
        time.sleep(1)

        tests = [
            self.test_bridge_health,
            self.test_bridge_stats,
            self.test_uav_position_update_event,
            self.test_uav_mission_event,
            self.test_network_config_event,
            self.test_invalid_event
        ]

        for test in tests:
            test()
            time.sleep(0.5)

        return self.print_summary()


def main():
    """Main test runner"""
    import argparse

    parser = argparse.ArgumentParser(description='ns-O-RAN Bridge Tests')
    parser.add_argument('--url', default='http://localhost:5000', help='Bridge URL')
    args = parser.parse_args()

    tester = BridgeTester(bridge_url=args.url)
    success = tester.run_all_tests()

    exit(0 if success else 1)


if __name__ == '__main__':
    main()
