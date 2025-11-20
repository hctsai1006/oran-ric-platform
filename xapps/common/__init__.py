"""
O-RAN SC Common Libraries for xApps
Release J compliant communication and utilities
"""

from .dual_path_messenger import (
    DualPathMessenger,
    CommunicationPath,
    PathStatus,
    EndpointConfig,
    PathHealthMetrics
)

__all__ = [
    'DualPathMessenger',
    'CommunicationPath',
    'PathStatus',
    'EndpointConfig',
    'PathHealthMetrics'
]

__version__ = '1.0.0'
__release__ = 'J'
