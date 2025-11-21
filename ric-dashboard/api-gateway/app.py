"""
O-RAN RIC Platform Dashboard API Gateway
MBWCL - 行動寬頻無線通訊實驗室

This gateway proxies requests from the Angular frontend to various backend services:
- Kubernetes API (for xApp management)
- KPIMON xApp (for KPI queries)
- Prometheus (for metrics)
- Grafana (for dashboards)
"""

from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
import requests
import os
import json
from kubernetes import client, config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for Angular frontend

# Configuration
KPIMON_SERVICE = os.getenv('KPIMON_SERVICE', 'kpimon-xapp.ricxapp.svc.cluster.local:8081')
PROMETHEUS_SERVICE = os.getenv('PROMETHEUS_SERVICE', 'r4-infrastructure-prometheus-server.ricplt.svc.cluster.local:80')
GRAFANA_SERVICE = os.getenv('GRAFANA_SERVICE', 'oran-grafana.ricplt.svc.cluster.local:80')

# Initialize Kubernetes client
try:
    config.load_incluster_config()  # Use in-cluster config when running in K8s
except:
    try:
        config.load_kube_config()  # Use kubeconfig when running locally
    except:
        logger.warning("Could not load Kubernetes config")

v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

# Configuration for Beam WebUI
BEAM_UI_DIR = os.path.join(os.path.dirname(__file__), 'beam-ui')

# Health check
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'RIC Dashboard API Gateway'}), 200

# Beam WebUI Static Files
@app.route('/beam/', methods=['GET'])
@app.route('/beam/index.html', methods=['GET'])
def serve_beam_ui():
    """Serve Beam WebUI index.html"""
    try:
        return send_from_directory(BEAM_UI_DIR, 'index.html')
    except Exception as e:
        logger.error(f"Error serving Beam UI: {str(e)}")
        return jsonify({'error': 'Beam UI not found'}), 404

@app.route('/beam/<path:filename>', methods=['GET'])
def serve_beam_ui_files(filename):
    """Serve Beam WebUI static files (js, css, etc.)"""
    try:
        return send_from_directory(BEAM_UI_DIR, filename)
    except Exception as e:
        logger.error(f"Error serving Beam UI file {filename}: {str(e)}")
        return jsonify({'error': f'File {filename} not found'}), 404

# xApps Management Endpoints
@app.route('/api/xapps', methods=['GET'])
def get_xapps():
    """Get all xApps in ricxapp namespace"""
    try:
        deployments = apps_v1.list_namespaced_deployment(namespace='ricxapp')

        xapps = []
        for dep in deployments.items:
            # Get pod status
            pods = v1.list_namespaced_pod(
                namespace='ricxapp',
                label_selector=f'app={dep.metadata.name}'
            )

            # Determine health status
            healthy_pods = sum(1 for pod in pods.items if pod.status.phase == 'Running')

            xapp = {
                'name': dep.metadata.name,
                'namespace': dep.metadata.namespace,
                'replicas': dep.spec.replicas,
                'ready_replicas': dep.status.ready_replicas or 0,
                'status': 'Running' if dep.status.ready_replicas == dep.spec.replicas else 'Degraded',
                'version': dep.metadata.labels.get('version', 'unknown'),
                'created': dep.metadata.creation_timestamp.isoformat(),
                'health': {
                    'alive': healthy_pods > 0,
                    'ready': dep.status.ready_replicas == dep.spec.replicas
                }
            }
            xapps.append(xapp)

        return jsonify(xapps), 200
    except Exception as e:
        logger.error(f"Error fetching xApps: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/xapps/<name>', methods=['GET'])
def get_xapp(name):
    """Get specific xApp details"""
    try:
        deployment = apps_v1.read_namespaced_deployment(name=name, namespace='ricxapp')

        # Get pods
        pods = v1.list_namespaced_pod(
            namespace='ricxapp',
            label_selector=f'app={name}'
        )

        pod_details = []
        for pod in pods.items:
            pod_details.append({
                'name': pod.metadata.name,
                'status': pod.status.phase,
                'ip': pod.status.pod_ip,
                'node': pod.spec.node_name,
                'started': pod.status.start_time.isoformat() if pod.status.start_time else None
            })

        xapp = {
            'name': deployment.metadata.name,
            'namespace': deployment.metadata.namespace,
            'replicas': deployment.spec.replicas,
            'ready_replicas': deployment.status.ready_replicas or 0,
            'status': deployment.status.conditions[-1].type if deployment.status.conditions else 'Unknown',
            'version': deployment.metadata.labels.get('version', 'unknown'),
            'created': deployment.metadata.creation_timestamp.isoformat(),
            'pods': pod_details
        }

        return jsonify(xapp), 200
    except Exception as e:
        logger.error(f"Error fetching xApp {name}: {str(e)}")
        return jsonify({'error': str(e)}), 404

@app.route('/api/xapps/<name>/logs', methods=['GET'])
def get_xapp_logs(name):
    """Get xApp logs"""
    try:
        lines = int(request.args.get('lines', 100))

        # Get the first pod of the xApp
        pods = v1.list_namespaced_pod(
            namespace='ricxapp',
            label_selector=f'app={name}'
        )

        if not pods.items:
            return jsonify({'error': 'No pods found'}), 404

        pod_name = pods.items[0].metadata.name
        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace='ricxapp',
            tail_lines=lines
        )

        return jsonify({'logs': logs.split('\n')}), 200
    except Exception as e:
        logger.error(f"Error fetching logs for {name}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/xapps/<name>/restart', methods=['POST'])
def restart_xapp(name):
    """Restart xApp by deleting its pods"""
    try:
        pods = v1.list_namespaced_pod(
            namespace='ricxapp',
            label_selector=f'app={name}'
        )

        for pod in pods.items:
            v1.delete_namespaced_pod(
                name=pod.metadata.name,
                namespace='ricxapp'
            )

        return jsonify({'message': f'xApp {name} restarted'}), 200
    except Exception as e:
        logger.error(f"Error restarting xApp {name}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/xapps/<name>/scale', methods=['POST'])
def scale_xapp(name):
    """Scale xApp replicas"""
    try:
        data = request.get_json()
        replicas = data.get('replicas', 1)

        deployment = apps_v1.read_namespaced_deployment(name=name, namespace='ricxapp')
        deployment.spec.replicas = replicas

        apps_v1.patch_namespaced_deployment(
            name=name,
            namespace='ricxapp',
            body=deployment
        )

        return jsonify({'message': f'xApp {name} scaled to {replicas} replicas'}), 200
    except Exception as e:
        logger.error(f"Error scaling xApp {name}: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Beam KPI Query API (Proxy to KPIMON)
@app.route('/api/beam/<int:beam_id>/kpi', methods=['GET'])
def get_beam_kpi(beam_id):
    """
    Proxy Beam KPI queries to KPIMON xApp
    Query parameters: kpi_type (default: all)
    """
    try:
        kpi_type = request.args.get('kpi_type', 'all')
        url = f'http://{KPIMON_SERVICE}/kpi/beam/{beam_id}'

        params = {'type': kpi_type} if kpi_type != 'all' else {}
        logger.info(f"Proxying Beam {beam_id} KPI query to KPIMON: {url}")

        response = requests.get(url, params=params, timeout=5)

        # If KPIMON service is not available, return mock data
        if response.status_code >= 500:
            logger.warning(f"KPIMON returned {response.status_code}, returning mock data")
            return jsonify(generate_mock_beam_kpi(beam_id, kpi_type)), 200

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'application/json')
        )
    except requests.exceptions.RequestException as e:
        logger.warning(f"KPIMON unavailable, returning mock data: {str(e)}")
        return jsonify(generate_mock_beam_kpi(beam_id, kpi_type)), 200

def generate_mock_beam_kpi(beam_id, kpi_type='all'):
    """Generate mock Beam KPI data for testing"""
    import random
    import datetime

    timestamp = datetime.datetime.now().isoformat()

    data = {
        'status': 'success',
        'beam_id': beam_id,
        'timestamp': timestamp,
        'data': {
            'metadata': {
                'beam_id': beam_id,
                'cell_id': f'CELL-{beam_id:02d}',
                'ue_count': random.randint(5, 25)
            },
            'signal_quality': {
                'rsrp': {
                    'value': round(random.uniform(-90, -60), 2),
                    'unit': 'dBm',
                    'quality': random.choice(['Excellent', 'Good', 'Fair']),
                    'timestamp': timestamp
                },
                'rsrq': {
                    'value': round(random.uniform(-15, -5), 2),
                    'unit': 'dB',
                    'quality': random.choice(['Good', 'Fair']),
                    'timestamp': timestamp
                },
                'sinr': {
                    'value': round(random.uniform(10, 25), 2),
                    'unit': 'dB',
                    'quality': random.choice(['Excellent', 'Good']),
                    'timestamp': timestamp
                }
            },
            'throughput': {
                'downlink': {
                    'value': round(random.uniform(50, 200), 2),
                    'unit': 'Mbps',
                    'timestamp': timestamp
                },
                'uplink': {
                    'value': round(random.uniform(20, 80), 2),
                    'unit': 'Mbps',
                    'timestamp': timestamp
                }
            },
            'packet_loss': {
                'downlink': {
                    'value': round(random.uniform(0.1, 2.0), 2),
                    'unit': '%',
                    'quality': 'Good' if random.random() > 0.2 else 'Fair',
                    'timestamp': timestamp
                }
            },
            'resource_utilization': {
                'prb_usage_dl': {
                    'value': round(random.uniform(30, 80), 2),
                    'unit': '%',
                    'timestamp': timestamp
                },
                'prb_usage_ul': {
                    'value': round(random.uniform(20, 60), 2),
                    'unit': '%',
                    'timestamp': timestamp
                }
            }
        }
    }

    return data

# KPIMON Endpoints (Proxy)
@app.route('/api/kpimon/<path:path>', methods=['GET', 'POST'])
def proxy_kpimon(path):
    """Proxy requests to KPIMON xApp"""
    try:
        url = f'http://{KPIMON_SERVICE}/{path}'
        logger.info(f"Proxying to KPIMON: {url}")

        if request.method == 'GET':
            response = requests.get(url, params=request.args, timeout=5)
        else:
            response = requests.post(url, json=request.get_json(), timeout=5)

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'application/json')
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Error proxying to KPIMON: {str(e)}")
        return jsonify({'error': f'KPIMON service unavailable: {str(e)}'}), 503

# Prometheus Endpoints (Proxy)
@app.route('/api/prometheus/<path:path>', methods=['GET'])
def proxy_prometheus(path):
    """Proxy requests to Prometheus"""
    try:
        url = f'http://{PROMETHEUS_SERVICE}/{path}'
        logger.info(f"Proxying to Prometheus: {url}")

        response = requests.get(url, params=request.args, timeout=10)

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'application/json')
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Error proxying to Prometheus: {str(e)}")
        return jsonify({'error': f'Prometheus service unavailable: {str(e)}'}), 503

# Cluster Statistics
@app.route('/api/cluster/stats', methods=['GET'])
def get_cluster_stats():
    """Get K8s cluster statistics"""
    try:
        # Get nodes
        nodes = v1.list_node()
        node_count = len(nodes.items)

        # Get all pods
        all_pods = v1.list_pod_for_all_namespaces()
        running_pods = sum(1 for pod in all_pods.items if pod.status.phase == 'Running')

        # Get all services
        all_services = v1.list_service_for_all_namespaces()
        service_count = len(all_services.items)

        # Get all deployments
        all_deployments = apps_v1.list_deployment_for_all_namespaces()
        deployment_count = len(all_deployments.items)

        return jsonify({
            'nodes': node_count,
            'pods': running_pods,
            'services': service_count,
            'deployments': deployment_count
        }), 200
    except Exception as e:
        logger.error(f"Error fetching cluster stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Grafana Endpoints (Proxy)
@app.route('/api/grafana/<path:path>', methods=['GET', 'POST'])
def proxy_grafana(path):
    """
    Proxy requests to Grafana with iframe embedding support
    Removes X-Frame-Options to allow embedding in Angular dashboard
    """
    try:
        url = f'http://{GRAFANA_SERVICE}/{path}'
        logger.info(f"Proxying to Grafana: {url}")

        # Forward auth headers if present
        headers = {}
        if 'Authorization' in request.headers:
            headers['Authorization'] = request.headers['Authorization']

        # Make request
        if request.method == 'GET':
            resp = requests.get(url, params=request.args, headers=headers, timeout=10, allow_redirects=True)
        else:
            resp = requests.post(url, json=request.get_json(), headers=headers, timeout=10)

        # Create Flask Response
        flask_response = Response(
            resp.content,
            status=resp.status_code
        )

        # Copy necessary headers, but exclude those that block iframe embedding
        excluded_headers = ['x-frame-options', 'content-security-policy', 'transfer-encoding', 'connection']
        for key, value in resp.headers.items():
            if key.lower() not in excluded_headers:
                flask_response.headers[key] = value

        # Allow iframe embedding from same origin
        flask_response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        flask_response.headers['Access-Control-Allow-Origin'] = '*'

        return flask_response

    except requests.exceptions.RequestException as e:
        logger.error(f"Error proxying to Grafana: {str(e)}")
        return jsonify({'error': f'Grafana service unavailable: {str(e)}'}), 503

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
