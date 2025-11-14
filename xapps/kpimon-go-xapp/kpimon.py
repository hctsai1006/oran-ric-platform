#!/usr/bin/env python3
"""
KPIMON xApp - Key Performance Indicator Monitoring
Based on O-RAN E2SM-KPM v2.0 specification
Supports cell-level and slice-level metrics collection
"""

import json
import time
import logging
import struct
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from threading import Thread, Lock
from datetime import datetime

from ricxappframe.xapp_frame import RMRXapp, rmr
from ricxappframe.xapp_sdl import SDLWrapper
from mdclogpy import Logger
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# Configure logging
logger = Logger(name="kpimon_xapp")
logger.set_level(logging.INFO)

# RMR Message Types
RIC_SUB_REQ = 12010
RIC_SUB_RESP = 12011
RIC_SUB_DEL_REQ = 12012
RIC_SUB_DEL_RESP = 12013
RIC_SUB_FAILURE = 12014
RIC_INDICATION = 12050
RIC_SUB_DEL_FAILURE = 12015

# E2SM-KPM Service Model ID
E2SM_KPM_ID = 2

# KPM Report Styles
REPORT_STYLE_1 = 1  # Cell-level aggregated metrics
REPORT_STYLE_3 = 3  # Slice-level metrics
REPORT_STYLE_4 = 4  # UE-level metrics

@dataclass
class CellMetrics:
    """Cell-level performance metrics"""
    ran_name: str
    cell_id: str
    drb_ue_throughput_dl: float  # DRB.UEThpDl
    prb_used_dl: int  # RRU.PrbUsedDl
    prb_avail_dl: int  # RRU.PrbAvailDl
    prb_total_dl: float  # RRU.PrbTotDl
    timestamp: datetime

@dataclass
class SliceMetrics:
    """Slice-level performance metrics"""
    ran_name: str
    slice_id: str  # SNSSAI
    plmn_id: str
    sst: int
    sd: str
    drb_ue_throughput_dl: float  # DRB.UEThpDl.SNSSAI
    prb_used_dl: int  # RRU.PrbUsedDl.SNSSAI
    timestamp: datetime

@dataclass
class UEMetrics:
    """UE-level performance metrics"""
    ue_id: str
    cell_id: str
    dl_throughput: float
    ul_throughput: float
    rsrp: float
    rsrq: float
    cqi: int
    timestamp: datetime

class KPIMonitorXapp(RMRXapp):
    """
    KPI Monitoring xApp implementation
    Collects and stores network performance metrics
    """
    
    def __init__(self):
        """Initialize KPI Monitor xApp"""
        super().__init__(
            default_handler=self._handle_message,
            config_handler=self._handle_config,
            rmr_port=4560,
            rmr_wait_for_ready=True,
            use_fake_sdl=False
        )
        
        # Initialize SDL
        self.sdl = SDLWrapper(use_fake_sdl=False)
        self.namespace = "kpimon"
        
        # Initialize InfluxDB client
        self.influx_client = self._init_influxdb()
        self.write_api = None
        if self.influx_client:
            self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
        
        # State management
        self.subscriptions: Dict[int, Dict] = {}
        self.metrics_lock = Lock()
        self.cell_metrics: List[CellMetrics] = []
        self.slice_metrics: List[SliceMetrics] = []
        self.ue_metrics: List[UEMetrics] = []
        
        # Statistics
        self.stats = {
            "indications_received": 0,
            "cell_metrics_stored": 0,
            "slice_metrics_stored": 0,
            "ue_metrics_stored": 0,
            "errors": 0
        }
        
        logger.info("KPIMON xApp initialized")
    
    def _init_influxdb(self) -> Optional[InfluxDBClient]:
        """Initialize InfluxDB connection"""
        try:
            # Get credentials from environment or config
            # These should match your RIC platform's InfluxDB setup
            url = "http://ricplt-influxdb2:8086"
            token = "admin-token"  # Should be from secret
            org = "primary"
            
            client = InfluxDBClient(
                url=url,
                token=token,
                org=org
            )
            
            # Create bucket if not exists
            buckets_api = client.buckets_api()
            bucket_name = "kpm"
            
            buckets = buckets_api.find_buckets().buckets
            if not any(b.name == bucket_name for b in buckets):
                buckets_api.create_bucket(bucket_name=bucket_name, org=org)
                logger.info(f"Created InfluxDB bucket: {bucket_name}")
            
            logger.info("InfluxDB connection established")
            return client
            
        except Exception as e:
            logger.error(f"Failed to initialize InfluxDB: {e}")
            return None
    
    def _handle_message(self, summary: dict, sbuf):
        """Handle incoming RMR messages"""
        
        mtype = summary['message type']
        logger.debug(f"Received message type: {mtype}")
        
        try:
            if mtype == RIC_INDICATION:
                self._handle_indication(summary, sbuf)
            elif mtype == RIC_SUB_RESP:
                self._handle_subscription_response(summary, sbuf)
            elif mtype == RIC_SUB_FAILURE:
                self._handle_subscription_failure(summary, sbuf)
            else:
                logger.warning(f"Unhandled message type: {mtype}")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            self.stats["errors"] += 1
            
        # Free the RMR buffer
        self.rmr_free(sbuf)
    
    def _handle_indication(self, summary: dict, sbuf):
        """Process E2SM-KPM Indication messages"""
        
        self.stats["indications_received"] += 1
        
        # Parse indication based on report style
        payload = self._decode_indication(sbuf)
        
        if not payload:
            logger.error("Failed to decode indication")
            return
        
        report_style = payload.get("report_style", 0)
        ran_name = payload.get("ran_name", "unknown")
        
        if report_style == REPORT_STYLE_1:
            # Cell-level metrics
            self._process_cell_metrics(ran_name, payload)
            
        elif report_style == REPORT_STYLE_3:
            # Slice-level metrics
            self._process_slice_metrics(ran_name, payload)
            
        elif report_style == REPORT_STYLE_4:
            # UE-level metrics
            self._process_ue_metrics(ran_name, payload)
        
        else:
            logger.warning(f"Unknown report style: {report_style}")
    
    def _decode_indication(self, sbuf) -> dict:
        """Decode E2SM-KPM indication message"""
        try:
            # This is a simplified decoder
            # In production, use proper ASN.1 decoding
            raw_payload = sbuf.contents.payload[:sbuf.contents.len]
            
            # Parse based on expected format
            # Format: [header_len][header][message_len][message]
            idx = 0
            header_len = struct.unpack('>H', raw_payload[idx:idx+2])[0]
            idx += 2
            
            header = raw_payload[idx:idx+header_len]
            idx += header_len
            
            message_len = struct.unpack('>H', raw_payload[idx:idx+2])[0]
            idx += 2
            
            message = raw_payload[idx:idx+message_len]
            
            # Decode JSON payload (simplified)
            return json.loads(message.decode('utf-8'))
            
        except Exception as e:
            logger.error(f"Failed to decode indication: {e}")
            return {}
    
    def _process_cell_metrics(self, ran_name: str, payload: dict):
        """Process and store cell-level metrics"""
        
        try:
            metrics_data = payload.get("cell_metrics", {})
            
            cell_metrics = CellMetrics(
                ran_name=ran_name,
                cell_id=metrics_data.get("cell_id", "0"),
                drb_ue_throughput_dl=metrics_data.get("DRB.UEThpDl", 0.0),
                prb_used_dl=metrics_data.get("RRU.PrbUsedDl", 0),
                prb_avail_dl=metrics_data.get("RRU.PrbAvailDl", 273),
                prb_total_dl=metrics_data.get("RRU.PrbTotDl", 0.0),
                timestamp=datetime.utcnow()
            )
            
            # Store locally
            with self.metrics_lock:
                self.cell_metrics.append(cell_metrics)
                
            # Store in SDL
            key = f"cell_metrics:{ran_name}:{cell_metrics.cell_id}"
            self.sdl.set(self.namespace, {key: json.dumps(asdict(cell_metrics), default=str)})
            
            # Store in InfluxDB
            if self.write_api:
                point = Point("CellMetrics") \
                    .tag("RanName", ran_name) \
                    .tag("CellId", cell_metrics.cell_id) \
                    .field("DRB.UEThpDl", cell_metrics.drb_ue_throughput_dl) \
                    .field("RRU.PrbUsedDl", cell_metrics.prb_used_dl) \
                    .field("RRU.PrbAvailDl", cell_metrics.prb_avail_dl) \
                    .field("RRU.PrbTotDl", cell_metrics.prb_total_dl) \
                    .time(cell_metrics.timestamp, WritePrecision.NS)
                
                self.write_api.write(bucket="kpm", record=point)
                
            self.stats["cell_metrics_stored"] += 1
            logger.info(f"Stored cell metrics for {ran_name}/{cell_metrics.cell_id}")
            
        except Exception as e:
            logger.error(f"Failed to process cell metrics: {e}")
            self.stats["errors"] += 1
    
    def _process_slice_metrics(self, ran_name: str, payload: dict):
        """Process and store slice-level metrics"""
        
        try:
            slice_list = payload.get("slice_metrics", [])
            
            for slice_data in slice_list:
                snssai = slice_data.get("snssai", {})
                
                slice_metrics = SliceMetrics(
                    ran_name=ran_name,
                    slice_id=slice_data.get("slice_id", ""),
                    plmn_id=snssai.get("plmn_id", ""),
                    sst=snssai.get("sst", 1),
                    sd=snssai.get("sd", "000001"),
                    drb_ue_throughput_dl=slice_data.get("DRB.UEThpDl.SNSSAI", 0.0),
                    prb_used_dl=slice_data.get("RRU.PrbUsedDl.SNSSAI", 0),
                    timestamp=datetime.utcnow()
                )
                
                # Store locally
                with self.metrics_lock:
                    self.slice_metrics.append(slice_metrics)
                    
                # Store in SDL
                key = f"slice_metrics:{ran_name}:{slice_metrics.slice_id}"
                self.sdl.set(self.namespace, {key: json.dumps(asdict(slice_metrics), default=str)})
                
                # Store in InfluxDB
                if self.write_api:
                    point = Point("SliceMetrics") \
                        .tag("RanName", ran_name) \
                        .tag("SliceID", slice_metrics.slice_id) \
                        .tag("SST", str(slice_metrics.sst)) \
                        .field("DRB.UEThpDl.SNSSAI", slice_metrics.drb_ue_throughput_dl) \
                        .field("RRU.PrbUsedDl.SNSSAI", slice_metrics.prb_used_dl) \
                        .time(slice_metrics.timestamp, WritePrecision.NS)
                    
                    self.write_api.write(bucket="kpm", record=point)
                    
                self.stats["slice_metrics_stored"] += 1
                logger.info(f"Stored slice metrics for {ran_name}/{slice_metrics.slice_id}")
                
        except Exception as e:
            logger.error(f"Failed to process slice metrics: {e}")
            self.stats["errors"] += 1
    
    def _process_ue_metrics(self, ran_name: str, payload: dict):
        """Process and store UE-level metrics"""
        
        try:
            ue_list = payload.get("ue_metrics", [])
            
            for ue_data in ue_list:
                ue_metrics = UEMetrics(
                    ue_id=ue_data.get("ue_id", ""),
                    cell_id=ue_data.get("cell_id", ""),
                    dl_throughput=ue_data.get("dl_throughput", 0.0),
                    ul_throughput=ue_data.get("ul_throughput", 0.0),
                    rsrp=ue_data.get("rsrp", -100.0),
                    rsrq=ue_data.get("rsrq", -15.0),
                    cqi=ue_data.get("cqi", 7),
                    timestamp=datetime.utcnow()
                )
                
                # Store locally
                with self.metrics_lock:
                    self.ue_metrics.append(ue_metrics)
                    
                # Store in SDL for quick access
                key = f"ue_metrics:{ue_metrics.ue_id}"
                self.sdl.set(self.namespace, {key: json.dumps(asdict(ue_metrics), default=str)})
                
                self.stats["ue_metrics_stored"] += 1
                logger.debug(f"Stored UE metrics for {ue_metrics.ue_id}")
                
        except Exception as e:
            logger.error(f"Failed to process UE metrics: {e}")
            self.stats["errors"] += 1
    
    def _handle_subscription_response(self, summary: dict, sbuf):
        """Handle subscription response from E2 Node"""
        
        try:
            # Simplified parsing - in production use proper ASN.1 decoder
            payload = json.loads(summary['payload'])
            
            sub_id = payload.get("subscription_id")
            status = payload.get("status", "unknown")
            
            if status == "success":
                logger.info(f"Subscription {sub_id} established successfully")
                self.subscriptions[sub_id] = {
                    "status": "active",
                    "ran_function_id": payload.get("ran_function_id"),
                    "timestamp": time.time()
                }
            else:
                logger.error(f"Subscription {sub_id} failed: {status}")
                
        except Exception as e:
            logger.error(f"Failed to handle subscription response: {e}")
    
    def _handle_subscription_failure(self, summary: dict, sbuf):
        """Handle subscription failure from E2 Node"""
        
        try:
            payload = json.loads(summary['payload'])
            sub_id = payload.get("subscription_id")
            reason = payload.get("reason", "unknown")
            
            logger.error(f"Subscription {sub_id} failed: {reason}")
            
            # Retry subscription after delay
            Thread(target=self._retry_subscription, args=(sub_id,)).start()
            
        except Exception as e:
            logger.error(f"Failed to handle subscription failure: {e}")
    
    def _retry_subscription(self, sub_id: int):
        """Retry failed subscription after delay"""
        
        time.sleep(30)  # Wait 30 seconds before retry
        logger.info(f"Retrying subscription {sub_id}")
        self.create_subscriptions()
    
    def create_subscriptions(self):
        """Create E2SM-KPM subscriptions"""
        
        subscriptions = [
            {
                "subscription_id": 1001,
                "ran_function_id": E2SM_KPM_ID,
                "report_style": REPORT_STYLE_1,
                "granularity_period": 1000,
                "measurements": [
                    "DRB.UEThpDl",
                    "RRU.PrbUsedDl",
                    "RRU.PrbAvailDl",
                    "RRU.PrbTotDl"
                ]
            },
            {
                "subscription_id": 1002,
                "ran_function_id": E2SM_KPM_ID,
                "report_style": REPORT_STYLE_3,
                "granularity_period": 1000,
                "measurements": [
                    "DRB.UEThpDl.SNSSAI",
                    "RRU.PrbUsedDl.SNSSAI"
                ]
            },
            {
                "subscription_id": 1003,
                "ran_function_id": E2SM_KPM_ID,
                "report_style": REPORT_STYLE_4,
                "granularity_period": 5000,
                "measurements": [
                    "DRB.UEThpDl",
                    "DRB.UEThpUl",
                    "RF.RSRP",
                    "RF.RSRQ"
                ]
            }
        ]
        
        for sub in subscriptions:
            self._send_subscription_request(sub)
            time.sleep(1)  # Space out subscriptions
    
    def _send_subscription_request(self, subscription: dict):
        """Send subscription request to E2 Node"""
        
        try:
            sbuf = self.rmr_alloc()
            sbuf.contents.mtype = RIC_SUB_REQ
            sbuf.contents.payload = json.dumps(subscription).encode()
            sbuf.contents.len = len(sbuf.contents.payload)
            
            sbuf = self.rmr_send(sbuf, retry=True)
            
            if sbuf.contents.state == rmr.RMR_OK:
                logger.info(f"Subscription request {subscription['subscription_id']} sent")
            else:
                logger.error(f"Failed to send subscription: {sbuf.contents.state}")
                
        except Exception as e:
            logger.error(f"Error sending subscription request: {e}")
    
    def _handle_config(self, config: dict):
        """Handle configuration updates"""
        
        logger.info(f"Configuration updated: {config}")
        
        # Update configuration parameters
        if 'influxdb' in config:
            # Reinitialize InfluxDB connection if config changed
            self.influx_client = self._init_influxdb()
            
        if 'subscriptions' in config:
            # Update subscription parameters
            self.create_subscriptions()
    
    def get_metrics_summary(self) -> dict:
        """Get summary of collected metrics"""
        
        with self.metrics_lock:
            return {
                "cell_metrics_count": len(self.cell_metrics),
                "slice_metrics_count": len(self.slice_metrics),
                "ue_metrics_count": len(self.ue_metrics),
                "stats": self.stats.copy()
            }
    
    def cleanup_old_metrics(self, retention_hours: int = 24):
        """Clean up metrics older than retention period"""
        
        cutoff_time = datetime.utcnow().timestamp() - (retention_hours * 3600)
        
        with self.metrics_lock:
            # Clean cell metrics
            self.cell_metrics = [
                m for m in self.cell_metrics 
                if m.timestamp.timestamp() > cutoff_time
            ]
            
            # Clean slice metrics
            self.slice_metrics = [
                m for m in self.slice_metrics
                if m.timestamp.timestamp() > cutoff_time
            ]
            
            # Clean UE metrics
            self.ue_metrics = [
                m for m in self.ue_metrics
                if m.timestamp.timestamp() > cutoff_time
            ]
        
        logger.info(f"Cleaned up metrics older than {retention_hours} hours")
    
    def start(self):
        """Start the KPIMON xApp"""
        
        logger.info("Starting KPIMON xApp")
        
        # Create initial subscriptions
        self.create_subscriptions()
        
        # Start cleanup thread
        cleanup_thread = Thread(target=self._cleanup_loop)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
        # Start statistics thread
        stats_thread = Thread(target=self._stats_loop)
        stats_thread.daemon = True
        stats_thread.start()
        
        # Start RMR message loop
        self.run()
    
    def _cleanup_loop(self):
        """Periodic cleanup of old metrics"""
        
        while True:
            time.sleep(3600)  # Run every hour
            self.cleanup_old_metrics()
    
    def _stats_loop(self):
        """Periodic statistics reporting"""
        
        while True:
            time.sleep(60)  # Report every minute
            summary = self.get_metrics_summary()
            logger.info(f"Metrics Summary: {summary}")

def main():
    """Main entry point"""
    
    # Create and start xApp
    xapp = KPIMonitorXapp()
    xapp.start()

if __name__ == "__main__":
    main()
