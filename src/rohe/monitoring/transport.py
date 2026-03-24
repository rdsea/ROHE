from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime

import httpx
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class MetricPayload(BaseModel):
    """A single metric report payload."""

    model_config = ConfigDict(protected_namespaces=())

    timestamp: datetime
    service_name: str
    experiment_id: str | None = None
    metric_type: str  # "generic", "inference", "request"
    name: str
    value: float | None = None
    labels: dict[str, str] = {}
    query_id: str | None = None
    predictions: dict[str, float] | None = None
    confidence: float | None = None
    response_time_ms: float | None = None
    ground_truth: str | None = None


class MetricTransport(ABC):
    """Abstract transport for sending metric batches."""

    @abstractmethod
    def send_batch(self, metrics: list[MetricPayload]) -> None:
        """Send a batch of metrics to the observation service."""
        ...


class HttpTransport(MetricTransport):
    """Send metrics via HTTP POST to the ROHE Observation Service."""

    def __init__(self, endpoint: str, max_retries: int = 3) -> None:
        self._endpoint = endpoint
        self._max_retries = max_retries

    def send_batch(self, metrics: list[MetricPayload]) -> None:
        """Send batch via HTTP. Retries with exponential backoff on failure."""
        if not metrics:
            return

        payload = [m.model_dump(mode="json") for m in metrics]

        for attempt in range(self._max_retries):
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.post(
                        self._endpoint,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    )
                    if response.status_code < 300:
                        logger.debug(f"Sent {len(metrics)} metrics to {self._endpoint}")
                        return
                    logger.warning(
                        f"Metric send failed (HTTP {response.status_code}), "
                        f"attempt {attempt + 1}/{self._max_retries}"
                    )
            except Exception:
                logger.debug(
                    f"Metric transport error, attempt {attempt + 1}/{self._max_retries}",
                    exc_info=True,
                )

            if attempt < self._max_retries - 1:
                time.sleep(0.5 * (2**attempt))

        logger.debug(
            f"Dropping {len(metrics)} metrics after {self._max_retries} retries"
        )


class NoopTransport(MetricTransport):
    """Transport that discards all metrics. Used for testing and standalone mode."""

    def __init__(self) -> None:
        self.sent: list[list[MetricPayload]] = []

    def send_batch(self, metrics: list[MetricPayload]) -> None:
        self.sent.append(metrics)
