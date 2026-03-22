"""YOLOv8 Nano inference service (simulated)."""
from __future__ import annotations

import logging
import random
import time

from fastapi import FastAPI, File, Form, UploadFile

logger = logging.getLogger(__name__)

MODEL_NAME = "yolov8n"
app = FastAPI(title=f"{MODEL_NAME} Inference Service")

DETECTION_CLASSES = ["car", "person", "truck", "bicycle", "bus", "motorcycle", "dog", "cat"]

# YOLOv8 Nano: fastest, lower confidence
BASE_CONFIDENCE = 0.55
CONFIDENCE_SPREAD = 0.25
LATENCY_BASE_MS = 8.0
LATENCY_JITTER_MS = 4.0
MIN_DETECTIONS = 2
MAX_DETECTIONS = 5

# Optional rohe-sdk monitoring
try:
    from rohe.monitoring.sdk import RoheMonitor
    monitor = RoheMonitor.from_env()
except Exception:
    monitor = None  # type: ignore[assignment]


@app.post("/predict")
async def predict(
    image: UploadFile = File(...),
    query_id: str = Form("unknown"),
) -> dict:
    """Run simulated YOLOv8 Nano inference on uploaded image."""
    start = time.perf_counter()

    await image.read()

    simulated_latency = LATENCY_BASE_MS + random.uniform(-LATENCY_JITTER_MS, LATENCY_JITTER_MS)
    time.sleep(max(simulated_latency / 1000.0, 0.001))

    num_detections = random.randint(MIN_DETECTIONS, MAX_DETECTIONS)
    detected_classes = random.sample(DETECTION_CLASSES, min(num_detections, len(DETECTION_CLASSES)))

    predictions: dict[str, float] = {}
    for cls in detected_classes:
        conf = BASE_CONFIDENCE + random.uniform(-CONFIDENCE_SPREAD, CONFIDENCE_SPREAD)
        predictions[cls] = round(max(0.05, min(0.99, conf)), 4)

    sorted_predictions = dict(sorted(predictions.items(), key=lambda x: x[1], reverse=True))
    confidence = max(sorted_predictions.values()) if sorted_predictions else 0.0
    elapsed_ms = (time.perf_counter() - start) * 1000

    if monitor:
        monitor.report_inference(
            query_id=query_id,
            predictions=sorted_predictions,
            confidence=confidence,
            response_time_ms=elapsed_ms,
            labels={"model": MODEL_NAME},
        )

    return {
        "query_id": query_id,
        "predictions": sorted_predictions,
        "confidence": round(confidence, 4),
        "model": MODEL_NAME,
        "response_time_ms": round(elapsed_ms, 2),
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "model": MODEL_NAME}
