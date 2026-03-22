from __future__ import annotations

import logging
import os
import uuid
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class ServiceDiscovery(ABC):
    """Abstract interface for service discovery (D3).

    Two implementations:
    - K8sServiceDiscovery: uses K8s-native DNS/Services (primary)
    - HttpRegistryDiscovery: lightweight HTTP-based fallback for non-K8s
    """

    @abstractmethod
    def register(self, service_name: str, host: str, port: int, metadata: dict[str, Any] | None = None) -> str:
        """Register a service instance. Returns instance ID."""
        ...

    @abstractmethod
    def deregister(self, instance_id: str) -> bool:
        """Deregister a service instance."""
        ...

    @abstractmethod
    def discover(self, service_name: str) -> list[dict[str, Any]]:
        """Discover all instances of a service."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the discovery backend is healthy."""
        ...


class K8sServiceDiscovery(ServiceDiscovery):
    """Kubernetes-native service discovery via DNS and API.

    In K8s, services are automatically discoverable via DNS:
    <service-name>.<namespace>.svc.cluster.local
    """

    def __init__(self, namespace: str = "default") -> None:
        self.namespace = namespace
        self._is_k8s = self._detect_k8s()
        if self._is_k8s:
            logger.info(f"K8s service discovery initialized for namespace '{namespace}'")
        else:
            logger.warning("Not running in K8s cluster, K8s discovery will be limited")

    @staticmethod
    def _detect_k8s() -> bool:
        """Detect if running inside a K8s cluster."""
        return os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token")

    def register(self, service_name: str, host: str, port: int, metadata: dict[str, Any] | None = None) -> str:
        """In K8s, registration is handled by K8s Service resources. This is a no-op."""
        instance_id = f"{service_name}-{host}-{port}"
        logger.info(f"K8s service '{service_name}' registered (managed by K8s): {instance_id}")
        return instance_id

    def deregister(self, instance_id: str) -> bool:
        """In K8s, deregistration is handled by K8s. This is a no-op."""
        logger.info(f"K8s service deregistered (managed by K8s): {instance_id}")
        return True

    def discover(self, service_name: str) -> list[dict[str, Any]]:
        """Discover service via K8s DNS.

        Returns the DNS name that resolves to service endpoints.
        For full endpoint enumeration, use the K8s API.
        """
        dns_name = f"{service_name}.{self.namespace}.svc.cluster.local"
        return [{"service_name": service_name, "dns": dns_name, "namespace": self.namespace}]

    def health_check(self) -> bool:
        return self._is_k8s


class HttpRegistryDiscovery(ServiceDiscovery):
    """HTTP-based service discovery for non-K8s environments.

    Services self-register via HTTP and are discovered via the registry API.
    Uses an in-memory store (suitable for development and small deployments).
    """

    def __init__(self) -> None:
        self._services: dict[str, dict[str, Any]] = {}
        logger.info("HTTP registry discovery initialized (in-memory)")

    def register(self, service_name: str, host: str, port: int, metadata: dict[str, Any] | None = None) -> str:
        instance_id = str(uuid.uuid4())
        self._services[instance_id] = {
            "instance_id": instance_id,
            "service_name": service_name,
            "host": host,
            "port": port,
            "metadata": metadata or {},
        }
        logger.info(f"Registered service '{service_name}' at {host}:{port} as {instance_id}")
        return instance_id

    def deregister(self, instance_id: str) -> bool:
        if instance_id in self._services:
            removed = self._services.pop(instance_id)
            logger.info(f"Deregistered service '{removed['service_name']}': {instance_id}")
            return True
        return False

    def discover(self, service_name: str) -> list[dict[str, Any]]:
        return [
            svc for svc in self._services.values()
            if svc["service_name"] == service_name
        ]

    def health_check(self) -> bool:
        return True


def create_service_discovery() -> ServiceDiscovery:
    """Factory: create the appropriate ServiceDiscovery based on environment.

    Uses K8s discovery if running in a cluster, falls back to HTTP registry.
    Can be overridden via ROHE_DISCOVERY_MODE env var ('k8s' or 'http').
    """
    mode = os.environ.get("ROHE_DISCOVERY_MODE", "auto")

    if mode == "k8s":
        namespace = os.environ.get("ROHE_K8S_NAMESPACE", "default")
        return K8sServiceDiscovery(namespace=namespace)

    if mode == "http":
        return HttpRegistryDiscovery()

    # Auto-detect
    if K8sServiceDiscovery._detect_k8s():
        namespace = os.environ.get("ROHE_K8S_NAMESPACE", "default")
        return K8sServiceDiscovery(namespace=namespace)

    return HttpRegistryDiscovery()
