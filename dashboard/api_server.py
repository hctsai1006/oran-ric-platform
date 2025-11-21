#!/usr/bin/env python3
"""
O-RAN RIC Dashboard API Server
Provides REST API endpoints for dashboard frontend
"""

import os
import json
import subprocess
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import logging

app = Flask(__name__, static_folder='.')
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_kubectl(args):
    """Execute kubectl command and return output"""
    try:
        cmd = ['kubectl'] + args
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.stdout, result.returncode
    except Exception as e:
        logger.error(f"kubectl error: {e}")
        return "", 1

@app.route('/')
def index():
    """Serve dashboard index page"""
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    """Serve static files"""
    return send_from_directory('.', path)

@app.route('/api/platform/status')
def platform_status():
    """Get platform status overview"""
    try:
        # Get ricplt pods
        output, code = run_kubectl(['get', 'pods', '-n', 'ricplt', '--no-headers'])
        platform_pods = len([line for line in output.strip().split('\n') if line]) if output else 0

        # Get ricxapp pods
        output, code = run_kubectl(['get', 'pods', '-n', 'ricxapp', '--no-headers'])
        xapp_pods = len([line for line in output.strip().split('\n') if line]) if output else 0

        # Get services
        output, code = run_kubectl(['get', 'svc', '--all-namespaces', '--no-headers'])
        services = len([line for line in output.strip().split('\n') if line]) if output else 0

        # Get components
        components = []
        output, code = run_kubectl(['get', 'pods', '-n', 'ricplt', '-o', 'json'])
        if code == 0 and output:
            try:
                data = json.loads(output)
                for pod in data.get('items', []):
                    name = pod['metadata']['name']
                    status = pod['status']['phase']
                    restarts = sum(cs.get('restartCount', 0) for cs in pod['status'].get('containerStatuses', []))
                    age = pod['metadata'].get('creationTimestamp', '--')

                    components.append({
                        'name': name,
                        'namespace': 'ricplt',
                        'status': status,
                        'restarts': restarts,
                        'age': age
                    })
            except json.JSONDecodeError:
                pass

        output, code = run_kubectl(['get', 'pods', '-n', 'ricxapp', '-o', 'json'])
        if code == 0 and output:
            try:
                data = json.loads(output)
                for pod in data.get('items', []):
                    name = pod['metadata']['name']
                    status = pod['status']['phase']
                    restarts = sum(cs.get('restartCount', 0) for cs in pod['status'].get('containerStatuses', []))
                    age = pod['metadata'].get('creationTimestamp', '--')

                    components.append({
                        'name': name,
                        'namespace': 'ricxapp',
                        'status': status,
                        'restarts': restarts,
                        'age': age
                    })
            except json.JSONDecodeError:
                pass

        return jsonify({
            'platformPods': platform_pods,
            'xappPods': xapp_pods,
            'services': services,
            'uptime': '30m',
            'components': components
        })
    except Exception as e:
        logger.error(f"Error getting platform status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/xapps')
def get_xapps():
    """Get list of xApps"""
    try:
        output, code = run_kubectl(['get', 'pods', '-n', 'ricxapp', '-o', 'json'])

        if code != 0 or not output:
            return jsonify([])

        data = json.loads(output)
        xapps = []

        for pod in data.get('items', []):
            name = pod['metadata']['name']
            status = pod['status']['phase']
            containers = pod['spec'].get('containers', [])
            image = containers[0]['image'] if containers else 'N/A'
            restarts = sum(cs.get('restartCount', 0) for cs in pod['status'].get('containerStatuses', []))

            xapps.append({
                'name': name,
                'status': status,
                'image': image,
                'restarts': restarts
            })

        return jsonify(xapps)
    except Exception as e:
        logger.error(f"Error getting xApps: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/xapps/<name>/restart', methods=['POST'])
def restart_xapp(name):
    """Restart an xApp"""
    try:
        output, code = run_kubectl(['delete', 'pod', name, '-n', 'ricxapp'])

        if code == 0:
            return jsonify({'message': f'{name} restart initiated'})
        else:
            return jsonify({'error': 'Failed to restart xApp'}), 500
    except Exception as e:
        logger.error(f"Error restarting xApp: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/pods')
def get_pods():
    """Get list of pods in a namespace"""
    namespace = request.args.get('namespace', 'ricxapp')

    try:
        output, code = run_kubectl(['get', 'pods', '-n', namespace, '-o', 'json'])

        if code != 0 or not output:
            return jsonify([])

        data = json.loads(output)
        pods = [{'name': pod['metadata']['name']} for pod in data.get('items', [])]

        return jsonify(pods)
    except Exception as e:
        logger.error(f"Error getting pods: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs')
def get_logs():
    """Get pod logs"""
    namespace = request.args.get('namespace', 'ricxapp')
    pod = request.args.get('pod', '')

    if not pod:
        return "Pod name required", 400

    try:
        output, code = run_kubectl(['logs', pod, '-n', namespace, '--tail=100'])
        return output if code == 0 else f"Error fetching logs for {pod}"
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return str(e), 500

@app.route('/api/platform/info')
def platform_info():
    """Get platform information"""
    try:
        # Get namespaces
        output, code = run_kubectl(['get', 'namespaces', '-o', 'json'])
        namespaces = []

        if code == 0 and output:
            data = json.loads(output)
            for ns in data.get('items', []):
                name = ns['metadata']['name']
                if name in ['ricplt', 'ricxapp', 'kube-system']:
                    # Count pods in namespace
                    pod_output, _ = run_kubectl(['get', 'pods', '-n', name, '--no-headers'])
                    pod_count = len([l for l in pod_output.strip().split('\n') if l]) if pod_output else 0

                    namespaces.append({
                        'name': name,
                        'podCount': pod_count
                    })

        # Get Helm releases
        releases = []
        try:
            result = subprocess.run(['helm', 'list', '-n', 'ricplt', '-o', 'json'],
                                    capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout:
                helm_data = json.loads(result.stdout)
                for rel in helm_data:
                    releases.append({
                        'name': rel.get('name', ''),
                        'chart': rel.get('chart', ''),
                        'status': rel.get('status', '')
                    })
        except Exception as e:
            logger.error(f"Error getting helm releases: {e}")

        return jsonify({
            'namespaces': namespaces,
            'releases': releases
        })
    except Exception as e:
        logger.error(f"Error getting platform info: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
