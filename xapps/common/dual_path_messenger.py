#!/usr/bin/env python3
"""
Dual-Path Messenger for O-RAN SC Release J
Implements RMR (primary) + HTTP (fallback) redundant communication with automatic failover
Compliant with O-RAN SC best practices for near-RT RIC xApps
"""

import json
import time
import logging
import requests
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from threading import Thread, Lock
from enum import Enum

from ricxappframe.xapp_frame import RMRXapp, rmr
from mdclogpy import Logger
from prometheus_client import Counter, Gauge, Histogram

# Configure logging
logger = Logger(name="dual_path_messenger")
logger.set_level(logging.INFO)

# Prometheus Metrics
METRIC_PREFIX = "dual_path_"

messages_sent_rmr = Counter(
    f'{METRIC_PREFIX}messages_sent_rmr_total',
    'Total messages sent via RMR',
    ['message_type', 'destination']
)

messages_sent_http = Counter(
    f'{METRIC_PREFIX}messages_sent_http_total',
    'Total messages sent via HTTP',
    ['message_type', 'destination']
)

messages_failed = Counter(
    f'{METRIC_PREFIX}messages_failed_total',
    'Total failed message deliveries',
    ['message_type', 'path_type']
)

rmr_health_status = Gauge(
    f'{METRIC_PREFIX}rmr_health_status',
    'RMR connection health (1=healthy, 0=unhealthy)'
)

http_health_status = Gauge(
    f'{METRIC_PREFIX}http_health_status',
    'HTTP connection health (1=healthy, 0=unhealthy)'
)

active_path = Gauge(
    f'{METRIC_PREFIX}active_path',
    'Currently active communication path (1=RMR, 0=HTTP)'
)

failover_events = Counter(
    f'{METRIC_PREFIX}failover_events_total',
    'Total number of path failover events',
    ['from_path', 'to_path']
)

message_latency = Histogram(
    f'{METRIC_PREFIX}message_latency_seconds',
    'Message delivery latency',
    ['path_type']
)


class CommunicationPath(Enum):
    """Communication path types"""
    RMR = "rmr"
    HTTP = "http"


class PathStatus(Enum):
    """Path health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass
class PathHealthMetrics:
    """Health metrics for a communication path"""
    path_type: CommunicationPath
    status: PathStatus
    last_success_time: float
    last_failure_time: float
    consecutive_failures: int
    consecutive_successes: int
    total_sent: int
    total_failed: int


@dataclass
class EndpointConfig:
    """Endpoint configuration for HTTP fallback"""
    service_name: str
    namespace: str = "ricxapp"
    http_port: int = 8080
    rmr_port: int = 4560
    health_endpoint: str = "/ric/v1/health/alive"
    message_endpoint: str = "/e2/indication"

    @property
    def http_base_url(self) -> str:
        """Get HTTP base URL"""
        return f"http://{self.service_name}.{self.namespace}.svc.cluster.local:{self.http_port}"

    @property
    def rmr_address(self) -> str:
        """Get RMR address"""
        return f"{self.service_name}.{self.namespace}"


class DualPathMessenger:
    """
    Dual-path communication manager for O-RAN xApps

    Features:
    - RMR as primary communication path
    - HTTP as fallback path
    - Automatic health monitoring
    - Intelligent failover with hysteresis
    - Comprehensive logging and monitoring
    - O-RAN SC Release J compliant
    """

    def __init__(
        self,
        xapp_name: str,
        rmr_port: int = 4560,
        message_handler: Optional[Callable] = None,
        config: Optional[Dict] = None
    ):
        """
        Initialize dual-path messenger

        Args:
            xapp_name: Name of the xApp
            rmr_port: RMR port number
            message_handler: Callback for incoming messages
            config: Configuration dictionary
        """
        self.xapp_name = xapp_name
        self.rmr_port = rmr_port
        self.message_handler = message_handler
        self.config = config or self._default_config()

        # RMR xApp instance
        self.rmr_xapp: Optional[RMRXapp] = None

        # Path health tracking
        self.path_health: Dict[CommunicationPath, PathHealthMetrics] = {
            CommunicationPath.RMR: PathHealthMetrics(
                path_type=CommunicationPath.RMR,
                status=PathStatus.DOWN,
                last_success_time=0,
                last_failure_time=0,
                consecutive_failures=0,
                consecutive_successes=0,
                total_sent=0,
                total_failed=0
            ),
            CommunicationPath.HTTP: PathHealthMetrics(
                path_type=CommunicationPath.HTTP,
                status=PathStatus.DOWN,
                last_success_time=0,
                last_failure_time=0,
                consecutive_failures=0,
                consecutive_successes=0,
                total_sent=0,
                total_failed=0
            )
        }

        # Current active path
        self.current_path = CommunicationPath.RMR
        self.path_lock = Lock()

        # Endpoint registry
        self.endpoints: Dict[str, EndpointConfig] = {}

        # Health check thread
        self.running = False
        self.health_check_thread: Optional[Thread] = None

        # HTTP session for connection pooling
        self.http_session = requests.Session()
        self.http_session.headers.update({
            'Content-Type': 'application/json',
            'X-Source-XApp': self.xapp_name
        })

        logger.info(f"DualPathMessenger initialized for xApp: {self.xapp_name}")

    def _default_config(self) -> Dict:
        """Default configuration"""
        return {
            'health_check_interval': 10,  # seconds
            'rmr_ready_timeout': 5,  # seconds
            'http_timeout': 5,  # seconds
            'failover_threshold': 3,  # consecutive failures before failover
            'recovery_threshold': 5,  # consecutive successes before recovery
            'max_retry_attempts': 2,
            'retry_delay': 0.5  # seconds
        }

    def initialize_rmr(self, use_fake_sdl: bool = False) -> bool:
        """
        Initialize RMR communication

        Args:
            use_fake_sdl: Use fake SDL for testing

        Returns:
            True if initialization successful
        """
        try:
            logger.info(f"Initializing RMR on port {self.rmr_port}")

            # Create RMR xApp with message handler wrapper
            self.rmr_xapp = RMRXapp(
                self._rmr_message_wrapper,
                rmr_port=self.rmr_port,
                use_fake_sdl=use_fake_sdl
            )

            # Wait for RMR to be ready
            ready_timeout = self.config['rmr_ready_timeout']
            start_time = time.time()

            while not self.is_rmr_ready():
                if time.time() - start_time > ready_timeout:
                    logger.error(f"RMR not ready after {ready_timeout}s timeout")
                    return False
                time.sleep(0.1)

            logger.info("RMR initialized successfully")
            self._update_path_health(CommunicationPath.RMR, success=True)
            rmr_health_status.set(1)

            return True

        except Exception as e:
            logger.error(f"Failed to initialize RMR: {e}")
            self._update_path_health(CommunicationPath.RMR, success=False)
            rmr_health_status.set(0)
            return False

    def is_rmr_ready(self) -> bool:
        """Check if RMR is ready"""
        if not self.rmr_xapp:
            return False
        try:
            # Use rmr_ready() to check RMR status
            return self.rmr_xapp.rmr_ready
        except:
            return False

    def _rmr_message_wrapper(self, xapp, summary: dict, sbuf):
        """
        Wrapper for RMR message handler

        Args:
            xapp: RMR xApp instance
            summary: Message summary
            sbuf: Message buffer
        """
        try:
            # Extract message info
            msg_type = summary.get(rmr.RMR_MS_MSG_TYPE, 0)

            # Call user's message handler
            if self.message_handler:
                self.message_handler(xapp, summary, sbuf)

            # Update health metrics
            self._update_path_health(CommunicationPath.RMR, success=True)

        except Exception as e:
            logger.error(f"Error in RMR message handler: {e}")
            self._update_path_health(CommunicationPath.RMR, success=False)

    def register_endpoint(self, endpoint: EndpointConfig):
        """
        Register an endpoint for HTTP fallback

        Args:
            endpoint: Endpoint configuration
        """
        self.endpoints[endpoint.service_name] = endpoint
        logger.info(f"Registered endpoint: {endpoint.service_name}")

    def send_message(
        self,
        msg_type: int,
        payload: Any,
        destination: Optional[str] = None,
        force_path: Optional[CommunicationPath] = None
    ) -> bool:
        """
        Send message with automatic path selection and failover

        Args:
            msg_type: RMR message type
            payload: Message payload (dict or string)
            destination: Destination service name (required for HTTP)
            force_path: Force specific communication path (for testing)

        Returns:
            True if message sent successfully
        """
        start_time = time.time()

        # Convert payload to string if needed
        if isinstance(payload, dict):
            payload_str = json.dumps(payload)
        else:
            payload_str = str(payload)

        # Determine which path to use
        with self.path_lock:
            if force_path:
                primary_path = force_path
                fallback_path = (CommunicationPath.HTTP
                               if force_path == CommunicationPath.RMR
                               else CommunicationPath.RMR)
            else:
                primary_path = self.current_path
                fallback_path = (CommunicationPath.HTTP
                               if primary_path == CommunicationPath.RMR
                               else CommunicationPath.RMR)

        # Try primary path
        success = self._send_via_path(
            primary_path, msg_type, payload_str, destination
        )

        if success:
            latency = time.time() - start_time
            message_latency.labels(path_type=primary_path.value).observe(latency)
            return True

        # Try fallback path
        logger.warning(
            f"Primary path {primary_path.value} failed, trying fallback {fallback_path.value}"
        )

        success = self._send_via_path(
            fallback_path, msg_type, payload_str, destination
        )

        if success:
            latency = time.time() - start_time
            message_latency.labels(path_type=fallback_path.value).observe(latency)

            # Consider failover if fallback succeeded
            self._evaluate_failover()

            return True

        # Both paths failed
        logger.error(f"Failed to send message type {msg_type} via both paths")
        messages_failed.labels(
            message_type=str(msg_type),
            path_type="both"
        ).inc()

        return False

    def _send_via_path(
        self,
        path: CommunicationPath,
        msg_type: int,
        payload: str,
        destination: Optional[str]
    ) -> bool:
        """
        Send message via specific path

        Args:
            path: Communication path to use
            msg_type: Message type
            payload: Message payload as string
            destination: Destination service name

        Returns:
            True if successful
        """
        if path == CommunicationPath.RMR:
            return self._send_via_rmr(msg_type, payload, destination)
        else:
            return self._send_via_http(msg_type, payload, destination)

    def _send_via_rmr(
        self,
        msg_type: int,
        payload: str,
        destination: Optional[str]
    ) -> bool:
        """
        Send message via RMR

        Args:
            msg_type: RMR message type
            payload: Message payload
            destination: Destination (logged but not used in RMR routing)

        Returns:
            True if successful
        """
        if not self.rmr_xapp or not self.is_rmr_ready():
            logger.warning("RMR not ready, cannot send message")
            self._update_path_health(CommunicationPath.RMR, success=False)
            return False

        try:
            # Send via RMR
            success = self.rmr_xapp.rmr_send(payload.encode(), msg_type)

            if success:
                logger.debug(
                    f"Sent message type {msg_type} via RMR "
                    f"(destination: {destination or 'routed'})"
                )
                messages_sent_rmr.labels(
                    message_type=str(msg_type),
                    destination=destination or "routed"
                ).inc()
                self._update_path_health(CommunicationPath.RMR, success=True)
                return True
            else:
                logger.warning(f"RMR send failed for message type {msg_type}")
                self._update_path_health(CommunicationPath.RMR, success=False)
                return False

        except Exception as e:
            logger.error(f"Exception sending via RMR: {e}")
            self._update_path_health(CommunicationPath.RMR, success=False)
            return False

    def _send_via_http(
        self,
        msg_type: int,
        payload: str,
        destination: Optional[str]
    ) -> bool:
        """
        Send message via HTTP fallback

        Args:
            msg_type: Message type
            payload: Message payload
            destination: Destination service name (required)

        Returns:
            True if successful
        """
        if not destination:
            logger.error("HTTP fallback requires destination service name")
            return False

        if destination not in self.endpoints:
            logger.error(f"No endpoint registered for {destination}")
            return False

        endpoint = self.endpoints[destination]
        url = f"{endpoint.http_base_url}{endpoint.message_endpoint}"

        try:
            # Prepare payload
            payload_dict = json.loads(payload) if isinstance(payload, str) else payload
            payload_dict['message_type'] = msg_type
            payload_dict['source_xapp'] = self.xapp_name

            # Send HTTP POST
            response = self.http_session.post(
                url,
                json=payload_dict,
                timeout=self.config['http_timeout']
            )

            if response.status_code == 200:
                logger.debug(f"Sent message type {msg_type} via HTTP to {destination}")
                messages_sent_http.labels(
                    message_type=str(msg_type),
                    destination=destination
                ).inc()
                self._update_path_health(CommunicationPath.HTTP, success=True)
                return True
            else:
                logger.warning(
                    f"HTTP send failed with status {response.status_code}: "
                    f"{response.text}"
                )
                self._update_path_health(CommunicationPath.HTTP, success=False)
                return False

        except requests.exceptions.Timeout:
            logger.warning(f"HTTP request to {destination} timed out")
            self._update_path_health(CommunicationPath.HTTP, success=False)
            return False
        except Exception as e:
            logger.error(f"Exception sending via HTTP: {e}")
            self._update_path_health(CommunicationPath.HTTP, success=False)
            return False

    def _update_path_health(self, path: CommunicationPath, success: bool):
        """
        Update health metrics for a communication path

        Args:
            path: Communication path
            success: Whether the operation was successful
        """
        with self.path_lock:
            metrics = self.path_health[path]
            current_time = time.time()

            if success:
                metrics.last_success_time = current_time
                metrics.consecutive_successes += 1
                metrics.consecutive_failures = 0
                metrics.total_sent += 1

                # Update status
                if metrics.consecutive_successes >= self.config['recovery_threshold']:
                    old_status = metrics.status
                    metrics.status = PathStatus.HEALTHY
                    if old_status != PathStatus.HEALTHY:
                        logger.info(f"{path.value.upper()} path recovered to HEALTHY")

            else:
                metrics.last_failure_time = current_time
                metrics.consecutive_failures += 1
                metrics.consecutive_successes = 0
                metrics.total_failed += 1

                # Update status
                if metrics.consecutive_failures >= self.config['failover_threshold']:
                    old_status = metrics.status
                    metrics.status = PathStatus.DOWN
                    if old_status != PathStatus.DOWN:
                        logger.warning(f"{path.value.upper()} path marked as DOWN")
                elif metrics.consecutive_failures > 0:
                    metrics.status = PathStatus.DEGRADED

            # Update Prometheus metrics
            if path == CommunicationPath.RMR:
                rmr_health_status.set(1 if metrics.status == PathStatus.HEALTHY else 0)
            else:
                http_health_status.set(1 if metrics.status == PathStatus.HEALTHY else 0)

    def _evaluate_failover(self):
        """Evaluate if failover is needed and execute if necessary"""
        with self.path_lock:
            rmr_metrics = self.path_health[CommunicationPath.RMR]
            http_metrics = self.path_health[CommunicationPath.HTTP]

            # Check if current path is unhealthy
            current_metrics = self.path_health[self.current_path]

            if current_metrics.status == PathStatus.DOWN:
                # Failover to other path if it's healthier
                other_path = (CommunicationPath.HTTP
                            if self.current_path == CommunicationPath.RMR
                            else CommunicationPath.RMR)
                other_metrics = self.path_health[other_path]

                if other_metrics.status != PathStatus.DOWN:
                    self._execute_failover(other_path)

            # Check if we should recover back to RMR (preferred path)
            elif (self.current_path == CommunicationPath.HTTP and
                  rmr_metrics.status == PathStatus.HEALTHY and
                  rmr_metrics.consecutive_successes >= self.config['recovery_threshold']):
                logger.info("RMR path fully recovered, switching back to RMR")
                self._execute_failover(CommunicationPath.RMR)

    def _execute_failover(self, new_path: CommunicationPath):
        """
        Execute failover to new path

        Args:
            new_path: Path to failover to
        """
        old_path = self.current_path

        if old_path == new_path:
            return

        logger.warning(
            f"FAILOVER: Switching from {old_path.value.upper()} to {new_path.value.upper()}"
        )

        self.current_path = new_path

        # Update metrics
        failover_events.labels(
            from_path=old_path.value,
            to_path=new_path.value
        ).inc()

        active_path.set(1 if new_path == CommunicationPath.RMR else 0)

        logger.info(f"Active communication path: {new_path.value.upper()}")

    def _health_check_loop(self):
        """Periodic health check for both paths"""
        while self.running:
            try:
                # Check RMR health
                rmr_healthy = self.is_rmr_ready()
                if not rmr_healthy:
                    logger.debug("RMR health check failed")
                    self._update_path_health(CommunicationPath.RMR, success=False)

                # Check HTTP health for all registered endpoints
                for service_name, endpoint in self.endpoints.items():
                    try:
                        url = f"{endpoint.http_base_url}{endpoint.health_endpoint}"
                        response = self.http_session.get(url, timeout=2)

                        if response.status_code == 200:
                            self._update_path_health(CommunicationPath.HTTP, success=True)
                        else:
                            logger.debug(
                                f"HTTP health check failed for {service_name}: "
                                f"status {response.status_code}"
                            )
                    except Exception as e:
                        logger.debug(f"HTTP health check failed for {service_name}: {e}")

                # Evaluate failover based on health
                self._evaluate_failover()

                # Log current status
                with self.path_lock:
                    rmr_status = self.path_health[CommunicationPath.RMR].status.value
                    http_status = self.path_health[CommunicationPath.HTTP].status.value
                    active = self.current_path.value.upper()

                logger.debug(
                    f"Health Status - RMR: {rmr_status}, HTTP: {http_status}, "
                    f"Active: {active}"
                )

            except Exception as e:
                logger.error(f"Error in health check loop: {e}")

            time.sleep(self.config['health_check_interval'])

    def start(self):
        """Start the dual-path messenger"""
        logger.info("Starting DualPathMessenger")
        self.running = True

        # Start health check thread
        self.health_check_thread = Thread(target=self._health_check_loop, daemon=True)
        self.health_check_thread.start()

        logger.info("DualPathMessenger started")

    def stop(self):
        """Stop the dual-path messenger"""
        logger.info("Stopping DualPathMessenger")
        self.running = False

        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)

        if self.rmr_xapp:
            self.rmr_xapp.stop()

        self.http_session.close()

        logger.info("DualPathMessenger stopped")

    def get_health_summary(self) -> Dict:
        """
        Get health summary for both paths

        Returns:
            Dictionary with health information
        """
        with self.path_lock:
            return {
                'active_path': self.current_path.value,
                'rmr': {
                    'status': self.path_health[CommunicationPath.RMR].status.value,
                    'last_success': self.path_health[CommunicationPath.RMR].last_success_time,
                    'last_failure': self.path_health[CommunicationPath.RMR].last_failure_time,
                    'total_sent': self.path_health[CommunicationPath.RMR].total_sent,
                    'total_failed': self.path_health[CommunicationPath.RMR].total_failed,
                },
                'http': {
                    'status': self.path_health[CommunicationPath.HTTP].status.value,
                    'last_success': self.path_health[CommunicationPath.HTTP].last_success_time,
                    'last_failure': self.path_health[CommunicationPath.HTTP].last_failure_time,
                    'total_sent': self.path_health[CommunicationPath.HTTP].total_sent,
                    'total_failed': self.path_health[CommunicationPath.HTTP].total_failed,
                },
                'endpoints': list(self.endpoints.keys())
            }
