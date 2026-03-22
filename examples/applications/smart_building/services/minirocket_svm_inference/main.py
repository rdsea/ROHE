"""MiniRocket + SVM inference service for activity recognition.

Time-series model using MiniRocket features with SVM classifier.
Predictions are simulated with random values.
"""
from __future__ import annotations

import logging
import random
import time

from fastapi import FastAPI
from pydantic import BaseModel

logger = logging.getLogger(__name__)

MODEL_NAME = "minirocket_svm"
MODALITY = "timeseries"
ACTIVITY_CLASSES = [
    "walking", "sitting", "standing", "running",
    "cooking", "cleaning", "eating", "reading",
]

# Accuracy profile: good accuracy for time-series, fast inference
BASE_CONFIDENCE_RANGE = (0.45, 0.80)
SIMULATED_LATENCY_RANGE_MS = (5, 20)

app = FastAPI(title=f"{MODEL_NAME} Inference Service")

try:
    from rohe.monitoring.sdk import RoheMonitor
    monitor = RoheMonitor.from_env()
except Exception:
    monitor = None  # type: ignore[assignment]


class TimeSeriesRequest(BaseModel):
    query_id: str = "unknown"
    data: list[float]


def _simulate_predictions() -> tuple[dict[str, float], float]:
    """Generate simulated activity predictions with model-specific accuracy profile."""
    raw_scores = {cls: random.uniform(0.01, 1.0) for cls in ACTIVITY_CLASSES}
    top_class = random.choice(ACTIVITY_CLASSES)
    raw_scores[top_class] += random.uniform(*BASE_CONFIDENCE_RANGE)

    total = sum(raw_scores.values())
    predictions = {
        cls: round(score / total, 4)
        for cls, score in sorted(raw_scores.items(), key=lambda x: x[1], reverse=True)
    }
    confidence = max(predictions.values())
    return predictions, confidence


@app.post("/predict")
async def predict(request: TimeSeriesRequest) -> dict:
    """Run MiniRocket+SVM inference on time-series sensor data."""
    start = time.perf_counter()

    latency_ms = random.uniform(*SIMULATED_LATENCY_RANGE_MS)
    time.sleep(latency_ms / 1000.0)

    predictions, confidence = _simulate_predictions()
    elapsed_ms = (time.perf_counter() - start) * 1000

    if monitor:
        monitor.report_inference(
            query_id=request.query_id,
            predictions=predictions,
            confidence=confidence,
            response_time_ms=elapsed_ms,
            labels={"model": MODEL_NAME, "modality": MODALITY},
        )

    return {
        "query_id": request.query_id,
        "predictions": predictions,
        "confidence": round(confidence, 4),
        "model": MODEL_NAME,
        "response_time_ms": round(elapsed_ms, 2),
        "modality": MODALITY,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "model": MODEL_NAME, "modality": MODALITY}
