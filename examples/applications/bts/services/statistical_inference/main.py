"""Statistical inference service: simulates ARIMA/statistical time-series prediction."""
from __future__ import annotations

import logging
import random
import time

import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel

logger = logging.getLogger(__name__)

MODEL_NAME = "statistical"
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
    """Simulate ARIMA/statistical prediction on normalized sensor data.

    Uses simple moving average and linear trend extrapolation.
    Fastest model with lowest computational cost but moderate accuracy.
    """
    start = time.perf_counter()

    values = np.array(request.data)
    n = len(values)

    # Simulate ARIMA: simple moving average + linear trend
    mean_val = float(np.mean(values))
    if n >= 2:
        trend = float(values[-1] - values[0]) / n
    else:
        trend = 0.0
    base_prediction = mean_val + trend

    noise = random.gauss(0, 0.035)
    energy_forecast_kwh = round(base_prediction + noise, 4)
    peak_demand_kw = round(base_prediction * 1.2 + random.gauss(0, 0.02), 4)
    avg_consumption_kwh = round(mean_val + random.gauss(0, 0.025), 4)

    predictions = {
        "energy_forecast_kwh": energy_forecast_kwh,
        "peak_demand_kw": peak_demand_kw,
        "avg_consumption_kwh": avg_consumption_kwh,
    }

    confidence = round(min(0.88, 0.65 + 0.02 * n + random.gauss(0, 0.04)), 4)
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
