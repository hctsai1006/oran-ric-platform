#!/usr/bin/env python3
"""
Beam Query UI Proxy Server - Professional Edition with Improved Error Handling
改進版：完整異常處理 + 多執行緒 + 日誌記錄

Author: 蔡秀吉 (thc1006)
Date: 2025-11-19
"""

import http.server
import socketserver
import urllib.request
import urllib.error
import json
import os
import sys
import logging
import signal
from urllib.parse import urlparse
from datetime import datetime

# ============================================================================
# Configuration
# ============================================================================
PORT = 8888
BEAM_API_URL = "http://localhost:8081"
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = "/tmp/beam-ui-proxy.log"

# ============================================================================
# Logging Setup
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# Proxy Handler
# ============================================================================
class BeamProxyHandler(http.server.SimpleHTTPRequestHandler):
    """
    HTTP Request Handler with CORS support and API proxying
    """

    # Suppress default logging to avoid duplicate logs
    def log_message(self, format, *args):
        logger.info(f"{self.address_string()} - {format % args}")

    def do_GET(self):
        parsed_path = urlparse(self.path)

        # Proxy API requests
        if parsed_path.path.startswith('/api/') or parsed_path.path.startswith('/health/'):
            self.proxy_to_api()
            return

        # Serve static files
        try:
            super().do_GET()
        except Exception as e:
            logger.error(f"Error serving static file {self.path}: {e}")
            self.send_error(500, f"Internal Server Error: {e}")

    def proxy_to_api(self):
        """Proxy requests to Beam API with improved error handling"""
        target_url = f"{BEAM_API_URL}{self.path}"
        logger.info(f"[PROXY] {self.path} -> {target_url}")

        try:
            req = urllib.request.Request(target_url)
            for header in ['User-Agent', 'Accept']:
                if header in self.headers:
                    req.add_header(header, self.headers[header])

            # Reduced timeout to fail fast
            with urllib.request.urlopen(req, timeout=3) as response:
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

                logger.info(f"[PROXY] Success: {self.path} -> {response.status}")

        except urllib.error.HTTPError as e:
            logger.error(f"[PROXY] HTTP Error {e.code}: {e.reason} for {target_url}")
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {
                "status": "error",
                "error_code": "PROXY_HTTP_ERROR",
                "message": f"API returned {e.code}: {e.reason}"
            }
            self.wfile.write(json.dumps(error_response).encode())

        except urllib.error.URLError as e:
            logger.error(f"[PROXY] URL Error: {e.reason} for {target_url}")
            self.send_error(502, f"Cannot connect to API: {e.reason}")

        except TimeoutError:
            logger.error(f"[PROXY] Timeout connecting to {target_url}")
            self.send_error(504, "API Gateway Timeout")

        except Exception as e:
            logger.error(f"[PROXY] Unexpected error: {type(e).__name__}: {e}")
            self.send_error(502, f"Proxy Error: {e}")

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

# ============================================================================
# Signal Handlers
# ============================================================================
def signal_handler(signum, frame):
    """Graceful shutdown on SIGTERM/SIGINT"""
    signal_name = signal.Signals(signum).name
    logger.info(f"Received signal {signal_name}, shutting down gracefully...")
    sys.exit(0)

# ============================================================================
# Main Server
# ============================================================================
def run_server():
    """Run the proxy server with comprehensive error handling"""

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Change to static directory
    os.chdir(STATIC_DIR)
    logger.info(f"Changed working directory to: {STATIC_DIR}")

    # Create server with ThreadingMixin for concurrent requests
    try:
        # Use ThreadingTCPServer instead of TCPServer for multi-threading
        httpd = socketserver.ThreadingTCPServer(("", PORT), BeamProxyHandler)
        # Allow reusing the address immediately (avoid "Address already in use")
        httpd.allow_reuse_address = True

        logger.info("=" * 70)
        logger.info("🚀 Beam Query UI Proxy Server (Professional Edition v2)")
        logger.info("=" * 70)
        logger.info(f"")
        logger.info(f"✅ Server running on: http://0.0.0.0:{PORT}")
        logger.info(f"")
        logger.info(f"📱 在瀏覽器開啟:")
        logger.info(f"   http://localhost:{PORT}/")
        logger.info(f"")
        logger.info(f"🔗 Proxy 設定:")
        logger.info(f"   UI:  http://0.0.0.0:{PORT}/")
        logger.info(f"   API: {BEAM_API_URL} (透過 proxy)")
        logger.info(f"")
        logger.info(f"📝 日誌檔案: {LOG_FILE}")
        logger.info(f"")
        logger.info(f"🔧 確保以下服務運行:")
        logger.info(f"   - KPIMON API: {BEAM_API_URL}")
        logger.info(f"   - E2 Simulator: kubectl get pods -n ricxapp")
        logger.info(f"")
        logger.info("=" * 70)
        logger.info(f"按 Ctrl+C 停止伺服器")
        logger.info("=" * 70)
        logger.info("")

        # Serve forever with comprehensive exception handling
        httpd.serve_forever()

    except OSError as e:
        if e.errno == 48 or e.errno == 98:  # Address already in use
            logger.error(f"❌ Port {PORT} already in use!")
            logger.error(f"   請先停止其他使用 {PORT} 的進程：")
            logger.error(f"   lsof -i :{PORT} | grep LISTEN")
            logger.error(f"   kill -9 <PID>")
        else:
            logger.error(f"❌ OS Error: {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n✅ 收到 KeyboardInterrupt，正在停止伺服器...")

    except Exception as e:
        logger.error(f"❌ Unexpected error in server: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logger.info("🛑 伺服器已完全停止")
        if 'httpd' in locals():
            httpd.shutdown()
            httpd.server_close()
            logger.info("✅ Socket 已關閉")

# ============================================================================
# Entry Point
# ============================================================================
if __name__ == "__main__":
    logger.info(f"Starting Beam UI Proxy Server at {datetime.now()}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"PID: {os.getpid()}")

    try:
        run_server()
    except Exception as e:
        logger.critical(f"Critical error: {e}")
        import traceback
        logger.critical(traceback.format_exc())
        sys.exit(1)
