"""Reusable inference service factory.

All inference services across all apps use this to create their FastAPI app.
The service is identical regardless of model type (real or simulated) --
the model is loaded via ModelLoader at startup from a YAML config.

Supports two request modes:
  1. POST /predict (PredictRequest) -- inline data, for direct testing
  2. POST /inference (InferenceTaskRequest) -- data reference, fetches from DataHub
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from .schemas import InferenceResponse, InferenceTaskRequest, PredictRequest

logger = logging.getLogger(__name__)


def create_inference_app(
    service_name: str,
    modality: str | None = None,
) -> FastAPI:
    """Create a standard inference service FastAPI app.

    The model is loaded at startup from MODEL_CONFIG env var.
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

    # -- Orchestrator-driven endpoint (data reference) --

    @app.post("/inference", response_model=InferenceResponse)
    async def inference_from_datahub(request: InferenceTaskRequest) -> InferenceResponse:
        """Run inference on data fetched from DataHub.

        Called by the orchestrator with a data reference. The service fetches
        its input from DataHub, runs the model, and returns the result.
        """
        data = await _fetch_from_datahub(
            data_hub_url=request.data_hub_url,
            query_id=request.query_id,
            data_key=request.data_key,
        )
        return _run_inference(app, request.query_id, data)

    # -- Direct endpoints (inline data, for testing and backward compat) --

    @app.post("/predict", response_model=InferenceResponse)
    async def predict_json(request: PredictRequest) -> InferenceResponse:
        """Predict from inline JSON data."""
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


async def _fetch_from_datahub(
    data_hub_url: str,
    query_id: str,
    data_key: str,
) -> Any:
    """Fetch data from DataHub by query_id and data_key."""
    url = f"{data_hub_url}/fetch/{query_id}/{data_key}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"DataHub fetch failed: {url} returned {resp.status_code}",
        )
    return resp.json().get("data")


def _run_inference(app: FastAPI, query_id: str, input_data: Any) -> InferenceResponse:
    """Run inference through the loaded model and report metrics."""
    if app.state.model is None:
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
