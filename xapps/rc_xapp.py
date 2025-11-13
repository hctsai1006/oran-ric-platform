#!/usr/bin/env python3
"""
RC xApp - RAN Control for Slice Management
Based on E2SM-RC specification
Supports Radio Resource Allocation Control (Style 2, Action 6)
"""

import json
import time
import logging
import struct
import grpc
from concurrent import futures
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from threading import Thread, Lock

from ricxappframe.xapp_frame import RMRXapp, rmr
from ricxappframe.xapp_sdl import SDLWrapper
from mdclogpy import Logger

# Import protobuf generated files (these would be generated from .proto files)
# For now, we'll implement a simple gRPC service inline

# Configure logging
logger = Logger(name="rc_xapp")
logger.set_level(logging.INFO)

# RMR Message Types
RIC_CONTROL_REQ = 12040
RIC_CONTROL_ACK = 12041
RIC_CONTROL_FAILURE = 12042
RC_XAPP_REQ = 40000
RC_XAPP_RESP = 40001

# E2SM-RC Service Model
E2SM_RC_ID = 3
CONTROL_STYLE_RADIO_RESOURCE = 2
CONTROL_ACTION_SLICE_LEVEL_PRB = 6

@dataclass
class SliceConfig:
    """Network slice configuration"""
    plmn_id: str
    sst: int  # Slice/Service Type
    sd: str  # Slice Differentiator
    min_prb_ratio: int  # 0-100
    max_prb_ratio: int  # 0-100
    ded_prb_ratio: int  # 0-100 (dedicated)

@dataclass
class RRMPolicy:
    """RRM Policy configuration"""
    policy_id: str
    members: List[SliceConfig]
    min_prb: int
    max_prb: int
    ded_prb: int

@dataclass
class ControlRequest:
    """E2SM-RC Control Request"""
    ran_name: str
    control_style: int
    control_action: int
    rrm_policies: List[RRMPolicy]
    request_id: str
    timestamp: float

class RCGrpcService:
    """gRPC service for receiving control requests"""
    
    def __init__(self, xapp):
        self.xapp = xapp
        
    def SendRRMPolicyServiceGrpc(self, request, context):
        """Handle RRM Policy configuration request via gRPC"""
        
        try:
            # Parse gRPC request
            ran_name = request.get('ranName')
            rrm_policies = request.get('rrmPolicy', [])
            
            logger.info(f"Received gRPC request for {ran_name} with {len(rrm_policies)} policies")
            
            # Convert to internal format
            policies = []
            for policy_data in rrm_policies:
                members = []
                for member_data in policy_data.get('member', []):
                    member = SliceConfig(
                        plmn_id=member_data.get('plmnId'),
                        sst=int(member_data.get('sst'), 16),
                        sd=member_data.get('sd'),
                        min_prb_ratio=0,  # Set from policy level
                        max_prb_ratio=0,
                        ded_prb_ratio=0
                    )
                    members.append(member)
                
                policy = RRMPolicy(
                    policy_id=f"policy_{len(policies)}",
                    members=members,
                    min_prb=policy_data.get('minPRB', 0),
                    max_prb=policy_data.get('maxPRB', 100),
                    ded_prb=policy_data.get('dedPRB', 0)
                )
                policies.append(policy)
            
            # Send RIC Control Request
            success = self.xapp.send_control_request(ran_name, policies)
            
            if success:
                return {"status": "SUCCESS", "message": "RRM Policy applied successfully"}
            else:
                return {"status": "FAILURE", "message": "Failed to apply RRM Policy"}
                
        except Exception as e:
            logger.error(f"gRPC service error: {e}")
            return {"status": "ERROR", "message": str(e)}

class RanControlXapp(RMRXapp):
    """
    RAN Control xApp implementation for slice-level PRB management
    """
    
    def __init__(self):
        """Initialize RC xApp"""
        super().__init__(
            default_handler=self._handle_message,
            config_handler=self._handle_config,
            rmr_port=4560,
            rmr_wait_for_ready=True,
            use_fake_sdl=False
        )
        
        # Initialize SDL
        self.sdl = SDLWrapper(use_fake_sdl=False)
        self.namespace = "rc_xapp"
        
        # State management
        self.active_policies: Dict[str, List[RRMPolicy]] = {}
        self.control_requests: Dict[str, ControlRequest] = {}
        self.request_lock = Lock()
        
        # gRPC server
        self.grpc_server = None
        self.grpc_port = 7777
        
        # Statistics
        self.stats = {
            "control_requests_sent": 0,
            "control_acks_received": 0,
            "control_failures": 0,
            "grpc_requests": 0
        }
        
        logger.info("RC xApp initialized")
    
    def _handle_message(self, summary: dict, sbuf):
        """Handle incoming RMR messages"""
        
        mtype = summary['message type']
        logger.debug(f"Received message type: {mtype}")
        
        try:
            if mtype == RIC_CONTROL_ACK:
                self._handle_control_ack(summary, sbuf)
            elif mtype == RIC_CONTROL_FAILURE:
                self._handle_control_failure(summary, sbuf)
            elif mtype == RC_XAPP_REQ:
                self._handle_xapp_request(summary, sbuf)
            else:
                logger.warning(f"Unhandled message type: {mtype}")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            
        # Free the RMR buffer
        self.rmr_free(sbuf)
    
    def send_control_request(self, ran_name: str, policies: List[RRMPolicy]) -> bool:
        """Send E2SM-RC Control Request to E2 Node"""
        
        try:
            # Create control request
            request = ControlRequest(
                ran_name=ran_name,
                control_style=CONTROL_STYLE_RADIO_RESOURCE,
                control_action=CONTROL_ACTION_SLICE_LEVEL_PRB,
                rrm_policies=policies,
                request_id=f"req_{int(time.time())}",
                timestamp=time.time()
            )
            
            # Store request for tracking
            with self.request_lock:
                self.control_requests[request.request_id] = request
            
            # Encode E2SM-RC Control message
            control_msg = self._encode_control_message(request)
            
            # Send via RMR
            sbuf = self.rmr_alloc()
            sbuf.contents.mtype = RIC_CONTROL_REQ
            sbuf.contents.payload = control_msg
            sbuf.contents.len = len(control_msg)
            
            # Add routing information
            sbuf.contents.sub_id = 0  # Subscription ID if needed
            
            sbuf = self.rmr_send(sbuf, retry=True)
            
            if sbuf.contents.state == rmr.RMR_OK:
                self.stats["control_requests_sent"] += 1
                logger.info(f"Control request sent to {ran_name}")
                
                # Store active policy
                self.active_policies[ran_name] = policies
                self._store_policy_in_sdl(ran_name, policies)
                
                return True
            else:
                logger.error(f"Failed to send control request: {sbuf.contents.state}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending control request: {e}")
            return False
    
    def _encode_control_message(self, request: ControlRequest) -> bytes:
        """Encode E2SM-RC Control message"""
        
        # This is a simplified encoding
        # In production, use proper ASN.1 encoding for E2SM-RC
        
        msg = {
            "header": {
                "ran_function_id": E2SM_RC_ID,
                "request_id": request.request_id,
                "control_style": request.control_style,
                "control_action_id": request.control_action
            },
            "message": {
                "rrm_policy_list": []
            }
        }
        
        for policy in request.rrm_policies:
            policy_msg = {
                "resource_type": "PRB",
                "policy_members": [],
                "policy_min_ratio": policy.min_prb,
                "policy_max_ratio": policy.max_prb,
                "policy_ded_ratio": policy.ded_prb
            }
            
            for member in policy.members:
                member_msg = {
                    "plmn_identity": self._encode_plmn(member.plmn_id),
                    "s_nssai": {
                        "sst": member.sst,
                        "sd": bytes.fromhex(member.sd).hex()
                    }
                }
                policy_msg["policy_members"].append(member_msg)
            
            msg["message"]["rrm_policy_list"].append(policy_msg)
        
        # Convert to JSON for simplicity (should be ASN.1 in production)
        return json.dumps(msg).encode()
    
    def _encode_plmn(self, plmn_id: str) -> str:
        """Encode PLMN ID"""
        # PLMN format: MCC (3 digits) + MNC (2-3 digits)
        # Example: "311480" -> MCC=311, MNC=480
        if len(plmn_id) == 6:
            mcc = plmn_id[:3]
            mnc = plmn_id[3:]
            # BCD encoding simulation
            return f"{mcc}{mnc}"
        return plmn_id
    
    def _handle_control_ack(self, summary: dict, sbuf):
        """Handle RIC Control Acknowledgment"""
        
        try:
            # Parse acknowledgment
            payload = json.loads(summary['payload'])
            request_id = payload.get('request_id')
            
            with self.request_lock:
                if request_id in self.control_requests:
                    request = self.control_requests[request_id]
                    logger.info(f"Control ACK received for {request.ran_name}")
                    
                    # Update statistics
                    self.stats["control_acks_received"] += 1
                    
                    # Store successful configuration
                    self._store_success_in_sdl(request)
                    
                    # Clean up request
                    del self.control_requests[request_id]
                    
        except Exception as e:
            logger.error(f"Failed to handle control ACK: {e}")
    
    def _handle_control_failure(self, summary: dict, sbuf):
        """Handle RIC Control Failure"""
        
        try:
            payload = json.loads(summary['payload'])
            request_id = payload.get('request_id')
            cause = payload.get('cause', 'unknown')
            
            with self.request_lock:
                if request_id in self.control_requests:
                    request = self.control_requests[request_id]
                    logger.error(f"Control FAILURE for {request.ran_name}: {cause}")
                    
                    # Update statistics
                    self.stats["control_failures"] += 1
                    
                    # Store failure in SDL
                    self._store_failure_in_sdl(request, cause)
                    
                    # Clean up request
                    del self.control_requests[request_id]
                    
        except Exception as e:
            logger.error(f"Failed to handle control failure: {e}")
    
    def _handle_xapp_request(self, summary: dict, sbuf):
        """Handle request from other xApps"""
        
        try:
            payload = json.loads(summary['payload'])
            action = payload.get('action')
            
            if action == 'apply_policy':
                ran_name = payload.get('ran_name')
                policies_data = payload.get('policies', [])
                
                # Convert to RRMPolicy objects
                policies = []
                for p_data in policies_data:
                    members = [SliceConfig(**m) for m in p_data.get('members', [])]
                    policy = RRMPolicy(
                        policy_id=p_data.get('policy_id'),
                        members=members,
                        min_prb=p_data.get('min_prb'),
                        max_prb=p_data.get('max_prb'),
                        ded_prb=p_data.get('ded_prb')
                    )
                    policies.append(policy)
                
                # Send control request
                success = self.send_control_request(ran_name, policies)
                
                # Send response
                response = {
                    'status': 'success' if success else 'failure',
                    'ran_name': ran_name
                }
                
                sbuf_resp = self.rmr_alloc()
                sbuf_resp.contents.mtype = RC_XAPP_RESP
                sbuf_resp.contents.payload = json.dumps(response).encode()
                sbuf_resp.contents.len = len(sbuf_resp.contents.payload)
                
                self.rmr_send(sbuf_resp, retry=True)
                
        except Exception as e:
            logger.error(f"Failed to handle xApp request: {e}")
    
    def _store_policy_in_sdl(self, ran_name: str, policies: List[RRMPolicy]):
        """Store active policy in SDL"""
        
        key = f"active_policy:{ran_name}"
        value = {
            'policies': [
                {
                    'policy_id': p.policy_id,
                    'members': [asdict(m) for m in p.members],
                    'min_prb': p.min_prb,
                    'max_prb': p.max_prb,
                    'ded_prb': p.ded_prb
                } for p in policies
            ],
            'timestamp': time.time()
        }
        
        self.sdl.set(self.namespace, {key: json.dumps(value)})
        logger.debug(f"Stored policy for {ran_name} in SDL")
    
    def _store_success_in_sdl(self, request: ControlRequest):
        """Store successful control request in SDL"""
        
        key = f"control_success:{request.ran_name}:{request.request_id}"
        value = {
            'ran_name': request.ran_name,
            'request_id': request.request_id,
            'timestamp': request.timestamp,
            'policies_count': len(request.rrm_policies)
        }
        
        self.sdl.set(self.namespace, {key: json.dumps(value)})
    
    def _store_failure_in_sdl(self, request: ControlRequest, cause: str):
        """Store failed control request in SDL"""
        
        key = f"control_failure:{request.ran_name}:{request.request_id}"
        value = {
            'ran_name': request.ran_name,
            'request_id': request.request_id,
            'timestamp': request.timestamp,
            'cause': cause
        }
        
        self.sdl.set(self.namespace, {key: json.dumps(value)})
    
    def start_grpc_server(self):
        """Start gRPC server for external control requests"""
        
        try:
            self.grpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
            
            # Add service (simplified - in production use proper protobuf)
            service = RCGrpcService(self)
            # grpc_service_pb2_grpc.add_MsgCommServicer_to_server(service, self.grpc_server)
            
            self.grpc_server.add_insecure_port(f'[::]:{self.grpc_port}')
            self.grpc_server.start()
            
            logger.info(f"gRPC server started on port {self.grpc_port}")
            
        except Exception as e:
            logger.error(f"Failed to start gRPC server: {e}")
    
    def _handle_config(self, config: dict):
        """Handle configuration updates"""
        
        logger.info(f"Configuration updated: {config}")
        
        if 'grpc_port' in config:
            self.grpc_port = config['grpc_port']
            # Restart gRPC server if needed
    
    def get_statistics(self) -> dict:
        """Get xApp statistics"""
        
        return {
            **self.stats,
            "active_policies_count": len(self.active_policies),
            "pending_requests": len(self.control_requests)
        }
    
    def start(self):
        """Start the RC xApp"""
        
        logger.info("Starting RC xApp")
        
        # Start gRPC server
        self.start_grpc_server()
        
        # Start statistics thread
        stats_thread = Thread(target=self._stats_loop)
        stats_thread.daemon = True
        stats_thread.start()
        
        # Start RMR message loop
        self.run()
    
    def _stats_loop(self):
        """Periodic statistics reporting"""
        
        while True:
            time.sleep(60)
            stats = self.get_statistics()
            logger.info(f"RC xApp Statistics: {stats}")

def main():
    """Main entry point"""
    
    # Create and start xApp
    xapp = RanControlXapp()
    xapp.start()

if __name__ == "__main__":
    main()
