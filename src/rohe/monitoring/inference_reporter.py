"""Inference result reporter for the orchestrator.

Reports inference monitoring data to a configured backend (DuckDB, HTTP, etc.).
Extracted from the legacy MonitoringClient that was embedded in data models.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from rohe.models.pipeline import MonitoringReport

logger = logging.getLogger(__name__)


class InferenceReporter(ABC):
    """Abstract reporter for inference monitoring data."""

    @abstractmethod
    def report(self, report: MonitoringReport) -> None:
        """Send a monitoring report to the backend."""
        ...


class LoggingReporter(InferenceReporter):
    """Reports inference results to the log (for testing/development)."""

    def report(self, report: MonitoringReport) -> None:
        logger.info(
            f"Inference report: query={report.query_id}, model={report.model_id}, "
            f"instance={report.instance_id}, time={report.response_time:.4f}s"
        )


class DuckDBReporter(InferenceReporter):
    """Reports inference results to DuckDB (legacy backend)."""

    def __init__(self, db_path: str, table_name: str) -> None:
        self._db_path = db_path
        self._table_name = table_name

    def report(self, report: MonitoringReport) -> None:
        try:
            import duckdb

            conn = duckdb.connect(self._db_path)
            conn.execute(
                f"INSERT INTO {self._table_name} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    report.query_id,
                    report.inf_id,
                    str(report.data_source),
                    report.time_window,
                    report.model_id,
                    report.model_version,
                    report.device_id,
                    report.instance_id,
                    report.response_time,
                    report.inf_time,
                    str(report.inf_result),
                    report.explainability,
                    report.time_violation,
                    report.time_for_inference,
                ],
            )
            conn.close()
        except Exception as e:
            logger.warning(f"DuckDB report failed: {e}")


class HttpReporter(InferenceReporter):
    """Reports inference results to an HTTP endpoint."""

    def __init__(self, endpoint_url: str) -> None:
        self._url = endpoint_url

    def report(self, report: MonitoringReport) -> None:
        try:
            import httpx

            with httpx.Client(timeout=5.0) as client:
                client.post(self._url, json=report.model_dump(mode="json"))
        except Exception as e:
            logger.warning(f"HTTP report failed: {e}")


class NoOpReporter(InferenceReporter):
    """Does nothing. Used when monitoring is disabled."""

    def report(self, report: MonitoringReport) -> None:
        pass
