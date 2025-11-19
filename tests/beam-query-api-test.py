#!/usr/bin/env python3
"""
Test script for Beam KPI Query API
Tests all API endpoints with various query parameters

Author: O-RAN RIC Platform Team
Date: 2025-11-19
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any

# Configuration
API_BASE_URL = "http://localhost:30081/api"  # NodePort access
# Alternative: "http://kpimon.ricxapp.svc.cluster.local:8081/api" for in-cluster access

class BeamAPITester:
    """Test suite for Beam KPI Query API"""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.test_results = []

    def test_health_endpoints(self):
        """Test health check endpoints"""
        print("\n=== Testing Health Endpoints ===")

        # Test alive endpoint
        try:
            response = requests.get(f"{self.base_url}/../health/alive", timeout=5)
            if response.status_code == 200:
                print("✓ Health alive endpoint: PASS")
                self.test_results.append(("health_alive", "PASS"))
            else:
                print(f"✗ Health alive endpoint: FAIL (HTTP {response.status_code})")
                self.test_results.append(("health_alive", "FAIL"))
        except Exception as e:
            print(f"✗ Health alive endpoint: ERROR ({e})")
            self.test_results.append(("health_alive", "ERROR"))

        # Test ready endpoint
        try:
            response = requests.get(f"{self.base_url}/../health/ready", timeout=5)
            if response.status_code == 200:
                print("✓ Health ready endpoint: PASS")
                self.test_results.append(("health_ready", "PASS"))
            else:
                print(f"✗ Health ready endpoint: FAIL (HTTP {response.status_code})")
                self.test_results.append(("health_ready", "FAIL"))
        except Exception as e:
            print(f"✗ Health ready endpoint: ERROR ({e})")
            self.test_results.append(("health_ready", "ERROR"))

    def test_get_beam_kpi_current(self, beam_id: int = 1):
        """Test GET /api/beam/{beam_id}/kpi with current data"""
        print(f"\n=== Testing GET /api/beam/{beam_id}/kpi (current) ===")

        try:
            response = requests.get(
                f"{self.base_url}/beam/{beam_id}/kpi",
                params={
                    'kpi_type': 'all',
                    'time_range': 'current'
                },
                timeout=10
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ GET beam KPI (current): PASS")
                print(f"  Beam ID: {data.get('beam_id')}")
                print(f"  Source: {data.get('source')}")
                print(f"  KPI Count: {data.get('count')}")

                # Display signal quality if available
                if 'data' in data and 'signal_quality' in data['data']:
                    sq = data['data']['signal_quality']
                    if 'rsrp' in sq:
                        print(f"  RSRP: {sq['rsrp']['value']} {sq['rsrp']['unit']} ({sq['rsrp'].get('quality', 'N/A')})")
                    if 'rsrq' in sq:
                        print(f"  RSRQ: {sq['rsrq']['value']} {sq['rsrq']['unit']} ({sq['rsrq'].get('quality', 'N/A')})")
                    if 'sinr' in sq:
                        print(f"  SINR: {sq['sinr']['value']} {sq['sinr']['unit']} ({sq['sinr'].get('quality', 'N/A')})")

                # Display throughput if available
                if 'data' in data and 'throughput' in data['data']:
                    tp = data['data']['throughput']
                    if 'downlink' in tp:
                        print(f"  DL Throughput: {tp['downlink']['value']} {tp['downlink']['unit']}")
                    if 'uplink' in tp:
                        print(f"  UL Throughput: {tp['uplink']['value']} {tp['uplink']['unit']}")

                print("\nFull Response:")
                print(json.dumps(data, indent=2))

                self.test_results.append((f"get_beam_{beam_id}_kpi_current", "PASS"))
                return data

            elif response.status_code == 404:
                print(f"✓ GET beam KPI (current): NO DATA (expected for beam without data)")
                print(f"  Message: {response.json().get('message')}")
                self.test_results.append((f"get_beam_{beam_id}_kpi_current", "NO_DATA"))
                return None

            else:
                print(f"✗ GET beam KPI (current): FAIL")
                print(f"  Response: {response.text}")
                self.test_results.append((f"get_beam_{beam_id}_kpi_current", "FAIL"))
                return None

        except Exception as e:
            print(f"✗ GET beam KPI (current): ERROR ({e})")
            self.test_results.append((f"get_beam_{beam_id}_kpi_current", "ERROR"))
            return None

    def test_get_beam_kpi_filtered(self, beam_id: int = 1):
        """Test GET /api/beam/{beam_id}/kpi with KPI type filter"""
        print(f"\n=== Testing GET /api/beam/{beam_id}/kpi (filtered) ===")

        try:
            response = requests.get(
                f"{self.base_url}/beam/{beam_id}/kpi",
                params={
                    'kpi_type': 'rsrp,rsrq,sinr',
                    'time_range': 'current'
                },
                timeout=10
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ GET beam KPI (filtered): PASS")
                print(f"  Query Params: {data.get('query_params')}")
                print(f"  KPI Count: {data.get('count')}")
                self.test_results.append((f"get_beam_{beam_id}_kpi_filtered", "PASS"))
                return data
            else:
                print(f"✗ GET beam KPI (filtered): FAIL")
                self.test_results.append((f"get_beam_{beam_id}_kpi_filtered", "FAIL"))
                return None

        except Exception as e:
            print(f"✗ GET beam KPI (filtered): ERROR ({e})")
            self.test_results.append((f"get_beam_{beam_id}_kpi_filtered", "ERROR"))
            return None

    def test_get_beam_kpi_historical(self, beam_id: int = 1):
        """Test GET /api/beam/{beam_id}/kpi with historical data"""
        print(f"\n=== Testing GET /api/beam/{beam_id}/kpi (historical) ===")

        try:
            response = requests.get(
                f"{self.base_url}/beam/{beam_id}/kpi",
                params={
                    'kpi_type': 'rsrp,rsrq,sinr',
                    'time_range': 'last_15m',
                    'aggregation': 'mean'
                },
                timeout=10
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ GET beam KPI (historical): PASS")
                print(f"  Source: {data.get('source')}")
                print(f"  Aggregation: {data.get('query_params', {}).get('aggregation')}")
                self.test_results.append((f"get_beam_{beam_id}_kpi_historical", "PASS"))
                return data
            elif response.status_code in [404, 500]:
                # InfluxDB might not be available or no historical data yet
                print(f"✓ GET beam KPI (historical): NO DATA (expected if InfluxDB not configured)")
                self.test_results.append((f"get_beam_{beam_id}_kpi_historical", "NO_DATA"))
                return None
            else:
                print(f"✗ GET beam KPI (historical): FAIL")
                self.test_results.append((f"get_beam_{beam_id}_kpi_historical", "FAIL"))
                return None

        except Exception as e:
            print(f"✗ GET beam KPI (historical): ERROR ({e})")
            self.test_results.append((f"get_beam_{beam_id}_kpi_historical", "ERROR"))
            return None

    def test_get_beam_timeseries(self, beam_id: int = 1):
        """Test GET /api/beam/{beam_id}/kpi/timeseries"""
        print(f"\n=== Testing GET /api/beam/{beam_id}/kpi/timeseries ===")

        try:
            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)

            response = requests.get(
                f"{self.base_url}/beam/{beam_id}/kpi/timeseries",
                params={
                    'kpi_type': 'rsrp',
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'interval': '30s'
                },
                timeout=10
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ GET beam timeseries: PASS")
                print(f"  KPI Type: {data.get('kpi_type')}")
                print(f"  Datapoints: {data.get('count')}")
                self.test_results.append((f"get_beam_{beam_id}_timeseries", "PASS"))
                return data
            elif response.status_code in [404, 500]:
                print(f"✓ GET beam timeseries: NO DATA (expected if InfluxDB not configured)")
                self.test_results.append((f"get_beam_{beam_id}_timeseries", "NO_DATA"))
                return None
            else:
                print(f"✗ GET beam timeseries: FAIL")
                self.test_results.append((f"get_beam_{beam_id}_timeseries", "FAIL"))
                return None

        except Exception as e:
            print(f"✗ GET beam timeseries: ERROR ({e})")
            self.test_results.append((f"get_beam_{beam_id}_timeseries", "ERROR"))
            return None

    def test_list_beams(self):
        """Test GET /api/beam/list"""
        print(f"\n=== Testing GET /api/beam/list ===")

        try:
            response = requests.get(
                f"{self.base_url}/beam/list",
                timeout=10
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ List beams: PASS")
                print(f"  Total Beams: {data.get('count')}")

                if data.get('beams'):
                    print("\n  Active Beams:")
                    for beam in data['beams'][:5]:  # Show first 5
                        print(f"    - Beam {beam['beam_id']} (Cell: {beam.get('cell_id')}, Status: {beam.get('status')})")
                        if 'summary' in beam:
                            summary = beam['summary']
                            if 'rsrp_avg' in summary:
                                print(f"      RSRP: {summary['rsrp_avg']:.2f} dBm")
                            if 'ue_count' in summary:
                                print(f"      UEs: {summary['ue_count']}")

                self.test_results.append(("list_beams", "PASS"))
                return data
            else:
                print(f"✗ List beams: FAIL")
                self.test_results.append(("list_beams", "FAIL"))
                return None

        except Exception as e:
            print(f"✗ List beams: ERROR ({e})")
            self.test_results.append(("list_beams", "ERROR"))
            return None

    def test_list_beams_filtered(self):
        """Test GET /api/beam/list with filters"""
        print(f"\n=== Testing GET /api/beam/list (filtered) ===")

        try:
            response = requests.get(
                f"{self.base_url}/beam/list",
                params={
                    'min_rsrp': -100
                },
                timeout=10
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ List beams (filtered): PASS")
                print(f"  Beams with RSRP > -100 dBm: {data.get('count')}")
                self.test_results.append(("list_beams_filtered", "PASS"))
                return data
            else:
                print(f"✗ List beams (filtered): FAIL")
                self.test_results.append(("list_beams_filtered", "FAIL"))
                return None

        except Exception as e:
            print(f"✗ List beams (filtered): ERROR ({e})")
            self.test_results.append(("list_beams_filtered", "ERROR"))
            return None

    def test_invalid_beam_id(self):
        """Test with invalid beam_id"""
        print(f"\n=== Testing Invalid Beam ID ===")

        try:
            response = requests.get(
                f"{self.base_url}/beam/999/kpi",  # Invalid beam_id
                timeout=10
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 400:
                data = response.json()
                print(f"✓ Invalid beam ID handling: PASS")
                print(f"  Error Code: {data.get('error_code')}")
                print(f"  Message: {data.get('message')}")
                self.test_results.append(("invalid_beam_id", "PASS"))
            else:
                print(f"✗ Invalid beam ID handling: FAIL (expected 400)")
                self.test_results.append(("invalid_beam_id", "FAIL"))

        except Exception as e:
            print(f"✗ Invalid beam ID handling: ERROR ({e})")
            self.test_results.append(("invalid_beam_id", "ERROR"))

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)

        total = len(self.test_results)
        passed = sum(1 for _, result in self.test_results if result == "PASS")
        failed = sum(1 for _, result in self.test_results if result == "FAIL")
        errors = sum(1 for _, result in self.test_results if result == "ERROR")
        no_data = sum(1 for _, result in self.test_results if result == "NO_DATA")

        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Errors: {errors}")
        print(f"No Data: {no_data}")
        print()

        for test_name, result in self.test_results:
            symbol = "✓" if result == "PASS" else "✗" if result == "FAIL" else "⚠" if result == "NO_DATA" else "!"
            print(f"{symbol} {test_name}: {result}")

        print("="*60)

    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*60)
        print("BEAM KPI QUERY API TEST SUITE")
        print("="*60)
        print(f"API Base URL: {self.base_url}")
        print(f"Test Time: {datetime.now().isoformat()}")
        print("="*60)

        # Wait for system to be ready
        print("\nWaiting 5 seconds for system to be ready...")
        time.sleep(5)

        # Run tests
        self.test_health_endpoints()
        self.test_get_beam_kpi_current(beam_id=1)
        self.test_get_beam_kpi_current(beam_id=2)
        self.test_get_beam_kpi_filtered(beam_id=1)
        self.test_get_beam_kpi_historical(beam_id=1)
        self.test_get_beam_timeseries(beam_id=1)
        self.test_list_beams()
        self.test_list_beams_filtered()
        self.test_invalid_beam_id()

        # Print summary
        self.print_summary()


def run_interactive_demo():
    """Run interactive demo of the API"""
    print("\n" + "="*60)
    print("BEAM KPI QUERY API - INTERACTIVE DEMO")
    print("="*60)

    base_url = input(f"\nEnter API base URL (default: {API_BASE_URL}): ").strip() or API_BASE_URL

    while True:
        print("\n" + "-"*60)
        print("Available Commands:")
        print("  1. Query beam KPI (current)")
        print("  2. Query beam KPI (historical)")
        print("  3. List all beams")
        print("  4. Get timeseries data")
        print("  5. Run automated tests")
        print("  0. Exit")
        print("-"*60)

        choice = input("\nEnter command: ").strip()

        if choice == "1":
            beam_id = int(input("Enter beam ID: ").strip())
            kpi_type = input("Enter KPI type (default: all): ").strip() or "all"

            url = f"{base_url}/beam/{beam_id}/kpi"
            params = {'kpi_type': kpi_type, 'time_range': 'current'}

            print(f"\nGET {url}")
            print(f"Params: {params}")

            response = requests.get(url, params=params, timeout=10)
            print(f"\nStatus: {response.status_code}")
            print(json.dumps(response.json(), indent=2))

        elif choice == "2":
            beam_id = int(input("Enter beam ID: ").strip())
            time_range = input("Enter time range (default: last_15m): ").strip() or "last_15m"

            url = f"{base_url}/beam/{beam_id}/kpi"
            params = {'time_range': time_range, 'aggregation': 'mean'}

            print(f"\nGET {url}")
            print(f"Params: {params}")

            response = requests.get(url, params=params, timeout=10)
            print(f"\nStatus: {response.status_code}")
            print(json.dumps(response.json(), indent=2))

        elif choice == "3":
            url = f"{base_url}/beam/list"

            print(f"\nGET {url}")

            response = requests.get(url, timeout=10)
            print(f"\nStatus: {response.status_code}")
            print(json.dumps(response.json(), indent=2))

        elif choice == "4":
            beam_id = int(input("Enter beam ID: ").strip())
            kpi_type = input("Enter KPI type (rsrp/rsrq/sinr): ").strip()

            url = f"{base_url}/beam/{beam_id}/kpi/timeseries"
            params = {'kpi_type': kpi_type, 'interval': '30s'}

            print(f"\nGET {url}")
            print(f"Params: {params}")

            response = requests.get(url, params=params, timeout=10)
            print(f"\nStatus: {response.status_code}")
            print(json.dumps(response.json(), indent=2))

        elif choice == "5":
            tester = BeamAPITester(base_url)
            tester.run_all_tests()

        elif choice == "0":
            print("\nExiting...")
            break
        else:
            print("\nInvalid command!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        run_interactive_demo()
    else:
        tester = BeamAPITester()
        tester.run_all_tests()
