"""Gateway service: receives image uploads and forwards to inference services."""
from __future__ import annotations

import logging
import os
import uuid

import httpx
from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(title="Object Classification Gateway")

INFERENCE_SERVICES = os.environ.get(
    "INFERENCE_SERVICES",
    "http://localhost:8001,http://localhost:8002,http://localhost:8003,http://localhost:8004",
).split(",")

AGGREGATOR_URL = os.environ.get("AGGREGATOR_URL", "http://localhost:8005/aggregate")


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


@app.post("/classify")
async def classify_image(image: UploadFile) -> GatewayResponse:
    """Receive image upload, fan out to all inference services, aggregate results."""
    query_id = str(uuid.uuid4())
    image_bytes = await image.read()

    results: list[InferenceResponse] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for service_url in INFERENCE_SERVICES:
            try:
                response = await client.post(
                    f"{service_url.strip()}/predict",
                    files={"image": ("image.jpg", image_bytes, "image/jpeg")},
                    data={"query_id": query_id},
                )
                if response.status_code == 200:
                    results.append(InferenceResponse(**response.json()))
            except Exception:
                logger.warning(f"Inference service {service_url} unavailable")

    if not results:
        raise HTTPException(status_code=503, detail="No inference services available")

    # Simple averaging aggregation
    all_classes: set[str] = set()
    for r in results:
        all_classes.update(r.predictions.keys())

    ensemble: dict[str, float] = {}
    for cls in all_classes:
        values = [r.predictions.get(cls, 0.0) for r in results]
        ensemble[cls] = sum(values) / len(values)

    return GatewayResponse(
        query_id=query_id,
        ensemble_result=dict(sorted(ensemble.items(), key=lambda x: x[1], reverse=True)),
        individual_results=results,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "gateway"}
