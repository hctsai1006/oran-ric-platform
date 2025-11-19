"""
E2E Test: Complete Data Flow
Tests: E2 Simulator → E2Term → KPIMON → Prometheus
"""
import requests
import time
import sys


def test_e2_to_prometheus_flow():
    """
    Test complete E2E data flow
    Verifies that metrics from E2 Simulator reach Prometheus
    """
    print("========================================")
    print("E2E Test: Complete Data Flow")
    print("========================================")
    print("")

    # Wait for E2 Simulator to send data
    print("[1/2] Waiting for E2 Simulator to generate data (10 seconds)...")
    time.sleep(10)

    # Check Prometheus for KPIMON metrics
    print("[2/2] Querying Prometheus for KPIMON metrics...")

    try:
        response = requests.get(
            'http://localhost:9090/api/v1/query',
            params={'query': 'kpimon_messages_received_total'},
            timeout=10
        )

        if response.status_code != 200:
            print(f"❌ Prometheus query failed with status {response.status_code}")
            return False

        data = response.json().get('data', {}).get('result', [])

        if len(data) == 0:
            print("❌ No KPIMON metrics found in Prometheus")
            print("   This is expected if RMR migration is not yet complete")
            return False

        # Check if messages were received
        metric_value = float(data[0]['value'][1])

        if metric_value > 0:
            print(f"  ✅ KPIMON metrics found: {metric_value} messages received")
            print("")
            print("========================================")
            print("✅ E2E test passed")
            print("========================================")
            return True
        else:
            print("❌ No messages received by KPIMON")
            return False

    except requests.RequestException as e:
        print(f"❌ Failed to connect to Prometheus: {e}")
        print("   Make sure to port-forward Prometheus first:")
        print("   kubectl port-forward -n ricplt svc/r4-infrastructure-prometheus-server 9090:80")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == '__main__':
    success = test_e2_to_prometheus_flow()
    sys.exit(0 if success else 1)
