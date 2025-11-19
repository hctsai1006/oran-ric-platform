#!/usr/bin/env python3
"""
Beam KPI Query API for KPIMON xApp
Provides RESTful API endpoints for querying beam-specific KPI measurements

Author: O-RAN RIC Platform Team
Date: 2025-11-19
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Blueprint, jsonify, request
import redis
from influxdb_client import InfluxDBClient
from influxdb_client.client.query_api import QueryApi

logger = logging.getLogger(__name__)

# Create Flask Blueprint for beam API
beam_api = Blueprint('beam_api', __name__, url_prefix='/api')


class BeamQueryService:
    """Service for querying beam-specific KPI data"""

    def __init__(self, redis_client: redis.Redis, influx_client: Optional[InfluxDBClient],
                 influx_org: str, influx_bucket: str):
        """
        Initialize Beam Query Service

        Args:
            redis_client: Redis client for real-time data
            influx_client: InfluxDB client for historical data
            influx_org: InfluxDB organization
            influx_bucket: InfluxDB bucket name
        """
        self.redis = redis_client
        self.influx = influx_client
        self.influx_org = influx_org
        self.influx_bucket = influx_bucket
        self.query_api: Optional[QueryApi] = None

        if self.influx:
            self.query_api = self.influx.query_api()

        # KPI quality thresholds
        self.quality_thresholds = {
            'rsrp': {
                'excellent': -85,
                'good': -95,
                'fair': -105,
                'poor': -110
            },
            'rsrq': {
                'excellent': -8,
                'good': -10,
                'fair': -13,
                'poor': -15
            },
            'sinr': {
                'excellent': 20,
                'good': 13,
                'fair': 8,
                'poor': 3
            }
        }

    def assess_quality(self, kpi_type: str, value: float) -> str:
        """Assess KPI quality based on thresholds"""
        if kpi_type not in self.quality_thresholds:
            return 'unknown'

        thresholds = self.quality_thresholds[kpi_type]

        if kpi_type == 'rsrp' or kpi_type == 'rsrq':
            # Lower values are worse
            if value >= thresholds['excellent']:
                return 'excellent'
            elif value >= thresholds['good']:
                return 'good'
            elif value >= thresholds['fair']:
                return 'fair'
            else:
                return 'poor'
        else:
            # Higher values are better (SINR)
            if value >= thresholds['excellent']:
                return 'excellent'
            elif value >= thresholds['good']:
                return 'good'
            elif value >= thresholds['fair']:
                return 'fair'
            else:
                return 'poor'

    def get_current_beam_kpi(self, beam_id: int, kpi_types: List[str],
                             cell_id: Optional[str] = None,
                             ue_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current KPI measurements for a beam from Redis

        Args:
            beam_id: Beam identifier
            kpi_types: List of KPI types to retrieve
            cell_id: Optional cell ID filter
            ue_id: Optional UE ID filter

        Returns:
            Dictionary with beam KPI measurements
        """
        try:
            # Build Redis key pattern
            if cell_id:
                pattern = f"kpi:beam:{beam_id}:cell:{cell_id}:*"
            else:
                pattern = f"kpi:beam:{beam_id}:*"

            # Get all matching keys
            keys = self.redis.keys(pattern)

            if not keys:
                return None

            # Organize data
            data = {
                'signal_quality': {},
                'throughput': {},
                'resource_utilization': {},
                'packet_loss': {},
                'metadata': {}
            }

            # Fetch and parse KPI data
            for key in keys:
                kpi_json = self.redis.get(key)
                if not kpi_json:
                    continue

                kpi_data = json.loads(kpi_json)
                kpi_name = kpi_data.get('kpi_name')
                kpi_value = kpi_data.get('kpi_value')
                timestamp = kpi_data.get('timestamp')

                # Map KPIs to response structure
                if kpi_name == 'UE.RSRP':
                    data['signal_quality']['rsrp'] = {
                        'value': kpi_value,
                        'unit': 'dBm',
                        'quality': self.assess_quality('rsrp', kpi_value),
                        'timestamp': timestamp
                    }
                elif kpi_name == 'UE.RSRQ':
                    data['signal_quality']['rsrq'] = {
                        'value': kpi_value,
                        'unit': 'dB',
                        'quality': self.assess_quality('rsrq', kpi_value),
                        'timestamp': timestamp
                    }
                elif kpi_name == 'UE.SINR':
                    data['signal_quality']['sinr'] = {
                        'value': kpi_value,
                        'unit': 'dB',
                        'quality': self.assess_quality('sinr', kpi_value),
                        'timestamp': timestamp
                    }
                elif kpi_name == 'DRB.UEThpDl':
                    data['throughput']['downlink'] = {
                        'value': kpi_value,
                        'unit': 'Mbps',
                        'timestamp': timestamp
                    }
                elif kpi_name == 'DRB.UEThpUl':
                    data['throughput']['uplink'] = {
                        'value': kpi_value,
                        'unit': 'Mbps',
                        'timestamp': timestamp
                    }
                elif kpi_name == 'RRU.PrbUsedDl':
                    data['resource_utilization']['prb_usage_dl'] = {
                        'value': kpi_value,
                        'unit': 'percentage',
                        'timestamp': timestamp
                    }
                elif kpi_name == 'RRU.PrbUsedUl':
                    data['resource_utilization']['prb_usage_ul'] = {
                        'value': kpi_value,
                        'unit': 'percentage',
                        'timestamp': timestamp
                    }
                elif kpi_name == 'DRB.PacketLossDl':
                    data['packet_loss']['downlink'] = {
                        'value': kpi_value,
                        'unit': 'percentage',
                        'timestamp': timestamp
                    }
                elif kpi_name == 'DRB.PacketLossUl':
                    data['packet_loss']['uplink'] = {
                        'value': kpi_value,
                        'unit': 'percentage',
                        'timestamp': timestamp
                    }

                # Add metadata
                if 'metadata' not in data or not data['metadata']:
                    data['metadata'] = {
                        'cell_id': kpi_data.get('cell_id'),
                        'beam_id': beam_id,
                        'ue_count': self._get_ue_count(beam_id, kpi_data.get('cell_id'))
                    }

            # Remove empty categories
            data = {k: v for k, v in data.items() if v}

            return data

        except Exception as e:
            logger.error(f"Error getting current beam KPI: {e}")
            raise

    def get_historical_beam_kpi(self, beam_id: int, kpi_types: List[str],
                                time_range: str, aggregation: str) -> Dict[str, Any]:
        """
        Get historical KPI measurements for a beam from InfluxDB

        Args:
            beam_id: Beam identifier
            kpi_types: List of KPI types to retrieve
            time_range: Time range (last_5m, last_15m, last_1h, last_24h)
            aggregation: Aggregation method (raw, mean, min, max, p95)

        Returns:
            Dictionary with aggregated beam KPI measurements
        """
        if not self.query_api:
            raise Exception("InfluxDB not available")

        try:
            # Map time range to InfluxDB duration
            time_map = {
                'last_5m': '5m',
                'last_15m': '15m',
                'last_1h': '1h',
                'last_24h': '24h'
            }
            duration = time_map.get(time_range, '15m')

            # Build Flux query
            if aggregation == 'raw':
                query = f'''
                from(bucket: "{self.influx_bucket}")
                  |> range(start: -{duration})
                  |> filter(fn: (r) => r._measurement == "kpi_measurement")
                  |> filter(fn: (r) => r.beam_id == "{beam_id}")
                  |> filter(fn: (r) => r.kpi_name =~ /UE.RSRP|UE.RSRQ|UE.SINR|DRB.UEThpDl|DRB.UEThpUl/)
                  |> yield(name: "raw")
                '''
            else:
                # Aggregation query
                agg_func = aggregation if aggregation in ['mean', 'min', 'max'] else 'mean'
                query = f'''
                from(bucket: "{self.influx_bucket}")
                  |> range(start: -{duration})
                  |> filter(fn: (r) => r._measurement == "kpi_measurement")
                  |> filter(fn: (r) => r.beam_id == "{beam_id}")
                  |> filter(fn: (r) => r.kpi_name =~ /UE.RSRP|UE.RSRQ|UE.SINR|DRB.UEThpDl|DRB.UEThpUl/)
                  |> group(columns: ["kpi_name"])
                  |> {agg_func}()
                  |> yield(name: "{agg_func}")
                '''

            # Execute query
            tables = self.query_api.query(query, org=self.influx_org)

            # Parse results
            data = {
                'signal_quality': {},
                'throughput': {}
            }

            for table in tables:
                for record in table.records:
                    kpi_name = record.values.get('kpi_name')
                    value = record.values.get('_value')

                    measurement = {
                        'value': value,
                        'timestamp': record.values.get('_time').isoformat()
                    }

                    if aggregation != 'raw':
                        measurement['sample_count'] = len(table.records)

                    # Map to response structure
                    if kpi_name == 'UE.RSRP':
                        measurement['unit'] = 'dBm'
                        measurement['quality'] = self.assess_quality('rsrp', value)
                        data['signal_quality']['rsrp'] = measurement
                    elif kpi_name == 'UE.RSRQ':
                        measurement['unit'] = 'dB'
                        measurement['quality'] = self.assess_quality('rsrq', value)
                        data['signal_quality']['rsrq'] = measurement
                    elif kpi_name == 'UE.SINR':
                        measurement['unit'] = 'dB'
                        measurement['quality'] = self.assess_quality('sinr', value)
                        data['signal_quality']['sinr'] = measurement
                    elif kpi_name == 'DRB.UEThpDl':
                        measurement['unit'] = 'Mbps'
                        data['throughput']['downlink'] = measurement
                    elif kpi_name == 'DRB.UEThpUl':
                        measurement['unit'] = 'Mbps'
                        data['throughput']['uplink'] = measurement

            return data

        except Exception as e:
            logger.error(f"Error getting historical beam KPI: {e}")
            raise

    def get_timeseries_data(self, beam_id: int, kpi_type: str,
                            start_time: Optional[datetime] = None,
                            end_time: Optional[datetime] = None,
                            interval: str = '5s') -> List[Dict[str, Any]]:
        """
        Get time-series KPI data for a beam

        Args:
            beam_id: Beam identifier
            kpi_type: KPI type (rsrp, rsrq, sinr, throughput_dl, throughput_ul)
            start_time: Start timestamp
            end_time: End timestamp
            interval: Data point interval

        Returns:
            List of time-series data points
        """
        if not self.query_api:
            raise Exception("InfluxDB not available")

        try:
            # Map KPI type to InfluxDB field
            kpi_map = {
                'rsrp': 'UE.RSRP',
                'rsrq': 'UE.RSRQ',
                'sinr': 'UE.SINR',
                'throughput_dl': 'DRB.UEThpDl',
                'throughput_ul': 'DRB.UEThpUl'
            }
            kpi_name = kpi_map.get(kpi_type)
            if not kpi_name:
                raise ValueError(f"Unknown KPI type: {kpi_type}")

            # Default time range: last 1 hour
            if not start_time:
                start_time = datetime.now() - timedelta(hours=1)
            if not end_time:
                end_time = datetime.now()

            # Build Flux query
            query = f'''
            from(bucket: "{self.influx_bucket}")
              |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
              |> filter(fn: (r) => r._measurement == "kpi_measurement")
              |> filter(fn: (r) => r.beam_id == "{beam_id}")
              |> filter(fn: (r) => r.kpi_name == "{kpi_name}")
              |> aggregateWindow(every: {interval}, fn: mean, createEmpty: false)
              |> yield(name: "timeseries")
            '''

            # Execute query
            tables = self.query_api.query(query, org=self.influx_org)

            # Parse results
            datapoints = []
            for table in tables:
                for record in table.records:
                    datapoints.append({
                        'timestamp': record.values.get('_time').isoformat(),
                        'value': record.values.get('_value'),
                        'quality': self.assess_quality(kpi_type, record.values.get('_value'))
                    })

            return sorted(datapoints, key=lambda x: x['timestamp'])

        except Exception as e:
            logger.error(f"Error getting timeseries data: {e}")
            raise

    def list_active_beams(self, cell_id: Optional[str] = None,
                          min_rsrp: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        List all active beams with basic statistics

        Args:
            cell_id: Optional cell ID filter
            min_rsrp: Optional minimum RSRP filter

        Returns:
            List of active beams with summary statistics
        """
        try:
            # Get all beam keys from Redis
            if cell_id:
                pattern = f"kpi:beam:*:cell:{cell_id}:*"
            else:
                pattern = "kpi:beam:*"

            keys = self.redis.keys(pattern)

            # Extract unique beam IDs
            beam_ids = set()
            for key in keys:
                parts = key.split(':')
                if len(parts) >= 3:
                    beam_ids.add(int(parts[2]))

            # Get summary for each beam
            beams = []
            for beam_id in sorted(beam_ids):
                beam_data = self.get_current_beam_kpi(beam_id, ['all'])
                if not beam_data:
                    continue

                # Extract RSRP if available
                rsrp = None
                if 'signal_quality' in beam_data and 'rsrp' in beam_data['signal_quality']:
                    rsrp = beam_data['signal_quality']['rsrp']['value']

                # Apply RSRP filter
                if min_rsrp is not None and (rsrp is None or rsrp < min_rsrp):
                    continue

                # Build summary
                summary = {
                    'beam_id': beam_id,
                    'cell_id': beam_data.get('metadata', {}).get('cell_id'),
                    'status': 'active',
                    'last_update': datetime.now().isoformat(),
                    'summary': {}
                }

                # Add RSRP
                if rsrp is not None:
                    summary['summary']['rsrp_avg'] = rsrp

                # Add RSRQ
                if 'signal_quality' in beam_data and 'rsrq' in beam_data['signal_quality']:
                    summary['summary']['rsrq_avg'] = beam_data['signal_quality']['rsrq']['value']

                # Add SINR
                if 'signal_quality' in beam_data and 'sinr' in beam_data['signal_quality']:
                    summary['summary']['sinr_avg'] = beam_data['signal_quality']['sinr']['value']

                # Add UE count
                summary['summary']['ue_count'] = beam_data.get('metadata', {}).get('ue_count', 0)

                beams.append(summary)

            return beams

        except Exception as e:
            logger.error(f"Error listing active beams: {e}")
            raise

    def _get_ue_count(self, beam_id: int, cell_id: str) -> int:
        """Get number of UEs served by this beam"""
        try:
            # This is a simplified implementation
            # In a real system, this would query actual UE association data
            pattern = f"ue:beam:{beam_id}:cell:{cell_id}:*"
            return len(self.redis.keys(pattern))
        except:
            return 0


# Global service instance (initialized by KPIMON xApp)
beam_service: Optional[BeamQueryService] = None


def init_beam_service(redis_client: redis.Redis, influx_client: Optional[InfluxDBClient],
                      influx_org: str, influx_bucket: str):
    """Initialize the beam query service"""
    global beam_service
    beam_service = BeamQueryService(redis_client, influx_client, influx_org, influx_bucket)
    logger.info("Beam Query Service initialized")


# Flask API Routes

@beam_api.route('/beam/<int:beam_id>/kpi', methods=['GET'])
def get_beam_kpi(beam_id: int):
    """
    Get KPI measurements for a specific beam

    Query Parameters:
        - kpi_type: KPI type filter (default: all)
        - time_range: Time range (default: current)
        - aggregation: Aggregation method (default: raw)
        - cell_id: Cell ID filter (optional)
        - ue_id: UE ID filter (optional)
    """
    try:
        # Validate beam_id
        if beam_id < 1 or beam_id > 64:
            return jsonify({
                'status': 'error',
                'error_code': 'INVALID_PARAMETER',
                'message': 'beam_id must be between 1 and 64',
                'timestamp': datetime.now().isoformat()
            }), 400

        # Get query parameters
        kpi_type = request.args.get('kpi_type', 'all')
        time_range = request.args.get('time_range', 'current')
        aggregation = request.args.get('aggregation', 'raw')
        cell_id = request.args.get('cell_id')
        ue_id = request.args.get('ue_id')

        # Parse KPI types
        if kpi_type == 'all':
            kpi_types = ['all']
        else:
            kpi_types = kpi_type.split(',')

        # Query data
        if time_range == 'current':
            data = beam_service.get_current_beam_kpi(beam_id, kpi_types, cell_id, ue_id)
            source = 'redis'
        else:
            data = beam_service.get_historical_beam_kpi(beam_id, kpi_types, time_range, aggregation)
            source = 'influxdb'

        if not data:
            return jsonify({
                'status': 'error',
                'error_code': 'BEAM_NOT_FOUND',
                'message': f'No KPI data found for beam_id={beam_id} in the requested time range',
                'timestamp': datetime.now().isoformat(),
                'suggestion': 'Check if beam_id is correct or try a different time_range'
            }), 404

        # Build response
        response = {
            'status': 'success',
            'beam_id': beam_id,
            'timestamp': datetime.now().isoformat(),
            'query_params': {
                'kpi_type': kpi_type,
                'time_range': time_range,
                'aggregation': aggregation
            },
            'data': data,
            'count': sum(len(v) for v in data.values() if isinstance(v, dict)),
            'source': source
        }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error in get_beam_kpi: {e}")
        return jsonify({
            'status': 'error',
            'error_code': 'INTERNAL_ERROR',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@beam_api.route('/beam/<int:beam_id>/kpi/timeseries', methods=['GET'])
def get_beam_kpi_timeseries(beam_id: int):
    """
    Get time-series KPI data for a beam

    Query Parameters:
        - kpi_type: KPI type (required)
        - start_time: Start timestamp (optional)
        - end_time: End timestamp (optional)
        - interval: Data point interval (default: 5s)
    """
    try:
        # Validate beam_id
        if beam_id < 1 or beam_id > 64:
            return jsonify({
                'status': 'error',
                'error_code': 'INVALID_PARAMETER',
                'message': 'beam_id must be between 1 and 64',
                'timestamp': datetime.now().isoformat()
            }), 400

        # Get query parameters
        kpi_type = request.args.get('kpi_type')
        if not kpi_type:
            return jsonify({
                'status': 'error',
                'error_code': 'MISSING_PARAMETER',
                'message': 'kpi_type is required',
                'timestamp': datetime.now().isoformat()
            }), 400

        start_time_str = request.args.get('start_time')
        end_time_str = request.args.get('end_time')
        interval = request.args.get('interval', '5s')

        # Parse timestamps
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00')) if start_time_str else None
        end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00')) if end_time_str else None

        # Query timeseries data
        datapoints = beam_service.get_timeseries_data(beam_id, kpi_type, start_time, end_time, interval)

        # Build response
        response = {
            'status': 'success',
            'beam_id': beam_id,
            'kpi_type': kpi_type,
            'start_time': start_time.isoformat() if start_time else None,
            'end_time': end_time.isoformat() if end_time else None,
            'interval': interval,
            'datapoints': datapoints,
            'count': len(datapoints)
        }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error in get_beam_kpi_timeseries: {e}")
        return jsonify({
            'status': 'error',
            'error_code': 'INTERNAL_ERROR',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@beam_api.route('/beam/list', methods=['GET'])
def list_beams():
    """
    List all active beams with basic statistics

    Query Parameters:
        - cell_id: Cell ID filter (optional)
        - min_rsrp: Minimum RSRP filter (optional)
    """
    try:
        # Get query parameters
        cell_id = request.args.get('cell_id')
        min_rsrp = request.args.get('min_rsrp', type=float)

        # List beams
        beams = beam_service.list_active_beams(cell_id, min_rsrp)

        # Build response
        response = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'beams': beams,
            'count': len(beams)
        }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error in list_beams: {e}")
        return jsonify({
            'status': 'error',
            'error_code': 'INTERNAL_ERROR',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500
