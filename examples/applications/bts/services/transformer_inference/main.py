"""Transformer inference service: simulates Transformer-based time-series prediction."""
from __future__ import annotations

import logging
import random
import time

import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel

logger = logging.getLogger(__name__)

MODEL_NAME = "transformer"
app = FastAPI(title=f"{MODEL_NAME} Inference Service")

# Optional rohe-sdk monitoring
try:
    from rohe.monitoring.sdk import RoheMonitor
    monitor = RoheMonitor.from_env()
except Exception:
    monitor = None  # type: ignore[assignment]


class PredictRequest(BaseModel):
    query_id: str
    data: list[float]


class PredictResponse(BaseModel):
    query_id: str
    predictions: dict[str, float]
    confidence: float
    model: str
    response_time_ms: float


@app.post("/predict")
async def predict(request: PredictRequest) -> PredictResponse:
    """Simulate Transformer prediction on normalized sensor data.

    Uses attention-like weighting where each position attends to all
    others via softmax similarity, producing the highest-quality but
    slowest predictions.
    """
    start = time.perf_counter()

    values = np.array(request.data)
    n = len(values)

    # Simulate Transformer: self-attention-like weighting
    # Compute pairwise similarity as dot products, apply softmax
    similarity = np.exp(values * values.mean())
    attention_weights = similarity / similarity.sum()
    base_prediction = float(np.dot(values, attention_weights))

    # Simulate slightly higher latency for transformer complexity
    time.sleep(random.uniform(0.001, 0.003))

    noise = random.gauss(0, 0.015)
    energy_forecast_kwh = round(base_prediction + noise, 4)
    peak_demand_kw = round(base_prediction * 1.35 + random.gauss(0, 0.008), 4)
    avg_consumption_kwh = round(float(np.mean(values)) + random.gauss(0, 0.01), 4)

    predictions = {
        "energy_forecast_kwh": energy_forecast_kwh,
        "peak_demand_kw": peak_demand_kw,
        "avg_consumption_kwh": avg_consumption_kwh,
    }

    confidence = round(min(0.97, 0.80 + 0.02 * n + random.gauss(0, 0.02)), 4)
    elapsed_ms = (time.perf_counter() - start) * 1000

    if monitor:
        monitor.report_inference(
            query_id=request.query_id,
            predictions=predictions,
            confidence=confidence,
            response_time_ms=elapsed_ms,
            labels={"model": MODEL_NAME},
        )

    return PredictResponse(
        query_id=request.query_id,
        predictions=predictions,
        confidence=round(confidence, 4),
        model=MODEL_NAME,
        response_time_ms=round(elapsed_ms, 2),
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "model": MODEL_NAME}
