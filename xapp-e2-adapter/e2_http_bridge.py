#!/usr/bin/env python3
"""
HTTP E2 Bridge Adapter for UAV xApp Simulation

This module provides an HTTP-based interface that simulates E2 communication
between ns-3 (or Python simulator) and the UAV Policy xApp.

It translates:
- KPM Indications -> HTTP POST to xApp
- RIC Control Requests <- HTTP response from xApp

Author: Research Team
Date: 2025-11-21
Purpose: Enable xApp validation without SCTP/E2AP complexity
"""

import json
import logging
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
import requests
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class KpmIndication:
    """E2SM-KPM Indication Message (simplified)"""
    timestamp: float
    ue_id: str
    gnb_id: str
    cell_id: int
    rsrp_serving: float      # dBm
    rsrq_serving: float      # dB
    sinr: float              # dB
    prb_utilization: float   # 0-1
    neighbor_cells: list     # [{cell_id, rsrp, rsrq}]
    position: Optional[dict] = None  # {x, y, z}

    def to_xapp_format(self) -> Dict:
        """Convert to xApp-expected format"""
        return {
            "indication_type": "KPM",
            "ue_id": self.ue_id,
            "gnb_id": self.gnb_id,
            "cell_id": self.cell_id,
            "timestamp": self.timestamp,
            "measurements": {
                "rsrp_serving_dbm": self.rsrp_serving,
                "rsrq_serving_db": self.rsrq_serving,
                "sinr_db": self.sinr,
                "prb_utilization": self.prb_utilization
            },
            "neighbor_cells": self.neighbor_cells,
            "ue_context": {
                "position": self.position
            }
        }


@dataclass
class RicControlRequest:
    """E2SM-RC Control Request (simplified)"""
    ue_id: str
    action: str           # "handover", "prb_allocation", "no_action"
    target_cell_id: Optional[int] = None
    allocated_prbs: Optional[int] = None
    reason: str = ""


class E2HttpBridge:
    """
    HTTP-based E2 Bridge between simulator and xApp.

    Architecture:
        [ns-3/Python Sim] --HTTP--> [E2 Bridge] --HTTP--> [UAV xApp]
                         <--Control--         <--Decision--
    """

    def __init__(
        self,
        bridge_host: str = "0.0.0.0",
        bridge_port: int = 8081,
        xapp_url: str = "http://localhost:8080"
    ):
        self.bridge_host = bridge_host
        self.bridge_port = bridge_port
        self.xapp_url = xapp_url
        self.server: Optional[HTTPServer] = None

        # Statistics
        self.stats = {
            "indications_received": 0,
            "indications_forwarded": 0,
            "control_requests_sent": 0,
            "handovers_requested": 0,
            "prb_allocations": 0,
            "errors": 0,
            "start_time": None
        }

        # Last control decision (cached)
        self.last_control: Optional[RicControlRequest] = None

    def forward_to_xapp(self, kpm: KpmIndication) -> Optional[RicControlRequest]:
        """Forward KPM indication to xApp and get control decision"""
        try:
            payload = kpm.to_xapp_format()

            response = requests.post(
                f"{self.xapp_url}/api/v1/e2/indication",
                json=payload,
                timeout=2.0
            )

            self.stats["indications_forwarded"] += 1

            if response.status_code == 200:
                data = response.json()

                # Parse control decision
                if data.get("action") and data["action"] != "no_action":
                    control = RicControlRequest(
                        ue_id=kpm.ue_id,
                        action=data["action"],
                        target_cell_id=data.get("target_cell_id"),
                        allocated_prbs=data.get("allocated_prbs"),
                        reason=data.get("reason", "")
                    )

                    if control.action == "handover":
                        self.stats["handovers_requested"] += 1
                    elif control.action == "prb_allocation":
                        self.stats["prb_allocations"] += 1

                    self.stats["control_requests_sent"] += 1
                    self.last_control = control
                    return control

            return None

        except requests.exceptions.Timeout:
            logger.warning("xApp request timed out")
            self.stats["errors"] += 1
            return None
        except Exception as e:
            logger.error(f"Error forwarding to xApp: {e}")
            self.stats["errors"] += 1
            return None

    def create_handler(bridge_instance):
        """Create HTTP request handler with bridge reference"""

        class E2BridgeHandler(BaseHTTPRequestHandler):
            bridge = bridge_instance

            def log_message(self, format, *args):
                logger.debug(format % args)

            def _send_response(self, code: int, data: dict):
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())

            def do_GET(self):
                """Handle GET requests (status, stats)"""
                if self.path == "/status":
                    self._send_response(200, {
                        "status": "running",
                        "xapp_url": self.bridge.xapp_url,
                        "uptime": time.time() - self.bridge.stats["start_time"]
                            if self.bridge.stats["start_time"] else 0
                    })
                elif self.path == "/stats":
                    self._send_response(200, self.bridge.stats)
                elif self.path == "/last_control":
                    if self.bridge.last_control:
                        self._send_response(200, asdict(self.bridge.last_control))
                    else:
                        self._send_response(200, {"action": "no_action"})
                else:
                    self._send_response(404, {"error": "Not found"})

            def do_POST(self):
                """Handle POST requests (KPM indications)"""
                if self.path == "/api/v1/kpm/indication":
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length)

                    try:
                        data = json.loads(body)
                        self.bridge.stats["indications_received"] += 1

                        # Create KPM indication
                        kpm = KpmIndication(
                            timestamp=data.get("timestamp", time.time()),
                            ue_id=data.get("ue_id", "UAV-001"),
                            gnb_id=data.get("gnb_id", "gNB-001"),
                            cell_id=data.get("serving_cell_id", 1),
                            rsrp_serving=data.get("rsrp_serving", -100),
                            rsrq_serving=data.get("rsrq_serving", -15),
                            sinr=data.get("rsrp_serving", -100) + 100,  # Simplified
                            prb_utilization=data.get("prb_utilization", 0.5),
                            neighbor_cells=data.get("neighbor_cells", []),
                            position=data.get("position")
                        )

                        # Forward to xApp
                        control = self.bridge.forward_to_xapp(kpm)

                        if control:
                            response_data = {
                                "status": "control_action",
                                "action": control.action,
                                "target_cell_id": control.target_cell_id,
                                "allocated_prbs": control.allocated_prbs,
                                "reason": control.reason
                            }
                        else:
                            response_data = {
                                "status": "no_action",
                                "action": "no_action"
                            }

                        self._send_response(200, response_data)

                    except json.JSONDecodeError:
                        self._send_response(400, {"error": "Invalid JSON"})
                    except Exception as e:
                        logger.error(f"Error processing indication: {e}")
                        self._send_response(500, {"error": str(e)})
                else:
                    self._send_response(404, {"error": "Not found"})

        return E2BridgeHandler

    def start(self):
        """Start the HTTP bridge server"""
        handler_class = E2HttpBridge.create_handler(self)
        self.server = HTTPServer((self.bridge_host, self.bridge_port), handler_class)
        self.stats["start_time"] = time.time()

        logger.info("=" * 50)
        logger.info("E2 HTTP Bridge Starting")
        logger.info("=" * 50)
        logger.info(f"Bridge listening on: http://{self.bridge_host}:{self.bridge_port}")
        logger.info(f"xApp URL: {self.xapp_url}")
        logger.info("")
        logger.info("Endpoints:")
        logger.info("  POST /api/v1/kpm/indication - Send KPM indication")
        logger.info("  GET  /status                - Bridge status")
        logger.info("  GET  /stats                 - Statistics")
        logger.info("  GET  /last_control          - Last control decision")
        logger.info("=" * 50)

        self.server.serve_forever()

    def start_background(self) -> Thread:
        """Start bridge in background thread"""
        thread = Thread(target=self.start, daemon=True)
        thread.start()
        time.sleep(0.5)  # Wait for server to start
        return thread

    def stop(self):
        """Stop the bridge server"""
        if self.server:
            self.server.shutdown()
            logger.info("E2 HTTP Bridge stopped")

    def print_stats(self):
        """Print statistics summary"""
        if self.stats["start_time"]:
            uptime = time.time() - self.stats["start_time"]
        else:
            uptime = 0

        logger.info("")
        logger.info("=" * 50)
        logger.info("E2 HTTP Bridge Statistics")
        logger.info("=" * 50)
        logger.info(f"Uptime: {uptime:.1f} seconds")
        logger.info(f"Indications Received: {self.stats['indications_received']}")
        logger.info(f"Indications Forwarded: {self.stats['indications_forwarded']}")
        logger.info(f"Control Requests Sent: {self.stats['control_requests_sent']}")
        logger.info(f"  - Handovers Requested: {self.stats['handovers_requested']}")
        logger.info(f"  - PRB Allocations: {self.stats['prb_allocations']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info("=" * 50)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="E2 HTTP Bridge")
    parser.add_argument("--host", default="0.0.0.0", help="Bridge host")
    parser.add_argument("--port", type=int, default=8081, help="Bridge port")
    parser.add_argument("--xapp-url", default="http://localhost:8080",
                       help="xApp HTTP URL")

    args = parser.parse_args()

    bridge = E2HttpBridge(
        bridge_host=args.host,
        bridge_port=args.port,
        xapp_url=args.xapp_url
    )

    try:
        bridge.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        bridge.print_stats()
        bridge.stop()


if __name__ == "__main__":
    main()
