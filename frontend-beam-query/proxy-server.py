#!/usr/bin/env python3
"""
Beam Query UI Proxy Server
解決 CORS 問題：將 UI 和 API 放在同一個 origin

Author: 蔡秀吉 (thc1006)
Date: 2025-11-19
"""

import http.server
import socketserver
import urllib.request
import urllib.error
import json
import os
from urllib.parse import urlparse

PORT = 8888
BEAM_API_URL = "http://localhost:8081"
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))

class BeamProxyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)

        # Proxy API requests
        if parsed_path.path.startswith('/api/') or parsed_path.path.startswith('/health/'):
            self.proxy_to_api()
            return

        # Serve static files
        super().do_GET()

    def proxy_to_api(self):
        """Proxy requests to Beam API"""
        try:
            target_url = f"{BEAM_API_URL}{self.path}"
            print(f"[PROXY] {self.path} -> {target_url}")

            req = urllib.request.Request(target_url)
            for header in ['User-Agent', 'Accept']:
                if header in self.headers:
                    req.add_header(header, self.headers[header])

            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read()

                self.send_response(response.status)

                for header in ['Content-Type', 'Content-Length']:
                    if header in response.headers:
                        self.send_header(header, response.headers[header])

                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')

                self.end_headers()
                self.wfile.write(content)

        except urllib.error.HTTPError as e:
            print(f"[ERROR] HTTP {e.code}: {e.reason}")
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {
                "status": "error",
                "error_code": "PROXY_ERROR",
                "message": f"API returned {e.code}: {e.reason}"
            }
            self.wfile.write(json.dumps(error_response).encode())

        except Exception as e:
            print(f"[ERROR] {e}")
            self.send_error(502, f"Cannot connect to API: {e}")

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

if __name__ == "__main__":
    os.chdir(STATIC_DIR)

    with socketserver.TCPServer(("", PORT), BeamProxyHandler) as httpd:
        print("=" * 70)
        print("🚀 Beam Query UI Proxy Server (Professional Edition)")
        print("=" * 70)
        print(f"")
        print(f"✅ Server running on: http://localhost:{PORT}")
        print(f"")
        print(f"📱 在瀏覽器開啟:")
        print(f"   http://localhost:{PORT}/")
        print(f"")
        print(f"🔗 Proxy 設定:")
        print(f"   UI:  http://localhost:{PORT}/")
        print(f"   API: {BEAM_API_URL} (透過 proxy)")
        print(f"")
        print(f"🔧 確保以下服務運行:")
        print(f"   - KPIMON API: {BEAM_API_URL}")
        print(f"   - E2 Simulator: kubectl get pods -n ricxapp")
        print(f"")
        print("=" * 70)
        print(f"按 Ctrl+C 停止伺服器")
        print("=" * 70)
        print("")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n✅ 伺服器已停止")
