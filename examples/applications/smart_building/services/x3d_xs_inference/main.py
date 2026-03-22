"""X3D Extra Small inference service for activity recognition.

Fast video model with lower accuracy, suitable for real-time applications.
Predictions are simulated with random values.
"""
from __future__ import annotations

import logging
import random
import time

from fastapi import FastAPI, File, Form, UploadFile

logger = logging.getLogger(__name__)

MODEL_NAME = "x3d_xs"
MODALITY = "video"
ACTIVITY_CLASSES = [
    "walking", "sitting", "standing", "running",
    "cooking", "cleaning", "eating", "reading",
]

# Accuracy profile: lower accuracy, faster inference
BASE_CONFIDENCE_RANGE = (0.35, 0.70)
SIMULATED_LATENCY_RANGE_MS = (15, 40)

app = FastAPI(title=f"{MODEL_NAME} Inference Service")

try:
    from rohe.monitoring.sdk import RoheMonitor
    monitor = RoheMonitor.from_env()
except Exception:
    monitor = None  # type: ignore[assignment]


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
async def predict(
    image: UploadFile = File(...),
    query_id: str = Form("unknown"),
) -> dict:
    """Run X3D-XS inference on uploaded video frame."""
    start = time.perf_counter()

    await image.read()

    latency_ms = random.uniform(*SIMULATED_LATENCY_RANGE_MS)
    time.sleep(latency_ms / 1000.0)

    predictions, confidence = _simulate_predictions()
    elapsed_ms = (time.perf_counter() - start) * 1000

    if monitor:
        monitor.report_inference(
            query_id=query_id,
            predictions=predictions,
            confidence=confidence,
            response_time_ms=elapsed_ms,
            labels={"model": MODEL_NAME, "modality": MODALITY},
        )

    return {
        "query_id": query_id,
        "predictions": predictions,
        "confidence": round(confidence, 4),
        "model": MODEL_NAME,
        "response_time_ms": round(elapsed_ms, 2),
        "modality": MODALITY,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "model": MODEL_NAME, "modality": MODALITY}
