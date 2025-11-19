"""
DBaaS Connection Test
Tests DBaaS connectivity to Redis backend
"""
import pytest
import redis
import sys


def test_dbaas_connection():
    """Test DBaaS can connect to Redis"""
    try:
        client = redis.Redis(
            host='dbaas-tcp.ricplt.svc.cluster.local',
            port=6379,
            socket_connect_timeout=5
        )

        # Test PING
        assert client.ping(), "Redis PING failed"

        # Test SET
        assert client.set('test_key', 'test_value'), "Redis SET failed"

        # Test GET
        value = client.get('test_key')
        assert value == b'test_value', f"Expected b'test_value', got {value}"

        # Cleanup
        client.delete('test_key')

        print("✅ DBaaS connection test passed")
        return True

    except redis.ConnectionError as e:
        print(f"❌ DBaaS connection failed: {e}")
        return False
    except AssertionError as e:
        print(f"❌ DBaaS assertion failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == '__main__':
    success = test_dbaas_connection()
    sys.exit(0 if success else 1)
