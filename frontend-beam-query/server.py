#!/usr/bin/env python3
"""
Simple HTTP Server for Beam Query UI
Author: 蔡秀吉 (thc1006)
Date: 2025-11-19

Usage:
    python server.py [port]

Default port: 8000
"""

import http.server
import socketserver
import sys
import os

# Default port
PORT = 8000

# Get port from command line if provided
if len(sys.argv) > 1:
    try:
        PORT = int(sys.argv[1])
    except ValueError:
        print(f"❌ Invalid port number: {sys.argv[1]}")
        print(f"Usage: {sys.argv[0]} [port]")
        sys.exit(1)

# Change to the script directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Create server
Handler = http.server.SimpleHTTPRequestHandler

# Add CORS headers
class CORSRequestHandler(Handler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

with socketserver.TCPServer(("", PORT), CORSRequestHandler) as httpd:
    print("=" * 60)
    print("🚀 Beam Query UI Server")
    print("=" * 60)
    print(f"")
    print(f"✅ Server running on: http://localhost:{PORT}")
    print(f"")
    print(f"📱 在瀏覽器開啟:")
    print(f"   http://localhost:{PORT}/")
    print(f"")
    print(f"🔗 確保以下服務運行:")
    print(f"   - KPIMON API: http://localhost:8081")
    print(f"   - E2 Simulator: kubectl get pods -n ricxapp | grep e2-simulator")
    print(f"")
    print("=" * 60)
    print(f"按 Ctrl+C 停止伺服器")
    print("=" * 60)
    print("")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✅ 伺服器已停止")
