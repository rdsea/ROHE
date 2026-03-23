"""Service registry interface for inference orchestration.

Abstracts the data layer for service/instance discovery, SLA lookup,
and result reporting. Implementations can use DuckDB (legacy), Redis,
or MongoDB as backends.
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from rohe.models.contracts import ServiceLevelAgreement
from rohe.models.enums import InstanceStatus
from rohe.models.pipeline import (
    InferenceServiceInstance,
    InferenceServiceProfile,
    MonitoringReport,
)

logger = logging.getLogger(__name__)


class ServiceRegistry(ABC):
    """Abstract interface for service/instance discovery and reporting."""

    @abstractmethod
    def get_services(self, modality: str | None = None) -> dict[str, InferenceServiceProfile]:
        """Get available inference services, optionally filtered by modality."""
        ...

    @abstractmethod
    def get_instances(
        self, service_id: str | None = None, status: InstanceStatus | None = None,
    ) -> dict[str, InferenceServiceInstance]:
        """Get running instances, optionally filtered by service and status."""
        ...

    @abstractmethod
    def get_sla(self, consumer_id: str) -> ServiceLevelAgreement | None:
        """Look up SLA for a consumer/tenant."""
        ...

    @abstractmethod
    def report_result(self, report: MonitoringReport) -> None:
        """Store an inference monitoring report."""
        ...

    @abstractmethod
    def refresh(self) -> None:
        """Refresh cached data from the backend."""
        ...


class DuckDBServiceRegistry(ServiceRegistry):
    """ServiceRegistry backed by DuckDB (legacy backend)."""

    def __init__(
        self,
        db_path: str,
        service_table: str = "inference_service_table",
        instance_table: str = "inference_service_instance_table",
        monitoring_table: str = "inference_result_table",
    ) -> None:
        self._db_path = db_path
        self._service_table = service_table
        self._instance_table = instance_table
        self._monitoring_table = monitoring_table
        self._services: dict[str, InferenceServiceProfile] = {}
        self._instances: dict[str, InferenceServiceInstance] = {}

    def get_services(self, modality: str | None = None) -> dict[str, InferenceServiceProfile]:
        if modality:
            return {
                k: v for k, v in self._services.items()
                if v.modality == modality
            }
        return dict(self._services)

    def get_instances(
        self, service_id: str | None = None, status: InstanceStatus | None = None,
    ) -> dict[str, InferenceServiceInstance]:
        result = dict(self._instances)
        if service_id:
            result = {
                k: v for k, v in result.items()
                if v.inference_service_id == service_id
            }
        if status:
            result = {
                k: v for k, v in result.items()
                if v.status == status.value
            }
        return result

    def get_sla(self, consumer_id: str) -> ServiceLevelAgreement | None:
        try:
            import duckdb
            conn = duckdb.connect(self._db_path, read_only=True)
            rows = conn.execute(
                "SELECT * FROM sla_table WHERE tenant_id = ?", [consumer_id]
            ).fetchall()
            conn.close()
            if rows:
                cols = [desc[0] for desc in conn.description] if conn.description else []
                data = dict(zip(cols, rows[0]))
                return ServiceLevelAgreement.from_dict(data)
        except Exception as e:
            logger.warning(f"SLA lookup failed for '{consumer_id}': {e}")
        return None

    def report_result(self, report: MonitoringReport) -> None:
        try:
            import duckdb
            conn = duckdb.connect(self._db_path)
            conn.execute(
                f"INSERT INTO {self._monitoring_table} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    report.query_id, report.inf_id, str(report.data_source),
                    report.time_window, report.model_id, report.model_version,
                    report.device_id, report.instance_id, report.response_time,
                    report.inf_time, str(report.inf_result), report.explainability,
                    report.time_violation, report.time_for_inference,
                ],
            )
            conn.close()
        except Exception as e:
            logger.warning(f"DuckDB report failed: {e}")

    def refresh(self) -> None:
        """Load services and instances from DuckDB."""
        try:
            import duckdb
            conn = duckdb.connect(self._db_path, read_only=True)

            rows = conn.execute(f"SELECT * FROM {self._service_table}").fetchall()
            cols = [desc[0] for desc in conn.description] if conn.description else []
            self._services = {}
            for row in rows:
                data = dict(zip(cols, row))
                svc = InferenceServiceProfile.from_dict(data)
                self._services[svc.inference_service_id] = svc

            rows = conn.execute(f"SELECT * FROM {self._instance_table}").fetchall()
            cols = [desc[0] for desc in conn.description] if conn.description else []
            self._instances = {}
            for row in rows:
                data = dict(zip(cols, row))
                inst = InferenceServiceInstance.from_dict(data)
                self._instances[inst.instance_id] = inst

            conn.close()
            logger.debug(
                f"Registry refreshed: {len(self._services)} services, "
                f"{len(self._instances)} instances"
            )
        except Exception as e:
            logger.warning(f"DuckDB refresh failed: {e}")


class InMemoryServiceRegistry(ServiceRegistry):
    """In-memory ServiceRegistry for testing and simulation.

    Services and instances are populated programmatically or from
    an ExecutionPlan.
    """

    def __init__(self) -> None:
        self._services: dict[str, InferenceServiceProfile] = {}
        self._instances: dict[str, InferenceServiceInstance] = {}
        self._slas: dict[str, ServiceLevelAgreement] = {}
        self._reports: list[MonitoringReport] = []

    def get_services(self, modality: str | None = None) -> dict[str, InferenceServiceProfile]:
        if modality:
            return {k: v for k, v in self._services.items() if v.modality == modality}
        return dict(self._services)

    def get_instances(
        self, service_id: str | None = None, status: InstanceStatus | None = None,
    ) -> dict[str, InferenceServiceInstance]:
        result = dict(self._instances)
        if service_id:
            result = {k: v for k, v in result.items() if v.inference_service_id == service_id}
        if status:
            result = {k: v for k, v in result.items() if v.status == status.value}
        return result

    def get_sla(self, consumer_id: str) -> ServiceLevelAgreement | None:
        return self._slas.get(consumer_id)

    def report_result(self, report: MonitoringReport) -> None:
        self._reports.append(report)

    def refresh(self) -> None:
        pass

    def add_service(self, service: InferenceServiceProfile) -> None:
        self._services[service.inference_service_id] = service

    def add_instance(self, instance: InferenceServiceInstance) -> None:
        self._instances[instance.instance_id] = instance

    def add_sla(self, consumer_id: str, sla: ServiceLevelAgreement) -> None:
        self._slas[consumer_id] = sla
