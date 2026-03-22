from __future__ import annotations

from .discovery import HttpRegistryDiscovery, K8sServiceDiscovery, ServiceDiscovery
from .registration import ApplicationRegistrar

__all__ = [
    "ApplicationRegistrar",
    "HttpRegistryDiscovery",
    "K8sServiceDiscovery",
    "ServiceDiscovery",
]
