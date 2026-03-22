"""Data ingestion service: receives raw sensor data, normalizes, and returns."""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(title="BTS Data Ingestion Service")

# Normalization parameters for 6 sensor channels:
# [temperature_c, humidity_pct, hvac_power_kw, lighting_power_kw, occupancy_count, solar_irradiance_wm2]
SENSOR_MEANS = [22.0, 50.0, 15.0, 5.0, 50.0, 400.0]
SENSOR_STDS = [5.0, 15.0, 8.0, 3.0, 30.0, 200.0]

# Optional rohe-sdk monitoring
try:
    from rohe.monitoring.sdk import RoheMonitor
    monitor = RoheMonitor.from_env()
except Exception:
    monitor = None  # type: ignore[assignment]


class IngestRequest(BaseModel):
    query_id: str = ""
    sensor_values: list[float]


class IngestResponse(BaseModel):
    query_id: str
    normalized_values: list[float]
    raw_values: list[float]
    response_time_ms: float


@app.post("/ingest")
async def ingest(request: IngestRequest) -> IngestResponse:
    """Normalize raw sensor data using z-score normalization."""
    start = time.perf_counter()

    query_id = request.query_id or str(uuid.uuid4())

    normalized = []
    for value, mean, std in zip(request.sensor_values, SENSOR_MEANS, SENSOR_STDS):
        normalized.append(round((value - mean) / std, 6))

    elapsed_ms = (time.perf_counter() - start) * 1000

    if monitor:
        monitor.report_inference(
            query_id=query_id,
            predictions={"normalized_count": len(normalized)},
            confidence=1.0,
            response_time_ms=elapsed_ms,
            labels={"service": "data_ingestion"},
        )

    return IngestResponse(
        query_id=query_id,
        normalized_values=normalized,
        raw_values=request.sensor_values,
        response_time_ms=round(elapsed_ms, 2),
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "data_ingestion"}
