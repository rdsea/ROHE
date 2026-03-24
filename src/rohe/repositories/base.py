from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class NodeRepository(ABC):
    """Repository for compute node state management."""

    @abstractmethod
    def get_node(self, node_name: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def get_all_nodes(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def upsert_node(self, node_name: str, node_data: dict[str, Any]) -> None: ...

    @abstractmethod
    def delete_node(self, node_name: str) -> bool: ...


class ServiceRepository(ABC):
    """Repository for ML inference service management."""

    @abstractmethod
    def get_service(self, service_name: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def get_all_services(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def upsert_service(
        self, service_name: str, service_data: dict[str, Any]
    ) -> None: ...

    @abstractmethod
    def delete_service(self, service_name: str) -> bool: ...


class MetricRepository(ABC):
    """Repository for observation metrics (per-request and per-period)."""

    @abstractmethod
    def insert_metric(self, metric: dict[str, Any]) -> str: ...

    @abstractmethod
    def insert_metrics_batch(self, metrics: list[dict[str, Any]]) -> int: ...

    @abstractmethod
    def query_metrics(
        self,
        filters: dict[str, Any] | None = None,
        time_from: datetime | None = None,
        time_to: datetime | None = None,
        limit: int = 10000,
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    def aggregate_metrics(
        self,
        pipeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    def delete_metrics(
        self,
        filters: dict[str, Any],
    ) -> int: ...


class ContractRepository(ABC):
    """Repository for service contracts and CDM definitions."""

    @abstractmethod
    def get_contract(self, contract_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def list_contracts(
        self,
        tenant_id: str | None = None,
        pipeline_id: str | None = None,
        is_active: bool | None = None,
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    def create_contract(self, contract: dict[str, Any]) -> str: ...

    @abstractmethod
    def update_contract(self, contract_id: str, updates: dict[str, Any]) -> bool: ...

    @abstractmethod
    def deactivate_contract(self, contract_id: str) -> bool: ...

    @abstractmethod
    def get_cdm(self, cdm_name: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def list_cdms(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def upsert_cdm(self, cdm: dict[str, Any]) -> None: ...


class PipelineRepository(ABC):
    """Repository for pipeline definitions and application registration."""

    @abstractmethod
    def get_application(self, application_name: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def register_application(self, app_data: dict[str, Any]) -> str: ...

    @abstractmethod
    def update_application(
        self, application_name: str, updates: dict[str, Any]
    ) -> bool: ...

    @abstractmethod
    def delete_application(self, application_name: str) -> bool: ...

    @abstractmethod
    def list_applications(self) -> list[dict[str, Any]]: ...


class ExperimentRepository(ABC):
    """Repository for experiment lifecycle and metadata."""

    @abstractmethod
    def create_experiment(self, experiment: dict[str, Any]) -> str: ...

    @abstractmethod
    def get_experiment(self, experiment_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def get_experiment_by_name(self, name: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def update_experiment(
        self, experiment_id: str, updates: dict[str, Any]
    ) -> bool: ...

    @abstractmethod
    def list_experiments(
        self,
        status: str | None = None,
        pipeline_id: str | None = None,
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    def delete_experiment(self, experiment_id: str) -> bool: ...
