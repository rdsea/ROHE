"""Control plane service for multi-modal activity recognition.

Receives inference queries, dispatches to appropriate modality services,
and aggregates results across video and time-series models.
"""
from __future__ import annotations

import logging
import os
import time
import uuid

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(title="Smart Building Control Plane")

VIDEO_SERVICES = os.environ.get(
    "VIDEO_SERVICES",
    "http://localhost:8001,http://localhost:8002,http://localhost:8003,http://localhost:8004",
).split(",")

TIMESERIES_SERVICES = os.environ.get(
    "TIMESERIES_SERVICES",
    "http://localhost:8005,http://localhost:8006,http://localhost:8007,http://localhost:8008",
).split(",")

AGGREGATOR_URL = os.environ.get("AGGREGATOR_URL", "http://localhost:8010/aggregate")

try:
    from rohe.monitoring.sdk import RoheMonitor
    monitor = RoheMonitor.from_env()
except Exception:
    monitor = None  # type: ignore[assignment]


class InferRequest(BaseModel):
    query_id: str | None = None
    modalities: list[str] = ["video", "timeseries"]
    time_constraint_ms: int = 500
    video_data: bytes | None = None
    timeseries_data: list[float] | None = None


class InferenceResult(BaseModel):
    query_id: str
    predictions: dict[str, float]
    confidence: float
    model: str
    response_time_ms: float
    modality: str


class InferResponse(BaseModel):
    query_id: str
    ensemble_result: dict[str, float]
    individual_results: list[InferenceResult]
    modalities_used: list[str]
    total_response_time_ms: float


@app.post("/infer")
async def infer(request: InferRequest) -> InferResponse:
    """Dispatch multi-modal inference and aggregate results."""
    start = time.perf_counter()
    query_id = request.query_id or str(uuid.uuid4())

    results: list[InferenceResult] = []
    modalities_used: list[str] = []
    timeout = request.time_constraint_ms / 1000.0

    async with httpx.AsyncClient(timeout=max(timeout, 5.0)) as client:
        if "video" in request.modalities:
            modalities_used.append("video")
            dummy_image = request.video_data or b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
            for service_url in VIDEO_SERVICES:
                try:
                    response = await client.post(
                        f"{service_url.strip()}/predict",
                        files={"image": ("frame.jpg", dummy_image, "image/jpeg")},
                        data={"query_id": query_id},
                    )
                    if response.status_code == 200:
                        results.append(InferenceResult(**response.json()))
                except Exception:
                    logger.warning(f"Video service {service_url} unavailable")

        if "timeseries" in request.modalities:
            modalities_used.append("timeseries")
            sensor_data = request.timeseries_data or [0.0] * 128
            for service_url in TIMESERIES_SERVICES:
                try:
                    response = await client.post(
                        f"{service_url.strip()}/predict",
                        json={"query_id": query_id, "data": sensor_data},
                    )
                    if response.status_code == 200:
                        results.append(InferenceResult(**response.json()))
                except Exception:
                    logger.warning(f"Timeseries service {service_url} unavailable")

    if not results:
        raise HTTPException(status_code=503, detail="No inference services available")

    all_classes: set[str] = set()
    for r in results:
        all_classes.update(r.predictions.keys())

    ensemble: dict[str, float] = {}
    for cls in all_classes:
        values = [r.predictions.get(cls, 0.0) for r in results]
        ensemble[cls] = round(sum(values) / len(values), 4)

    sorted_ensemble = dict(sorted(ensemble.items(), key=lambda x: x[1], reverse=True))
    elapsed_ms = (time.perf_counter() - start) * 1000

    if monitor:
        monitor.report_request(
            query_id=query_id,
            pipeline_id="smart-building",
            response_time_ms=elapsed_ms,
            prediction=sorted_ensemble,
        )

    return InferResponse(
        query_id=query_id,
        ensemble_result=sorted_ensemble,
        individual_results=results,
        modalities_used=modalities_used,
        total_response_time_ms=round(elapsed_ms, 2),
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "control-plane"}
