from __future__ import annotations

import functools
import logging
import os
import time
from collections.abc import Callable
from datetime import datetime, timezone
from threading import Lock, Thread
from typing import Any, TypeVar

from .transport import HttpTransport, MetricPayload, MetricTransport

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class RoheMonitor:
    """Lightweight monitoring SDK for reporting metrics to ROHE Observation Service.

    Designed for ML inference services and clients. Non-blocking, with
    async batching and graceful degradation when the endpoint is unreachable.

    Usage:
        monitor = RoheMonitor.from_env()
        monitor.report_inference(
            query_id="q-001",
            predictions={"car": 0.92},
            confidence=0.92,
            response_time_ms=45.2,
            labels={"model": "yolov8n"},
        )
    """

    def __init__(
        self,
        endpoint: str,
        service_name: str,
        experiment_id: str | None = None,
        transport: MetricTransport | None = None,
        batch_size: int = 100,
        flush_interval_seconds: float = 5.0,
    ) -> None:
        self._endpoint = endpoint
        self._service_name = service_name
        self._experiment_id = experiment_id
        self._transport = transport or HttpTransport(endpoint)
        self._batch_size = batch_size
        self._flush_interval = flush_interval_seconds

        self._buffer: list[MetricPayload] = []
        self._lock = Lock()
        self._is_running = True

        # Start background flush thread
        self._flush_thread = Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()

    @classmethod
    def from_env(cls) -> RoheMonitor:
        """Create monitor from environment variables.

        Reads: ROHE_ENDPOINT, ROHE_SERVICE_NAME, ROHE_EXPERIMENT_ID
        """
        endpoint = os.environ.get("ROHE_ENDPOINT", "http://localhost:5010/metrics")
        service_name = os.environ.get("ROHE_SERVICE_NAME", "unknown")
        experiment_id = os.environ.get("ROHE_EXPERIMENT_ID")

        return cls(
            endpoint=endpoint,
            service_name=service_name,
            experiment_id=experiment_id,
        )

    def report_metric(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Report a generic metric (non-blocking)."""
        payload = MetricPayload(
            timestamp=datetime.now(tz=timezone.utc),
            service_name=self._service_name,
            experiment_id=self._experiment_id,
            metric_type="generic",
            name=name,
            value=value,
            labels=labels or {},
        )
        self._enqueue(payload)

    def report_inference(
        self,
        query_id: str,
        predictions: dict[str, float],
        confidence: float,
        response_time_ms: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Report inference result from an ML service (non-blocking)."""
        payload = MetricPayload(
            timestamp=datetime.now(tz=timezone.utc),
            service_name=self._service_name,
            experiment_id=self._experiment_id,
            metric_type="inference",
            name="inference",
            query_id=query_id,
            predictions=predictions,
            confidence=confidence,
            response_time_ms=response_time_ms,
            labels=labels or {},
        )
        self._enqueue(payload)

    def report_request(
        self,
        query_id: str,
        pipeline_id: str,
        response_time_ms: float,
        ground_truth: str | None = None,
        prediction: dict[str, float] | None = None,
    ) -> None:
        """Report request result from a client (non-blocking).

        Includes ground truth for accuracy evaluation by the platform.
        """
        payload = MetricPayload(
            timestamp=datetime.now(tz=timezone.utc),
            service_name=self._service_name,
            experiment_id=self._experiment_id,
            metric_type="request",
            name="request",
            query_id=query_id,
            response_time_ms=response_time_ms,
            ground_truth=ground_truth,
            predictions=prediction,
            labels={"pipeline_id": pipeline_id},
        )
        self._enqueue(payload)

    def track_inference(self, func: F) -> F:
        """Decorator that auto-reports inference timing and result.

        The decorated function must return a dict with 'predictions' and 'confidence' keys.
        """

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000

            if isinstance(result, dict):
                self.report_inference(
                    query_id=result.get("query_id", "unknown"),
                    predictions=result.get("predictions", {}),
                    confidence=result.get("confidence", 0.0),
                    response_time_ms=elapsed_ms,
                    labels=result.get("labels"),
                )

            return result

        return wrapper  # type: ignore[return-value]

    def flush(self) -> None:
        """Force flush the buffer (blocking)."""
        with self._lock:
            if not self._buffer:
                return
            batch = self._buffer.copy()
            self._buffer.clear()

        self._transport.send_batch(batch)

    def close(self) -> None:
        """Flush remaining metrics and stop background thread."""
        self._is_running = False
        self.flush()

    def _enqueue(self, payload: MetricPayload) -> None:
        """Add metric to buffer. Triggers flush if batch size reached."""
        with self._lock:
            self._buffer.append(payload)
            should_flush = len(self._buffer) >= self._batch_size

        if should_flush:
            self.flush()

    def _flush_loop(self) -> None:
        """Background thread: flush buffer every flush_interval seconds."""
        while self._is_running:
            time.sleep(self._flush_interval)
            try:
                self.flush()
            except Exception:
                logger.debug("Failed to flush metrics, will retry", exc_info=True)
