"""Gateway service: receives sensor data and forwards to inference services."""
from __future__ import annotations

import logging
import os
import uuid

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(title="BTS Gateway")

DATA_INGESTION_URL = os.environ.get(
    "DATA_INGESTION_URL",
    "http://localhost:8010",
)

INFERENCE_SERVICES = os.environ.get(
    "INFERENCE_SERVICES",
    "http://localhost:8001,http://localhost:8002,http://localhost:8003,http://localhost:8004",
).split(",")

AGGREGATOR_URL = os.environ.get("AGGREGATOR_URL", "http://localhost:8005/aggregate")


class SensorRequest(BaseModel):
    sensor_values: list[float]


class InferenceResponse(BaseModel):
    query_id: str
    predictions: dict[str, float]
    confidence: float
    model: str
    response_time_ms: float


class GatewayResponse(BaseModel):
    query_id: str
    ensemble_result: dict[str, float]
    individual_results: list[InferenceResponse]


@app.post("/forecast")
async def forecast(request: SensorRequest) -> GatewayResponse:
    """Receive sensor data, normalize via ingestion service, fan out to all inference services, aggregate."""
    query_id = str(uuid.uuid4())

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Normalize data via ingestion service
        try:
            ingest_response = await client.post(
                f"{DATA_INGESTION_URL.strip()}/ingest",
                json={"query_id": query_id, "sensor_values": request.sensor_values},
            )
            if ingest_response.status_code != 200:
                raise HTTPException(status_code=502, detail="Data ingestion service error")
            normalized_data = ingest_response.json()["normalized_values"]
        except httpx.HTTPError as exc:
            logger.warning(f"Data ingestion service unavailable: {exc}")
            raise HTTPException(status_code=503, detail="Data ingestion service unavailable")

        # Step 2: Fan out to all inference services
        results: list[InferenceResponse] = []
        for service_url in INFERENCE_SERVICES:
            try:
                response = await client.post(
                    f"{service_url.strip()}/predict",
                    json={"query_id": query_id, "data": normalized_data},
                )
                if response.status_code == 200:
                    results.append(InferenceResponse(**response.json()))
            except Exception:
                logger.warning(f"Inference service {service_url} unavailable")

    if not results:
        raise HTTPException(status_code=503, detail="No inference services available")

    # Step 3: Simple averaging aggregation (inline, same as object classification)
    all_keys: set[str] = set()
    for r in results:
        all_keys.update(r.predictions.keys())

    ensemble: dict[str, float] = {}
    for key in all_keys:
        values = [r.predictions.get(key, 0.0) for r in results]
        ensemble[key] = round(sum(values) / len(values), 4)

    return GatewayResponse(
        query_id=query_id,
        ensemble_result=dict(sorted(ensemble.items())),
        individual_results=results,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "gateway"}
