"""GRU inference service: simulates GRU-based time-series prediction."""
from __future__ import annotations

import logging
import random
import time

import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel

logger = logging.getLogger(__name__)

MODEL_NAME = "gru"
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
    """Simulate GRU prediction on normalized sensor data.

    Uses weighted average with linear decay weights to mimic a GRU
    with simpler gating than LSTM.
    """
    start = time.perf_counter()

    values = np.array(request.data)
    n = len(values)

    # Simulate GRU: linear decay weights (simpler than LSTM exponential)
    weights = np.linspace(0.5, 1.0, n)
    weights /= weights.sum()
    base_prediction = float(np.dot(values, weights))

    noise = random.gauss(0, 0.025)
    energy_forecast_kwh = round(base_prediction + noise, 4)
    peak_demand_kw = round(base_prediction * 1.25 + random.gauss(0, 0.015), 4)
    avg_consumption_kwh = round(float(np.mean(values)) + random.gauss(0, 0.02), 4)

    predictions = {
        "energy_forecast_kwh": energy_forecast_kwh,
        "peak_demand_kw": peak_demand_kw,
        "avg_consumption_kwh": avg_consumption_kwh,
    }

    confidence = round(min(0.93, 0.72 + 0.02 * n + random.gauss(0, 0.03)), 4)
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
