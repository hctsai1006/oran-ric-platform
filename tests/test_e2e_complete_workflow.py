"""
End-to-End Tests for Complete O-RAN RIC Workflow
Tests the complete flow: E2-simulator → xApp → decision logging
"""

import pytest
import json
import time
import logging
from typing import Dict, Any, List
from datetime import datetime
import tempfile
import os

logger = logging.getLogger(__name__)


class DecisionLogger:
    """Logs decisions to file for audit trail"""

    def __init__(self, log_file: str):
        self.log_file = log_file
        self.decisions = []

    def log_decision(self, decision: Dict[str, Any]) -> bool:
        """Log decision to file"""
        try:
            self.decisions.append(decision)

            with open(self.log_file, 'a') as f:
                f.write(json.dumps(decision) + '\n')

            return True
        except Exception as e:
            logger.error(f"Failed to log decision: {e}")
            return False

    def read_decisions(self) -> List[Dict[str, Any]]:
        """Read decisions from log file"""
        decisions = []

        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    if line.strip():
                        decisions.append(json.loads(line))
        except FileNotFoundError:
            pass

        return decisions

    def clear_log(self):
        """Clear log file"""
        if os.path.exists(self.log_file):
            os.remove(self.log_file)
        self.decisions = []


class E2ToXAppToLogWorkflow:
    """Complete workflow from E2 to logging"""

    def __init__(self, log_file: str):
        self.logger = DecisionLogger(log_file)
        self.decisions = []
        self.errors = []

    def process_indication(self, indication: Dict[str, Any]) -> bool:
        """Process single indication through complete workflow"""
        try:
            # Validate indication
            if not self._validate_indication(indication):
                return False

            # Make decision
            decision = self._make_decision(indication)

            # Log decision
            if not self.logger.log_decision(decision):
                return False

            self.decisions.append(decision)
            return True

        except Exception as e:
            self.errors.append(str(e))
            logger.error(f"Error processing indication: {e}")
            return False

    def process_indication_batch(self, indications: List[Dict[str, Any]]) -> int:
        """Process batch of indications"""
        success_count = 0

        for indication in indications:
            if self.process_indication(indication):
                success_count += 1

        return success_count

    @staticmethod
    def _validate_indication(indication: Dict[str, Any]) -> bool:
        """Validate indication"""
        required_fields = ['timestamp', 'cell_id', 'ue_id']
        return all(field in indication for field in required_fields)

    @staticmethod
    def _make_decision(indication: Dict[str, Any]) -> Dict[str, Any]:
        """Make decision based on indication"""
        measurements = {m['name']: m.get('value', 0)
                       for m in indication.get('measurements', [])
                       if isinstance(m, dict)}

        rsrp = measurements.get('UE.RSRP', -100.0)
        sinr = measurements.get('UE.SINR', 10.0)

        return {
            'timestamp': datetime.now().isoformat(),
            'ue_id': indication['ue_id'],
            'cell_id': indication['cell_id'],
            'decision_type': 'beam_selection',
            'parameters': {
                'beam_id': indication.get('beam_id', 0),
                'rsrp_value': rsrp,
                'sinr_value': sinr,
                'confidence': 0.85 if rsrp > -110 else 0.65
            }
        }

    def get_decision_count(self) -> int:
        """Get number of decisions made"""
        return len(self.decisions)

    def get_error_count(self) -> int:
        """Get number of errors"""
        return len(self.errors)


class TestCompleteE2ToXAppWorkflow:
    """Test complete E2 to xApp workflow"""

    def test_single_indication_complete_workflow(self, test_data_factory, temp_log_dir):
        """Test processing single indication through complete workflow"""
        log_file = os.path.join(temp_log_dir, 'decisions.log')
        workflow = E2ToXAppToLogWorkflow(log_file)

        indication = test_data_factory.create_kpi_indication()

        result = workflow.process_indication(indication)

        assert result is True
        assert workflow.get_decision_count() == 1
        assert workflow.get_error_count() == 0

    def test_multiple_indications_workflow(self, test_data_factory, temp_log_dir):
        """Test processing multiple indications"""
        log_file = os.path.join(temp_log_dir, 'decisions.log')
        workflow = E2ToXAppToLogWorkflow(log_file)

        indications = [
            test_data_factory.create_kpi_indication(ue_id=f'ue_{i:03d}')
            for i in range(5)
        ]

        success_count = workflow.process_indication_batch(indications)

        assert success_count == 5
        assert workflow.get_decision_count() == 5
        assert workflow.get_error_count() == 0

    def test_decisions_persisted_to_log(self, test_data_factory, temp_log_dir):
        """Test decisions are persisted to log file"""
        log_file = os.path.join(temp_log_dir, 'decisions.log')
        workflow = E2ToXAppToLogWorkflow(log_file)

        indications = [
            test_data_factory.create_kpi_indication(ue_id=f'ue_{i:03d}')
            for i in range(3)
        ]

        workflow.process_indication_batch(indications)

        # Read decisions from log
        logged_decisions = workflow.logger.read_decisions()

        assert len(logged_decisions) == 3
        assert all('ue_id' in d for d in logged_decisions)
        assert all('decision_type' in d for d in logged_decisions)

    def test_workflow_with_invalid_indication(self, temp_log_dir):
        """Test workflow handles invalid indication"""
        log_file = os.path.join(temp_log_dir, 'decisions.log')
        workflow = E2ToXAppToLogWorkflow(log_file)

        invalid_indication = {}  # Missing required fields

        result = workflow.process_indication(invalid_indication)

        assert result is False

    def test_decision_log_format(self, test_data_factory, temp_log_dir):
        """Test decision log has correct format"""
        log_file = os.path.join(temp_log_dir, 'decisions.log')
        workflow = E2ToXAppToLogWorkflow(log_file)

        indication = test_data_factory.create_kpi_indication()
        workflow.process_indication(indication)

        # Read log file
        with open(log_file, 'r') as f:
            log_line = f.readline()

        logged_decision = json.loads(log_line)

        assert isinstance(logged_decision, dict)
        assert 'timestamp' in logged_decision
        assert 'ue_id' in logged_decision
        assert 'cell_id' in logged_decision
        assert 'decision_type' in logged_decision
        assert 'parameters' in logged_decision

    def test_multiple_ues_independent_processing(self, test_data_factory, temp_log_dir):
        """Test multiple UEs are processed independently"""
        log_file = os.path.join(temp_log_dir, 'decisions.log')
        workflow = E2ToXAppToLogWorkflow(log_file)

        ues = ['ue_001', 'ue_002', 'ue_003']

        for ue_id in ues:
            indication = test_data_factory.create_kpi_indication(ue_id=ue_id)
            result = workflow.process_indication(indication)
            assert result is True

        # Verify all UEs were processed
        logged_decisions = workflow.logger.read_decisions()
        logged_ues = {d['ue_id'] for d in logged_decisions}

        assert logged_ues == set(ues)

    def test_workflow_preserves_measurement_data(self, test_data_factory, temp_log_dir):
        """Test workflow preserves measurement data in decision"""
        log_file = os.path.join(temp_log_dir, 'decisions.log')
        workflow = E2ToXAppToLogWorkflow(log_file)

        rsrp_value = -92.5
        sinr_value = 18.3

        indication = test_data_factory.create_kpi_indication(
            rsrp=rsrp_value,
            sinr=sinr_value
        )

        workflow.process_indication(indication)

        logged_decisions = workflow.logger.read_decisions()
        decision = logged_decisions[0]

        # Decision should preserve measurement values
        assert decision['parameters']['rsrp_value'] == rsrp_value
        assert decision['parameters']['sinr_value'] == sinr_value


class TestE2XAppLogConsistency:
    """Test consistency across E2, xApp, and logging"""

    def test_ue_cell_consistency_throughout_workflow(self, test_data_factory, temp_log_dir):
        """Test UE and cell IDs are consistent throughout workflow"""
        log_file = os.path.join(temp_log_dir, 'decisions.log')
        workflow = E2ToXAppToLogWorkflow(log_file)

        ue_id = 'ue_test_001'
        cell_id = 'cell_test_001'

        indication = test_data_factory.create_kpi_indication(
            ue_id=ue_id,
            cell_id=cell_id
        )

        workflow.process_indication(indication)

        # Check in-memory decisions
        assert workflow.decisions[0]['ue_id'] == ue_id
        assert workflow.decisions[0]['cell_id'] == cell_id

        # Check logged decisions
        logged_decisions = workflow.logger.read_decisions()
        assert logged_decisions[0]['ue_id'] == ue_id
        assert logged_decisions[0]['cell_id'] == cell_id

    def test_timestamp_ordering_in_log(self, test_data_factory, temp_log_dir):
        """Test decisions are logged with ordered timestamps"""
        log_file = os.path.join(temp_log_dir, 'decisions.log')
        workflow = E2ToXAppToLogWorkflow(log_file)

        num_indications = 10

        for i in range(num_indications):
            indication = test_data_factory.create_kpi_indication()
            workflow.process_indication(indication)
            time.sleep(0.01)  # Small delay to ensure timestamp differences

        logged_decisions = workflow.logger.read_decisions()

        # Timestamps should be non-decreasing
        timestamps = [d['timestamp'] for d in logged_decisions]
        assert timestamps == sorted(timestamps)

    def test_decision_completeness(self, test_data_factory, temp_log_dir):
        """Test all decisions are logged with complete data"""
        log_file = os.path.join(temp_log_dir, 'decisions.log')
        workflow = E2ToXAppToLogWorkflow(log_file)

        indications = [
            test_data_factory.create_kpi_indication(ue_id=f'ue_{i:03d}')
            for i in range(5)
        ]

        workflow.process_indication_batch(indications)

        logged_decisions = workflow.logger.read_decisions()

        # All decisions should have same structure
        required_fields = {'timestamp', 'ue_id', 'cell_id', 'decision_type', 'parameters'}

        for decision in logged_decisions:
            assert required_fields.issubset(set(decision.keys()))

    def test_beam_selection_consistency(self, test_data_factory, temp_log_dir):
        """Test beam selection is consistent across workflow"""
        log_file = os.path.join(temp_log_dir, 'decisions.log')
        workflow = E2ToXAppToLogWorkflow(log_file)

        for beam_id in [0, 1, 2, 3]:
            indication = test_data_factory.create_kpi_indication(beam_id=beam_id)
            workflow.process_indication(indication)

        logged_decisions = workflow.logger.read_decisions()

        # Each decision should preserve its beam ID
        for i, decision in enumerate(logged_decisions):
            assert decision['parameters']['beam_id'] == i


class TestE2XAppEndToEndScenarios:
    """Test complete end-to-end scenarios"""

    def test_continuous_operation_scenario(self, test_data_factory, temp_log_dir):
        """Test continuous operation with multiple indications"""
        log_file = os.path.join(temp_log_dir, 'decisions.log')
        workflow = E2ToXAppToLogWorkflow(log_file)

        # Simulate 30 seconds of operation (1 indication per second)
        duration_sec = 3
        indication_interval = 0.1

        start_time = time.time()
        indication_count = 0

        while time.time() - start_time < duration_sec:
            indication = test_data_factory.create_kpi_indication()
            result = workflow.process_indication(indication)

            if result:
                indication_count += 1

            time.sleep(indication_interval)

        logger.info(f"Processed {indication_count} indications in {duration_sec}s")

        # Should process reasonable number of indications
        assert indication_count > 0
        assert workflow.get_error_count() == 0

    def test_handover_scenario(self, test_data_factory, temp_log_dir):
        """Test handover scenario"""
        log_file = os.path.join(temp_log_dir, 'decisions.log')
        workflow = E2ToXAppToLogWorkflow(log_file)

        # Initial cell
        indication = test_data_factory.create_kpi_indication(
            ue_id='ue_001',
            cell_id='cell_001',
            rsrp=-90.0
        )
        workflow.process_indication(indication)

        # Signal degradation
        indication = test_data_factory.create_kpi_indication(
            ue_id='ue_001',
            cell_id='cell_001',
            rsrp=-115.0
        )
        workflow.process_indication(indication)

        # Handover to new cell
        indication = test_data_factory.create_kpi_indication(
            ue_id='ue_001',
            cell_id='cell_002',
            rsrp=-95.0
        )
        workflow.process_indication(indication)

        logged_decisions = workflow.logger.read_decisions()

        # Should have 3 decisions
        assert len(logged_decisions) == 3
        assert logged_decisions[0]['cell_id'] == 'cell_001'
        assert logged_decisions[1]['cell_id'] == 'cell_001'
        assert logged_decisions[2]['cell_id'] == 'cell_002'

    def test_multi_ue_scenario(self, test_data_factory, temp_log_dir):
        """Test multi-UE scenario"""
        log_file = os.path.join(temp_log_dir, 'decisions.log')
        workflow = E2ToXAppToLogWorkflow(log_file)

        ues = ['ue_001', 'ue_002', 'ue_003']

        # Process 10 rounds of indications for all UEs
        for round_num in range(10):
            for ue_id in ues:
                indication = test_data_factory.create_kpi_indication(ue_id=ue_id)
                workflow.process_indication(indication)

        logged_decisions = workflow.logger.read_decisions()

        # Should have 30 decisions total
        assert len(logged_decisions) == 30

        # Each UE should appear 10 times
        for ue_id in ues:
            ue_decisions = [d for d in logged_decisions if d['ue_id'] == ue_id]
            assert len(ue_decisions) == 10

    def test_beam_selection_sequence(self, test_data_factory, temp_log_dir):
        """Test beam selection across multiple indications"""
        log_file = os.path.join(temp_log_dir, 'decisions.log')
        workflow = E2ToXAppToLogWorkflow(log_file)

        ue_id = 'ue_beam_test'

        # Process indications with different beams
        beam_sequence = [0, 1, 2, 3, 2, 1, 0]

        for beam_id in beam_sequence:
            indication = test_data_factory.create_kpi_indication(
                ue_id=ue_id,
                beam_id=beam_id
            )
            workflow.process_indication(indication)

        logged_decisions = workflow.logger.read_decisions()

        # Verify beam sequence is preserved
        logged_beams = [d['parameters']['beam_id'] for d in logged_decisions]
        assert logged_beams == beam_sequence
