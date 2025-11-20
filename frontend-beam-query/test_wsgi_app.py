#!/usr/bin/env python3
"""
Simple tests for WSGI application
Following TDD principles - keep it minimal
"""

import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO
import json


class TestWSGIApp(unittest.TestCase):
    """Test WSGI application basic functionality"""

    def setUp(self):
        """Import the WSGI app"""
        try:
            from wsgi_app import application
            self.app = application
        except ImportError:
            self.app = None

    def _call_app(self, path='/', method='GET'):
        """Helper to call WSGI app"""
        if self.app is None:
            self.skipTest("WSGI app not implemented yet")

        environ = {
            'REQUEST_METHOD': method,
            'PATH_INFO': path,
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '8888',
            'wsgi.input': BytesIO(b''),
            'wsgi.errors': BytesIO(),
            'wsgi.url_scheme': 'http',
        }

        self.response_status = None
        self.response_headers = []

        def start_response(status, headers):
            self.response_status = status
            self.response_headers = headers

        response_body = self.app(environ, start_response)
        return b''.join(response_body), self.response_status, dict(self.response_headers)

    def test_root_path_returns_html(self):
        """Test GET / returns index.html"""
        body, status, headers = self._call_app('/')

        self.assertEqual(status, '200 OK')
        self.assertIn('text/html', headers.get('Content-Type', ''))
        self.assertIn(b'<!DOCTYPE html>', body)

    def test_static_file_exists(self):
        """Test static files can be served"""
        body, status, headers = self._call_app('/app.js')

        self.assertEqual(status, '200 OK')
        self.assertIn('javascript', headers.get('Content-Type', '').lower())

    @patch('urllib.request.urlopen')
    def test_api_proxy_basic(self, mock_urlopen):
        """Test API requests are proxied to backend"""
        # Mock backend response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({"status": "success"}).encode()
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_urlopen.return_value.__enter__.return_value = mock_response

        body, status, headers = self._call_app('/api/beam/5/kpi?kpi_type=all')

        self.assertEqual(status, '200 OK')
        self.assertIn(b'"status"', body)
        # Verify CORS headers
        self.assertIn('Access-Control-Allow-Origin', headers)


if __name__ == '__main__':
    unittest.main()
