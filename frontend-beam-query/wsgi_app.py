#!/usr/bin/env python3
"""
WSGI Application for Beam Query UI
Simple, focused implementation following TDD principles
"""

import os
import mimetypes
import urllib.request
import urllib.error


# Configuration
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_API_URL = "http://kpimon-beam-api:8081"


def application(environ, start_response):
    """
    WSGI application entry point
    """
    path = environ['PATH_INFO']
    query_string = environ.get('QUERY_STRING', '')

    # Route: API proxy
    if path.startswith('/api/') or path.startswith('/health/'):
        return proxy_to_backend(path, query_string, start_response)

    # Route: Static files
    if path == '/':
        path = '/index.html'

    return serve_static_file(path, start_response)


def proxy_to_backend(path, query_string, start_response):
    """
    Proxy API requests to backend server
    """
    # Build target URL
    target_url = f"{BACKEND_API_URL}{path}"
    if query_string:
        target_url += f"?{query_string}"

    try:
        # Make request to backend
        with urllib.request.urlopen(target_url, timeout=5) as response:
            content = response.read()
            status = response.status

            # Build response headers with CORS
            headers = [
                ('Content-Type', response.headers.get('Content-Type', 'application/json')),
                ('Content-Length', str(len(content))),
                ('Access-Control-Allow-Origin', '*'),
                ('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'),
                ('Access-Control-Allow-Headers', 'Content-Type'),
            ]

            start_response(f'{status} OK', headers)
            return [content]

    except urllib.error.HTTPError as e:
        # Backend returned an error
        start_response(f'{e.code} Error', [
            ('Content-Type', 'application/json'),
            ('Access-Control-Allow-Origin', '*'),
        ])
        return [b'{"error": "Backend API error"}']

    except Exception as e:
        # Connection error or timeout
        start_response('502 Bad Gateway', [
            ('Content-Type', 'application/json'),
            ('Access-Control-Allow-Origin', '*'),
        ])
        return [b'{"error": "Cannot connect to backend"}']


def serve_static_file(path, start_response):
    """
    Serve static file from STATIC_DIR
    """
    file_path = os.path.join(STATIC_DIR, path.lstrip('/'))

    # Security: prevent directory traversal
    if not file_path.startswith(STATIC_DIR):
        start_response('403 Forbidden', [('Content-Type', 'text/plain')])
        return [b'Forbidden']

    # Check file exists
    if not os.path.isfile(file_path):
        start_response('404 Not Found', [('Content-Type', 'text/plain')])
        return [b'Not Found']

    # Determine content type
    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        content_type = 'application/octet-stream'

    # Read and return file
    try:
        with open(file_path, 'rb') as f:
            content = f.read()

        headers = [
            ('Content-Type', content_type),
            ('Content-Length', str(len(content))),
        ]
        start_response('200 OK', headers)
        return [content]

    except Exception as e:
        start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
        return [f'Error reading file: {e}'.encode()]
