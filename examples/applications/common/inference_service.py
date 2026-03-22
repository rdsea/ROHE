"""Reusable inference service factory.

All inference services across all apps use this to create their FastAPI app.
The service is identical regardless of model type (real or simulated) --
the model is loaded via ModelLoader at startup from a YAML config.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile

from .schemas import InferenceResponse, PredictRequest

logger = logging.getLogger(__name__)


def create_inference_app(
    service_name: str,
    modality: str | None = None,
) -> FastAPI:
    """Create a standard inference service FastAPI app.

    The model is loaded at startup from MODEL_CONFIG env var.
    Supports both JSON (PredictRequest) and file upload (UploadFile) endpoints.
    """
    app = FastAPI(title=f"{service_name} Inference Service")
    app.state.model = None
    app.state.service_name = service_name
    app.state.modality = modality
    app.state.monitor = None

    @app.on_event("startup")
    async def startup() -> None:
        config_path = os.environ.get("MODEL_CONFIG", "/config/model.yaml")
        try:
            from rohe.common.model_loader import ModelLoader
            app.state.model = ModelLoader.load(config_path)
            logger.info(f"Loaded model: {app.state.model.get_model_info()}")
        except Exception:
            logger.warning(f"Could not load model from {config_path}, service will return 503")

        try:
            from rohe.monitoring.sdk import RoheMonitor
            app.state.monitor = RoheMonitor.from_env()
        except Exception:
            logger.debug("rohe-sdk not available, monitoring disabled")

    @app.post("/predict", response_model=InferenceResponse)
    async def predict_json(request: PredictRequest) -> InferenceResponse:
        """Predict from JSON request (timeseries, tabular data)."""
        return _run_inference(app, request.query_id, request.data)

    @app.post("/predict/image", response_model=InferenceResponse)
    async def predict_image(
        image: UploadFile = File(...),
        query_id: str = Form("unknown"),
    ) -> InferenceResponse:
        """Predict from image upload."""
        image_bytes = await image.read()
        return _run_inference(app, query_id, image_bytes)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        model_info = app.state.model.get_model_info() if app.state.model else {}
        return {
            "status": "ok" if app.state.model else "no_model",
            "service": service_name,
            **model_info,
        }

    return app


def _run_inference(app: FastAPI, query_id: str, input_data: Any) -> InferenceResponse:
    """Run inference through the loaded model and report metrics."""
    if app.state.model is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Model not loaded")

    start = time.perf_counter()
    result = app.state.model.predict(input_data)
    elapsed_ms = (time.perf_counter() - start) * 1000

    model_info = app.state.model.get_model_info()

    if app.state.monitor:
        app.state.monitor.report_inference(
            query_id=query_id,
            predictions=result.predictions,
            confidence=result.confidence,
            response_time_ms=elapsed_ms,
            labels={"model": model_info.get("name", "unknown"), "service": app.state.service_name},
        )

    return InferenceResponse(
        query_id=query_id,
        predictions=result.predictions,
        confidence=round(result.confidence, 4),
        model=model_info.get("name", app.state.service_name),
        response_time_ms=round(elapsed_ms, 2),
        modality=app.state.modality,
    )
