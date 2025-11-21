"""
Pytest configuration and shared fixtures for O-RAN RIC integration tests
"""

import pytest
import json
import time
import logging
import tempfile
import os
from typing import Dict, Any
from datetime import datetime

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class TestDataFactory:
    """Factory for generating test data"""

    @staticmethod
    def create_kpi_indication(
        cell_id: str = "cell_001",
        ue_id: str = "ue_001",
        beam_id: int = 0,
        rsrp: float = -95.0,
        sinr: float = 15.0,
        throughput_dl: float = 50.0
    ) -> Dict[str, Any]:
        """Create a KPI indication for testing"""
        return {
            'timestamp': datetime.now().isoformat(),
            'cell_id': cell_id,
            'ue_id': ue_id,
            'beam_id': beam_id,
            'measurements': [
                {
                    'name': 'UE.RSRP',
                    'value': rsrp
                },
                {
                    'name': 'UE.SINR',
                    'value': sinr
                },
                {
                    'name': 'DRB.UEThpDl',
                    'value': throughput_dl
                },
                {
                    'name': 'L1-RSRP.beam',
                    'value': rsrp * 0.95,
                    'beam_id': beam_id
                },
                {
                    'name': 'L1-SINR.beam',
                    'value': sinr * 0.95,
                    'beam_id': beam_id
                }
            ],
            'indication_sn': int(time.time() * 1000),
            'indication_type': 'report'
        }

    @staticmethod
    def create_handover_event(
        ue_id: str = "ue_001",
        source_cell: str = "cell_001",
        target_cell: str = "cell_002",
        rsrp: float = -95.0
    ) -> Dict[str, Any]:
        """Create a handover event for testing"""
        return {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'handover_request',
            'ue_id': ue_id,
            'source_cell': source_cell,
            'target_cell': target_cell,
            'rsrp': rsrp,
            'rsrq': -10.0,
            'trigger': 'A3_event'
        }

    @staticmethod
    def create_resource_decision(
        ue_id: str = "ue_001",
        cell_id: str = "cell_001",
        decision_type: str = "beam_selection",
        beam_id: int = 0,
        prb_allocation: int = 100,
        timestamp: str = None
    ) -> Dict[str, Any]:
        """Create a resource decision for testing"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        return {
            'timestamp': timestamp,
            'ue_id': ue_id,
            'cell_id': cell_id,
            'decision_type': decision_type,
            'parameters': {
                'beam_id': beam_id,
                'prb_allocation': prb_allocation
            }
        }


@pytest.fixture
def test_data_factory():
    """Provide test data factory"""
    return TestDataFactory()


@pytest.fixture
def temp_log_dir():
    """Provide temporary directory for test logs"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Provide test configuration"""
    return {
        'xapp_http_port': 8081,
        'simulator_host': 'localhost',
        'simulator_port': 8082,
        'decision_log_path': '/tmp/xapp_decisions.log',
        'http_timeout': 5,
        'indication_interval': 1,
        'cells': ['cell_001', 'cell_002', 'cell_003'],
        'ues': ['ue_001', 'ue_002', 'ue_003'],
        'beams_per_cell': 8,
        'performance_threshold': {
            'decision_latency_ms': 1000,  # 1 second
            'throughput_indications_per_sec': 10
        }
    }


@pytest.fixture(scope="session")
def log_test_results(request):
    """Log test results at the end of session"""
    yield

    # Collect test results
    session = request.session
    if hasattr(session, 'testsfailed'):
        logger.info(f"Test session completed - Failed: {session.testsfailed}, "
                   f"Passed: {session.testspassed}")
