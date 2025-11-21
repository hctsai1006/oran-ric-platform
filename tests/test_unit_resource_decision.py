"""
Unit Tests for Resource Decision Logic
Tests the decision-making logic and serialization of resource decisions
"""

import pytest
import json
from datetime import datetime
from typing import Dict, Any


class PolicyEngine:
    """Simple policy engine for making resource decisions"""

    def __init__(self):
        """Initialize policy engine with default policies"""
        self.policies = {
            'beam_selection': self._beam_selection_policy,
            'prb_allocation': self._prb_allocation_policy,
            'handover_decision': self._handover_decision_policy
        }

    def make_decision(self, indication: Dict[str, Any], policy_type: str = 'beam_selection') -> Dict[str, Any]:
        """Make a resource decision based on indication and policy"""
        if policy_type not in self.policies:
            raise ValueError(f"Unknown policy type: {policy_type}")

        policy_func = self.policies[policy_type]
        decision = policy_func(indication)

        return decision

    @staticmethod
    def _beam_selection_policy(indication: Dict[str, Any]) -> Dict[str, Any]:
        """Select best beam based on L1-RSRP measurements"""
        measurements_by_name = {m['name']: m for m in indication['measurements']}

        # Select beam with highest RSRP
        best_beam = indication['beam_id']
        best_rsrp = measurements_by_name.get('L1-RSRP.beam', {}).get('value', -100.0)

        # In practice, would evaluate multiple beams from measurements
        # For now, use the beam from indication as baseline

        return {
            'timestamp': datetime.now().isoformat(),
            'ue_id': indication['ue_id'],
            'cell_id': indication['cell_id'],
            'decision_type': 'beam_selection',
            'parameters': {
                'beam_id': best_beam,
                'rsrp_value': best_rsrp,
                'confidence': 0.85 if best_rsrp > -100 else 0.65
            }
        }

    @staticmethod
    def _prb_allocation_policy(indication: Dict[str, Any]) -> Dict[str, Any]:
        """Allocate PRBs based on throughput demand"""
        measurements_by_name = {m['name']: m for m in indication['measurements']}

        throughput = measurements_by_name.get('DRB.UEThpDl', {}).get('value', 50.0)

        # Allocate PRBs based on throughput demand
        # Simple rule: 10% of 100 PRBs per Mbps, max 95% PRBs
        prb_allocation = int(min(95, max(10, throughput / 10 * 100 / 100 * 100)))

        return {
            'timestamp': datetime.now().isoformat(),
            'ue_id': indication['ue_id'],
            'cell_id': indication['cell_id'],
            'decision_type': 'prb_allocation',
            'parameters': {
                'prb_allocation': prb_allocation,
                'throughput_demand': throughput
            }
        }

    @staticmethod
    def _handover_decision_policy(indication: Dict[str, Any]) -> Dict[str, Any]:
        """Decide if handover is needed"""
        measurements_by_name = {m['name']: m for m in indication['measurements']}

        rsrp = measurements_by_name.get('UE.RSRP', {}).get('value', -100.0)
        sinr = measurements_by_name.get('UE.SINR', {}).get('value', 10.0)

        # Simple rule: if RSRP < -110 dBm or SINR < 5 dB, trigger handover
        needs_handover = rsrp < -110 or sinr < 5
        confidence = 0.9 if needs_handover else 0.1

        return {
            'timestamp': datetime.now().isoformat(),
            'ue_id': indication['ue_id'],
            'cell_id': indication['cell_id'],
            'decision_type': 'handover_decision',
            'parameters': {
                'needs_handover': needs_handover,
                'rsrp_value': rsrp,
                'sinr_value': sinr,
                'confidence': confidence
            }
        }


class TestResourceDecisionLogic:
    """Test suite for resource decision-making logic"""

    def test_beam_selection_decision_structure(self, test_data_factory):
        """Test beam selection decision has correct structure"""
        engine = PolicyEngine()
        indication = test_data_factory.create_kpi_indication()

        decision = engine.make_decision(indication, 'beam_selection')

        assert 'timestamp' in decision
        assert 'ue_id' in decision
        assert 'cell_id' in decision
        assert 'decision_type' in decision
        assert decision['decision_type'] == 'beam_selection'
        assert 'parameters' in decision

    def test_beam_selection_selects_valid_beam(self, test_data_factory):
        """Test beam selection returns a valid beam ID"""
        engine = PolicyEngine()

        for beam_id in [0, 3, 7]:
            indication = test_data_factory.create_kpi_indication(beam_id=beam_id)
            decision = engine.make_decision(indication, 'beam_selection')

            assert 'beam_id' in decision['parameters']
            selected_beam = decision['parameters']['beam_id']
            assert 0 <= selected_beam <= 7, f"Selected beam {selected_beam} outside valid range"

    def test_beam_selection_confidence_score(self, test_data_factory):
        """Test beam selection includes confidence score"""
        engine = PolicyEngine()
        indication = test_data_factory.create_kpi_indication(rsrp=-95.0)

        decision = engine.make_decision(indication, 'beam_selection')

        assert 'confidence' in decision['parameters']
        confidence = decision['parameters']['confidence']
        assert 0.0 <= confidence <= 1.0, f"Confidence {confidence} outside [0, 1] range"

    def test_prb_allocation_decision_structure(self, test_data_factory):
        """Test PRB allocation decision has correct structure"""
        engine = PolicyEngine()
        indication = test_data_factory.create_kpi_indication()

        decision = engine.make_decision(indication, 'prb_allocation')

        assert 'decision_type' in decision
        assert decision['decision_type'] == 'prb_allocation'
        assert 'parameters' in decision
        assert 'prb_allocation' in decision['parameters']

    def test_prb_allocation_realistic_values(self, test_data_factory):
        """Test PRB allocation produces realistic values"""
        engine = PolicyEngine()

        throughputs = [10.0, 50.0, 100.0]
        for throughput in throughputs:
            indication = test_data_factory.create_kpi_indication(throughput_dl=throughput)
            decision = engine.make_decision(indication, 'prb_allocation')

            prb = decision['parameters']['prb_allocation']
            assert 0 <= prb <= 100, f"PRB allocation {prb} outside valid range [0, 100]"

    def test_prb_allocation_higher_demand_more_prbs(self, test_data_factory):
        """Test higher throughput demand results in more PRBs"""
        engine = PolicyEngine()

        indication_low = test_data_factory.create_kpi_indication(throughput_dl=10.0)
        indication_high = test_data_factory.create_kpi_indication(throughput_dl=100.0)

        decision_low = engine.make_decision(indication_low, 'prb_allocation')
        decision_high = engine.make_decision(indication_high, 'prb_allocation')

        prb_low = decision_low['parameters']['prb_allocation']
        prb_high = decision_high['parameters']['prb_allocation']

        assert prb_high >= prb_low, "Higher throughput demand should allocate more PRBs"

    def test_handover_decision_structure(self, test_data_factory):
        """Test handover decision has correct structure"""
        engine = PolicyEngine()
        indication = test_data_factory.create_kpi_indication()

        decision = engine.make_decision(indication, 'handover_decision')

        assert 'decision_type' in decision
        assert decision['decision_type'] == 'handover_decision'
        assert 'parameters' in decision
        assert 'needs_handover' in decision['parameters']

    def test_handover_decision_boolean_flag(self, test_data_factory):
        """Test handover decision produces boolean needs_handover flag"""
        engine = PolicyEngine()

        indication_good = test_data_factory.create_kpi_indication(rsrp=-90.0, sinr=15.0)
        indication_bad = test_data_factory.create_kpi_indication(rsrp=-115.0, sinr=2.0)

        decision_good = engine.make_decision(indication_good, 'handover_decision')
        decision_bad = engine.make_decision(indication_bad, 'handover_decision')

        assert isinstance(decision_good['parameters']['needs_handover'], bool)
        assert isinstance(decision_bad['parameters']['needs_handover'], bool)

    def test_handover_decision_bad_conditions_trigger(self, test_data_factory):
        """Test handover is triggered under poor signal conditions"""
        engine = PolicyEngine()

        # Poor RSRP should trigger handover
        indication = test_data_factory.create_kpi_indication(rsrp=-120.0, sinr=15.0)
        decision = engine.make_decision(indication, 'handover_decision')

        assert decision['parameters']['needs_handover'] is True

    def test_handover_decision_good_conditions_no_trigger(self, test_data_factory):
        """Test handover is not triggered under good signal conditions"""
        engine = PolicyEngine()

        # Good RSRP and SINR should not trigger handover
        indication = test_data_factory.create_kpi_indication(rsrp=-80.0, sinr=20.0)
        decision = engine.make_decision(indication, 'handover_decision')

        assert decision['parameters']['needs_handover'] is False

    def test_decision_timestamp_is_iso_format(self, test_data_factory):
        """Test decision timestamp is in ISO 8601 format"""
        engine = PolicyEngine()
        indication = test_data_factory.create_kpi_indication()

        decision = engine.make_decision(indication, 'beam_selection')

        try:
            datetime.fromisoformat(decision['timestamp'])
        except ValueError:
            pytest.fail(f"Decision timestamp {decision['timestamp']} is not in ISO 8601 format")

    def test_decision_serialization_to_json(self, test_data_factory):
        """Test decision can be serialized to JSON"""
        engine = PolicyEngine()
        indication = test_data_factory.create_kpi_indication()

        decision = engine.make_decision(indication, 'beam_selection')

        # Should be JSON serializable
        json_str = json.dumps(decision)
        assert isinstance(json_str, str)

        # Should be deserializable back
        deserialized = json.loads(json_str)
        assert deserialized['ue_id'] == decision['ue_id']
        assert deserialized['decision_type'] == decision['decision_type']

    def test_unknown_policy_type_raises_error(self, test_data_factory):
        """Test unknown policy type raises ValueError"""
        engine = PolicyEngine()
        indication = test_data_factory.create_kpi_indication()

        with pytest.raises(ValueError, match="Unknown policy type"):
            engine.make_decision(indication, 'invalid_policy')

    def test_decision_preserves_ue_and_cell_ids(self, test_data_factory):
        """Test decision preserves UE and cell IDs from indication"""
        engine = PolicyEngine()

        for ue_id in ['ue_001', 'ue_002']:
            for cell_id in ['cell_001', 'cell_002']:
                indication = test_data_factory.create_kpi_indication(
                    ue_id=ue_id,
                    cell_id=cell_id
                )

                decision = engine.make_decision(indication, 'beam_selection')

                assert decision['ue_id'] == ue_id
                assert decision['cell_id'] == cell_id

    def test_all_policy_types_produce_valid_decisions(self, test_data_factory):
        """Test all policy types produce structurally valid decisions"""
        engine = PolicyEngine()
        indication = test_data_factory.create_kpi_indication()

        policy_types = ['beam_selection', 'prb_allocation', 'handover_decision']

        for policy_type in policy_types:
            decision = engine.make_decision(indication, policy_type)

            # Check common decision structure
            assert 'timestamp' in decision
            assert 'ue_id' in decision
            assert 'cell_id' in decision
            assert 'decision_type' in decision
            assert 'parameters' in decision
            assert isinstance(decision['parameters'], dict)


class TestResourceDecisionSerialization:
    """Test suite for resource decision serialization"""

    def test_decision_to_json_preserves_data(self, test_data_factory):
        """Test JSON serialization preserves all decision data"""
        engine = PolicyEngine()
        indication = test_data_factory.create_kpi_indication()

        original_decision = engine.make_decision(indication, 'beam_selection')
        json_str = json.dumps(original_decision)
        restored_decision = json.loads(json_str)

        assert restored_decision == original_decision

    def test_decision_json_is_valid_utf8(self, test_data_factory):
        """Test decision JSON is valid UTF-8"""
        engine = PolicyEngine()
        indication = test_data_factory.create_kpi_indication()

        decision = engine.make_decision(indication, 'beam_selection')
        json_str = json.dumps(decision)

        # Should be valid UTF-8
        try:
            json_str.encode('utf-8')
        except UnicodeEncodeError:
            pytest.fail("Decision JSON is not valid UTF-8")

    def test_decision_json_file_write_and_read(self, test_data_factory, temp_log_dir):
        """Test decision can be written to and read from file"""
        import os

        engine = PolicyEngine()
        indication = test_data_factory.create_kpi_indication()

        decision = engine.make_decision(indication, 'beam_selection')

        # Write to file
        filepath = os.path.join(temp_log_dir, 'decision.json')
        with open(filepath, 'w') as f:
            json.dump(decision, f)

        # Read from file
        with open(filepath, 'r') as f:
            loaded_decision = json.load(f)

        assert loaded_decision == decision
