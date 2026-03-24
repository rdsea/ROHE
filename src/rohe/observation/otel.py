"""OpenTelemetry integration for ROHE infrastructure metrics.

Provides OTel-based metric collection for infrastructure-level monitoring
(CPU, memory, GPU, network) alongside ROHE's custom ML quality metrics.

This is the "infra metrics" half of the hybrid observation strategy (D2):
- OTel handles infrastructure metrics (standardized, widely supported)
- ROHE's custom observation handles ML quality metrics (CDMs, per-class accuracy)

Usage:
    # In any service
    from rohe.observation.otel import setup_otel_metrics, record_inference_metric

    setup_otel_metrics(service_name="lstm-inference", endpoint="http://otel-collector:4317")
    record_inference_metric(model="lstm", latency_ms=12.5, confidence=0.85)

Environment variables:
    OTEL_EXPORTER_OTLP_ENDPOINT: OTel collector endpoint (default: http://localhost:4317)
    OTEL_SERVICE_NAME: Service name for OTel resource
    OTEL_ENABLED: "true" to enable (default: "false")
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_meter: Any = None
_counters: dict[str, Any] = {}
_histograms: dict[str, Any] = {}


def setup_otel_metrics(
    service_name: str = "",
    endpoint: str = "",
) -> bool:
    """Initialize OpenTelemetry metrics exporter.

    Returns True if OTel was successfully initialized.
    """
    global _meter

    enabled = os.environ.get("OTEL_ENABLED", "false").lower() == "true"
    if not enabled:
        logger.debug("OTel disabled (set OTEL_ENABLED=true to enable)")
        return False

    service_name = service_name or os.environ.get("OTEL_SERVICE_NAME", "rohe-service")
    endpoint = endpoint or os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
    )

    try:
        from opentelemetry import metrics
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({"service.name": service_name})
        exporter = OTLPMetricExporter(endpoint=endpoint, insecure=True)
        reader = PeriodicExportingMetricReader(exporter, export_interval_millis=10000)
        provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(provider)

        _meter = metrics.get_meter("rohe.inference", "1.0.0")

        # Create standard instruments
        _counters["inference_requests"] = _meter.create_counter(
            "rohe.inference.requests",
            description="Total inference requests",
            unit="1",
        )
        _histograms["inference_latency"] = _meter.create_histogram(
            "rohe.inference.latency",
            description="Inference latency",
            unit="ms",
        )
        _histograms["inference_confidence"] = _meter.create_histogram(
            "rohe.inference.confidence",
            description="Inference confidence scores",
            unit="1",
        )
        _counters["sla_violations"] = _meter.create_counter(
            "rohe.sla.violations",
            description="SLA violation count",
            unit="1",
        )

        logger.info(
            f"OTel metrics initialized: service={service_name}, endpoint={endpoint}"
        )
        return True

    except ImportError:
        logger.debug("opentelemetry packages not installed, OTel disabled")
        return False
    except Exception as e:
        logger.warning(f"OTel initialization failed: {e}")
        return False


def record_inference_metric(
    model: str,
    latency_ms: float,
    confidence: float,
    pipeline_id: str = "",
    modality: str = "",
) -> None:
    """Record an inference metric via OTel."""
    if _meter is None:
        return

    attributes = {"model": model, "pipeline_id": pipeline_id, "modality": modality}

    if "inference_requests" in _counters:
        _counters["inference_requests"].add(1, attributes)
    if "inference_latency" in _histograms:
        _histograms["inference_latency"].record(latency_ms, attributes)
    if "inference_confidence" in _histograms:
        _histograms["inference_confidence"].record(confidence, attributes)


def record_sla_violation(
    pipeline_id: str,
    metric_name: str,
    severity: str,
) -> None:
    """Record an SLA violation event via OTel."""
    if _meter is None:
        return

    attributes = {
        "pipeline_id": pipeline_id,
        "metric_name": metric_name,
        "severity": severity,
    }
    if "sla_violations" in _counters:
        _counters["sla_violations"].add(1, attributes)


def is_enabled() -> bool:
    """Check if OTel metrics are initialized."""
    return _meter is not None
