"""
Unit Tests for E2 Indication Parsing
Tests the parsing and validation of E2 indications from E2-simulator
"""

import pytest
import json
from datetime import datetime


class TestE2IndicationParsing:
    """Test suite for E2 indication message parsing"""

    def test_valid_kpi_indication_structure(self, test_data_factory):
        """Test parsing valid KPI indication with all required fields"""
        indication = test_data_factory.create_kpi_indication()

        # Verify all required fields are present
        assert 'timestamp' in indication
        assert 'cell_id' in indication
        assert 'ue_id' in indication
        assert 'beam_id' in indication
        assert 'measurements' in indication
        assert 'indication_type' in indication

        # Verify field types
        assert isinstance(indication['timestamp'], str)
        assert isinstance(indication['cell_id'], str)
        assert isinstance(indication['ue_id'], str)
        assert isinstance(indication['beam_id'], int)
        assert isinstance(indication['measurements'], list)

    def test_measurements_array_structure(self, test_data_factory):
        """Test measurements array contains valid measurement objects"""
        indication = test_data_factory.create_kpi_indication()
        measurements = indication['measurements']

        assert len(measurements) > 0, "Measurements array should not be empty"

        for measurement in measurements:
            assert 'name' in measurement, "Each measurement must have a name"
            assert 'value' in measurement, "Each measurement must have a value"
            assert isinstance(measurement['name'], str)
            assert isinstance(measurement['value'], (int, float))

    def test_beam_specific_measurements(self, test_data_factory):
        """Test beam-specific L1 measurements are present"""
        indication = test_data_factory.create_kpi_indication(beam_id=3)

        measurements_by_name = {m['name']: m for m in indication['measurements']}

        # Verify beam-specific measurements
        assert 'L1-RSRP.beam' in measurements_by_name
        assert 'L1-SINR.beam' in measurements_by_name

        # Verify beam ID is associated with beam measurements
        assert measurements_by_name['L1-RSRP.beam']['beam_id'] == 3
        assert measurements_by_name['L1-SINR.beam']['beam_id'] == 3

    def test_rsrp_value_ranges(self, test_data_factory):
        """Test RSRP values are within expected range"""
        # Typical RSRP range: -140 to -44 dBm
        indication = test_data_factory.create_kpi_indication(rsrp=-100.0)

        measurements_by_name = {m['name']: m for m in indication['measurements']}
        rsrp_value = measurements_by_name['UE.RSRP']['value']

        assert -140 <= rsrp_value <= -44, f"RSRP {rsrp_value} outside expected range"

    def test_sinr_value_ranges(self, test_data_factory):
        """Test SINR values are within expected range"""
        # Typical SINR range: -20 to 40 dB
        indication = test_data_factory.create_kpi_indication(sinr=15.0)

        measurements_by_name = {m['name']: m for m in indication['measurements']}
        sinr_value = measurements_by_name['UE.SINR']['value']

        assert -20 <= sinr_value <= 40, f"SINR {sinr_value} outside expected range"

    def test_throughput_value_ranges(self, test_data_factory):
        """Test throughput values are realistic (0-1000 Mbps)"""
        indication = test_data_factory.create_kpi_indication(throughput_dl=75.5)

        measurements_by_name = {m['name']: m for m in indication['measurements']}
        throughput = measurements_by_name['DRB.UEThpDl']['value']

        assert 0 <= throughput <= 1000, f"Throughput {throughput} outside expected range"

    def test_beam_id_valid_range(self, test_data_factory):
        """Test beam_id is within valid range (0-7 for 5G NR)"""
        for beam_id in [0, 3, 7]:
            indication = test_data_factory.create_kpi_indication(beam_id=beam_id)
            assert 0 <= indication['beam_id'] <= 7, f"Beam ID {beam_id} outside valid range"

    def test_timestamp_iso_format(self, test_data_factory):
        """Test timestamp is in ISO 8601 format"""
        indication = test_data_factory.create_kpi_indication()
        timestamp = indication['timestamp']

        # Should be parseable as ISO format
        try:
            datetime.fromisoformat(timestamp)
        except ValueError:
            pytest.fail(f"Timestamp {timestamp} is not in ISO 8601 format")

    def test_handover_event_structure(self, test_data_factory):
        """Test handover event has required fields"""
        event = test_data_factory.create_handover_event()

        assert 'timestamp' in event
        assert 'event_type' in event
        assert event['event_type'] == 'handover_request'
        assert 'ue_id' in event
        assert 'source_cell' in event
        assert 'target_cell' in event
        assert 'trigger' in event

        # Verify source and target cells are different
        assert event['source_cell'] != event['target_cell']

    def test_indication_serialization_to_json(self, test_data_factory):
        """Test indication can be serialized to JSON"""
        indication = test_data_factory.create_kpi_indication()

        # Should be JSON serializable
        json_str = json.dumps(indication)
        assert isinstance(json_str, str)

        # Should be deserializable back
        deserialized = json.loads(json_str)
        assert deserialized['cell_id'] == indication['cell_id']
        assert deserialized['ue_id'] == indication['ue_id']

    def test_missing_required_field_detection(self, test_data_factory):
        """Test detection of missing required fields"""
        indication = test_data_factory.create_kpi_indication()

        # Remove a required field and verify detection
        del indication['ue_id']

        # Check that validation would catch this
        required_fields = {'timestamp', 'cell_id', 'ue_id', 'beam_id', 'measurements', 'indication_type'}
        present_fields = set(indication.keys())
        missing_fields = required_fields - present_fields

        assert len(missing_fields) > 0, "Should detect missing ue_id"
        assert 'ue_id' in missing_fields

    def test_multiple_beam_measurements(self, test_data_factory):
        """Test indication contains measurements for multiple metrics"""
        indication = test_data_factory.create_kpi_indication()

        measurements_by_name = {m['name']: m for m in indication['measurements']}

        # Verify multiple different metrics are present
        expected_metrics = [
            'UE.RSRP', 'UE.SINR', 'DRB.UEThpDl',
            'L1-RSRP.beam', 'L1-SINR.beam'
        ]

        for metric in expected_metrics:
            assert metric in measurements_by_name, f"Missing metric {metric}"

    def test_indication_sn_monotonic_increasing(self, test_data_factory):
        """Test indication sequence number increases over time"""
        indication1 = test_data_factory.create_kpi_indication()
        indication2 = test_data_factory.create_kpi_indication()

        assert indication2['indication_sn'] >= indication1['indication_sn'], \
            "Indication SN should be monotonically increasing"

    def test_cell_ue_beam_combination_valid(self, test_data_factory):
        """Test valid combinations of cell, UE, and beam IDs"""
        cells = ['cell_001', 'cell_002', 'cell_003']
        ues = ['ue_001', 'ue_002', 'ue_003']
        beams = [0, 1, 2, 3, 4, 5, 6, 7]

        for cell in cells:
            for ue in ues:
                for beam in beams:
                    indication = test_data_factory.create_kpi_indication(
                        cell_id=cell,
                        ue_id=ue,
                        beam_id=beam
                    )

                    assert indication['cell_id'] == cell
                    assert indication['ue_id'] == ue
                    assert indication['beam_id'] == beam


class TestE2IndicationValidation:
    """Test suite for E2 indication validation logic"""

    def test_validate_kpi_indication_valid(self, test_data_factory):
        """Test validation passes for valid indication"""
        indication = test_data_factory.create_kpi_indication()
        is_valid = self._validate_indication(indication)
        assert is_valid is True

    def test_validate_kpi_indication_invalid_rsrp_range(self, test_data_factory):
        """Test validation fails for RSRP outside acceptable range"""
        indication = test_data_factory.create_kpi_indication(rsrp=-500.0)  # Invalid
        is_valid = self._validate_indication(indication)
        assert is_valid is False

    def test_validate_kpi_indication_invalid_sinr_range(self, test_data_factory):
        """Test validation fails for SINR outside acceptable range"""
        indication = test_data_factory.create_kpi_indication(sinr=100.0)  # Invalid
        is_valid = self._validate_indication(indication)
        assert is_valid is False

    def test_validate_missing_timestamp(self, test_data_factory):
        """Test validation fails when timestamp is missing"""
        indication = test_data_factory.create_kpi_indication()
        del indication['timestamp']
        is_valid = self._validate_indication(indication)
        assert is_valid is False

    def test_validate_empty_measurements(self, test_data_factory):
        """Test validation fails with empty measurements array"""
        indication = test_data_factory.create_kpi_indication()
        indication['measurements'] = []
        is_valid = self._validate_indication(indication)
        assert is_valid is False

    @staticmethod
    def _validate_indication(indication: dict) -> bool:
        """Simple validation logic for testing"""
        # Check required fields
        required_fields = ['timestamp', 'cell_id', 'ue_id', 'beam_id', 'measurements']
        if not all(field in indication for field in required_fields):
            return False

        # Check measurements array
        if not indication.get('measurements') or len(indication['measurements']) == 0:
            return False

        # Check value ranges
        measurements_by_name = {m['name']: m for m in indication['measurements']}

        if 'UE.RSRP' in measurements_by_name:
            rsrp = measurements_by_name['UE.RSRP']['value']
            if rsrp < -140 or rsrp > -44:
                return False

        if 'UE.SINR' in measurements_by_name:
            sinr = measurements_by_name['UE.SINR']['value']
            if sinr < -20 or sinr > 40:
                return False

        return True
