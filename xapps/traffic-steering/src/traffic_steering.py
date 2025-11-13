#!/usr/bin/env python3
"""
Traffic Steering xApp
Implements policy-based handover decisions for O-RAN
"""

import json
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from threading import Thread

from ricxappframe.xapp_frame import RMRXapp, rmr
from ricxappframe.xapp_sdl import SDLWrapper
from mdclogpy import Logger

# Configure logging
logger = Logger(name="traffic_steering_xapp")
logger.set_level(logging.INFO)

# RMR Message Types
RIC_SUB_REQ = 12010
RIC_SUB_RESP = 12011
RIC_SUB_DEL_REQ = 12012
RIC_INDICATION = 12050
RIC_CONTROL_REQ = 12040
RIC_CONTROL_RESP = 12041
A1_POLICY_REQ = 20010
A1_POLICY_RESP = 20011

# E2SM Service Model IDs
E2SM_KPM_ID = 0
E2SM_RC_ID = 1

@dataclass
class UEMetrics:
    """UE performance metrics from E2SM-KPM"""
    ue_id: str
    serving_cell: str
    rsrp: float  # Reference Signal Received Power
    rsrq: float  # Reference Signal Received Quality
    dl_throughput: float  # Downlink throughput (Mbps)
    ul_throughput: float  # Uplink throughput (Mbps)
    timestamp: float

@dataclass
class HandoverPolicy:
    """A1 policy for handover thresholds"""
    policy_id: str
    rsrp_threshold: float = -100.0  # dBm
    throughput_threshold: float = 10.0  # Mbps
    load_threshold: float = 0.8  # 80% cell load
    enabled: bool = True

class TrafficSteeringXapp(RMRXapp):
    """
    Traffic Steering xApp implementation
    """
    
    def __init__(self):
        """Initialize xApp"""
        super().__init__(
            default_handler=self._handle_message,
            config_handler=self._handle_config,
            rmr_port=4560,
            rmr_wait_for_ready=True,
            use_fake_sdl=False
        )
        
        # Initialize SDL
        self.sdl = SDLWrapper(use_fake_sdl=False)
        self.namespace = "ts_xapp"
        
        # State management
        self.ue_metrics: Dict[str, UEMetrics] = {}
        self.policies: Dict[str, HandoverPolicy] = {}
        self.subscriptions: Dict[int, Dict] = {}
        
        # Load default policy
        self.default_policy = HandoverPolicy(policy_id="default")
        
        logger.info("Traffic Steering xApp initialized")
    
    def _handle_message(self, summary: dict, sbuf):
        """Handle incoming RMR messages"""
        
        mtype = summary['message type']
        logger.debug(f"Received message type: {mtype}")
        
        try:
            if mtype == RIC_INDICATION:
                self._handle_indication(summary, sbuf)
            elif mtype == RIC_SUB_RESP:
                self._handle_subscription_response(summary, sbuf)
            elif mtype == A1_POLICY_REQ:
                self._handle_policy_request(summary, sbuf)
            else:
                logger.warning(f"Unhandled message type: {mtype}")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            
        # Free the RMR buffer
        self.rmr_free(sbuf)
    
    def _handle_indication(self, summary: dict, sbuf):
        """Process E2 Indication messages"""
        
        # Parse E2SM-KPM indication
        payload = json.loads(summary['payload'])
        
        # Extract UE metrics
        for ue_data in payload.get('ue_list', []):
            ue_metrics = UEMetrics(
                ue_id=ue_data['ue_id'],
                serving_cell=ue_data['serving_cell'],
                rsrp=ue_data['rsrp'],
                rsrq=ue_data['rsrq'],
                dl_throughput=ue_data['dl_throughput'],
                ul_throughput=ue_data['ul_throughput'],
                timestamp=time.time()
            )
            
            # Store metrics
            self.ue_metrics[ue_metrics.ue_id] = ue_metrics
            
            # Store in SDL for persistence
            self.sdl.set(
                self.namespace,
                {f"ue_metrics:{ue_metrics.ue_id}": json.dumps(ue_data)}
            )
            
            # Evaluate handover decision
            self._evaluate_handover(ue_metrics)
    
    def _evaluate_handover(self, metrics: UEMetrics):
        """Evaluate if handover is needed based on policy"""
        
        # Get active policy
        policy = self.policies.get('active', self.default_policy)
        
        if not policy.enabled:
            return
        
        # Check handover criteria
        needs_handover = False
        reason = ""
        
        if metrics.rsrp < policy.rsrp_threshold:
            needs_handover = True
            reason = f"Low RSRP: {metrics.rsrp} dBm"
            
        if metrics.dl_throughput < policy.throughput_threshold:
            needs_handover = True
            reason = f"Low throughput: {metrics.dl_throughput} Mbps"
        
        if needs_handover:
            logger.info(f"Triggering handover for UE {metrics.ue_id}: {reason}")
            
            # Get target cell from QoE Predictor
            target_cell = self._get_target_cell(metrics)
            
            if target_cell:
                # Send control request to RC xApp
                self._send_handover_command(metrics.ue_id, target_cell)
    
    def _get_target_cell(self, metrics: UEMetrics) -> Optional[str]:
        """Query QoE Predictor for best target cell"""
        
        # Send RMR message to QoE Predictor xApp
        request = {
            "ue_id": metrics.ue_id,
            "serving_cell": metrics.serving_cell,
            "timestamp": metrics.timestamp
        }
        
        # Message type for QoE prediction request
        QOE_PRED_REQ = 30000
        
        sbuf = self.rmr_alloc()
        sbuf.contents.mtype = QOE_PRED_REQ
        sbuf.contents.payload = json.dumps(request).encode()
        sbuf.contents.len = len(sbuf.contents.payload)
        
        # Send and wait for response
        sbuf = self.rmr_send(sbuf, retry=True)
        
        # For now, return a mock target cell
        # In production, this would parse the QoE Predictor response
        return "cell_02"
    
    def _send_handover_command(self, ue_id: str, target_cell: str):
        """Send handover command via RC xApp"""
        
        # Construct E2SM-RC control message
        control_msg = {
            "ue_id": ue_id,
            "target_cell": target_cell,
            "control_style": 3,  # UE-specific handover
            "action": "handover"
        }
        
        # Send to RC xApp
        RC_XAPP_REQ = 40000
        
        sbuf = self.rmr_alloc()
        sbuf.contents.mtype = RC_XAPP_REQ
        sbuf.contents.payload = json.dumps(control_msg).encode()
        sbuf.contents.len = len(sbuf.contents.payload)
        
        sbuf = self.rmr_send(sbuf, retry=True)
        
        if sbuf.contents.state == rmr.RMR_OK:
            logger.info(f"Handover command sent for UE {ue_id} to {target_cell}")
        else:
            logger.error(f"Failed to send handover command: {sbuf.contents.state}")
    
    def _handle_subscription_response(self, summary: dict, sbuf):
        """Handle E2 subscription response"""
        
        payload = json.loads(summary['payload'])
        sub_id = payload.get('subscription_id')
        
        if payload.get('status') == 'success':
            logger.info(f"Subscription {sub_id} established successfully")
            self.subscriptions[sub_id] = payload
        else:
            logger.error(f"Subscription {sub_id} failed: {payload.get('reason')}")
    
    def _handle_policy_request(self, summary: dict, sbuf):
        """Handle A1 policy updates"""
        
        payload = json.loads(summary['payload'])
        policy_data = payload.get('policy', {})
        
        # Create new policy
        policy = HandoverPolicy(
            policy_id=payload.get('policy_id'),
            rsrp_threshold=policy_data.get('rsrp_threshold', -100.0),
            throughput_threshold=policy_data.get('throughput_threshold', 10.0),
            load_threshold=policy_data.get('load_threshold', 0.8),
            enabled=policy_data.get('enabled', True)
        )
        
        # Store policy
        self.policies[policy.policy_id] = policy
        self.sdl.set(
            self.namespace,
            {f"policy:{policy.policy_id}": json.dumps(policy_data)}
        )
        
        logger.info(f"Policy {policy.policy_id} updated")
        
        # Send acknowledgment
        self._send_policy_response(payload.get('policy_id'), 'success')
    
    def _send_policy_response(self, policy_id: str, status: str):
        """Send A1 policy response"""
        
        response = {
            "policy_id": policy_id,
            "status": status,
            "timestamp": time.time()
        }
        
        sbuf = self.rmr_alloc()
        sbuf.contents.mtype = A1_POLICY_RESP
        sbuf.contents.payload = json.dumps(response).encode()
        sbuf.contents.len = len(sbuf.contents.payload)
        
        self.rmr_send(sbuf, retry=True)
    
    def _handle_config(self, config: dict):
        """Handle configuration updates"""
        
        logger.info(f"Configuration updated: {config}")
        
        # Update thresholds from config
        if 'handover' in config:
            self.default_policy.rsrp_threshold = config['handover'].get(
                'rsrp_threshold', self.default_policy.rsrp_threshold
            )
            self.default_policy.throughput_threshold = config['handover'].get(
                'throughput_threshold', self.default_policy.throughput_threshold
            )
    
    def create_subscriptions(self):
        """Create E2 subscriptions for KPM metrics"""
        
        # E2SM-KPM subscription for UE metrics
        kpm_subscription = {
            "subscription_id": 1001,
            "ran_function_id": E2SM_KPM_ID,
            "action_type": "report",
            "report_style": 4,  # UE-level measurements
            "granularity_period": 1000,  # 1 second
            "measurements": [
                "DRB.UEThpDl",
                "DRB.UEThpUl",
                "RRU.PrbTotDl",
                "RRU.PrbUsedDl"
            ]
        }
        
        # Send subscription request
        sbuf = self.rmr_alloc()
        sbuf.contents.mtype = RIC_SUB_REQ
        sbuf.contents.payload = json.dumps(kpm_subscription).encode()
        sbuf.contents.len = len(sbuf.contents.payload)
        
        sbuf = self.rmr_send(sbuf, retry=True)
        
        if sbuf.contents.state == rmr.RMR_OK:
            logger.info("E2 subscription request sent")
        else:
            logger.error(f"Failed to send subscription: {sbuf.contents.state}")
    
    def start(self):
        """Start the xApp"""
        
        logger.info("Starting Traffic Steering xApp")
        
        # Create E2 subscriptions
        self.create_subscriptions()
        
        # Start health check thread
        health_thread = Thread(target=self._health_check_loop)
        health_thread.daemon = True
        health_thread.start()
        
        # Start RMR message loop
        self.run()
    
    def _health_check_loop(self):
        """Periodic health check"""
        
        while True:
            time.sleep(30)
            
            # Clean old metrics
            current_time = time.time()
            expired_ues = []
            
            for ue_id, metrics in self.ue_metrics.items():
                if current_time - metrics.timestamp > 60:  # 1 minute timeout
                    expired_ues.append(ue_id)
            
            for ue_id in expired_ues:
                del self.ue_metrics[ue_id]
                logger.debug(f"Removed stale metrics for UE {ue_id}")
            
            # Log status
            logger.info(f"Active UEs: {len(self.ue_metrics)}, Policies: {len(self.policies)}")

def main():
    """Main entry point"""
    
    # Create and start xApp
    xapp = TrafficSteeringXapp()
    xapp.start()

if __name__ == "__main__":
    main()
