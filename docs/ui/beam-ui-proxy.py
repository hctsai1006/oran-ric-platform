#!/usr/bin/env python3
"""
Beam Query UI Proxy Server
解決 CORS 問題：將 Web UI 和 Beam API 放在同一個 origin
"""
import http.server
import socketserver
import urllib.request
import urllib.error
import json
import os
from urllib.parse import urlparse, parse_qs

PORT = 8889
BEAM_API_URL = "http://localhost:8081"
WEB_UI_PATH = "/home/mbwcl711_3060/thc1006/tmep/oran-ric-platform/beam-query-interface.html"

class BeamProxyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Parse the URL
        parsed_path = urlparse(self.path)

        # Serve the Web UI
        if self.path == '/' or self.path == '/index.html':
            self.serve_file(WEB_UI_PATH, 'text/html')
            return

        # Proxy requests to Beam API
        if parsed_path.path.startswith('/api/') or parsed_path.path.startswith('/health/'):
            self.proxy_to_beam_api()
            return

        # Default handler for other files
        super().do_GET()

    def serve_file(self, filepath, content_type):
        """Serve a local file"""
        try:
            with open(filepath, 'rb') as f:
                content = f.read()

            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error serving file: {e}")

    def proxy_to_beam_api(self):
        """Proxy requests to Beam API"""
        try:
            # Build the target URL
            target_url = f"{BEAM_API_URL}{self.path}"

            print(f"[PROXY] {self.path} -> {target_url}")

            # Forward the request
            req = urllib.request.Request(target_url)

            # Copy headers from original request
            for header in ['User-Agent', 'Accept', 'Accept-Language']:
                if header in self.headers:
                    req.add_header(header, self.headers[header])

            # Make the request
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read()

                # Send response back to client
                self.send_response(response.status)

                # Copy relevant headers
                for header in ['Content-Type', 'Content-Length']:
                    if header in response.headers:
                        self.send_header(header, response.headers[header])

                # Add CORS headers
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

        except urllib.error.URLError as e:
            print(f"[ERROR] URL Error: {e.reason}")
            self.send_error(502, f"Cannot connect to Beam API: {e.reason}")

        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            self.send_error(500, f"Proxy error: {e}")

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        """Custom logging"""
        print(f"[{self.client_address[0]}] {format % args}")

if __name__ == "__main__":
    # Change to the project directory
    os.chdir('/home/mbwcl711_3060/thc1006/tmep/oran-ric-platform')

    with socketserver.TCPServer(("", PORT), BeamProxyHandler) as httpd:
        print("=" * 60)
        print(f"🚀 Beam Query UI Proxy Server")
        print("=" * 60)
        print(f"")
        print(f"✅ Server running on: http://localhost:{PORT}")
        print(f"")
        print(f"📱 在瀏覽器開啟:")
        print(f"   http://localhost:{PORT}/")
        print(f"")
        print(f"🔗 Proxy 設定:")
        print(f"   Web UI:  http://localhost:{PORT}/")
        print(f"   API:     {BEAM_API_URL} (透過 proxy)")
        print(f"")
        print(f"📊 測試 API:")
        print(f"   http://localhost:{PORT}/health/alive")
        print(f"   http://localhost:{PORT}/api/beam/5/kpi?kpi_type=all")
        print(f"")
        print("=" * 60)
        print(f"按 Ctrl+C 停止伺服器")
        print("=" * 60)
        print("")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n✅ 伺服器已停止")
