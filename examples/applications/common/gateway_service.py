"""Reusable gateway service factory.

Gateways fan out requests to inference services and delegate
aggregation to the aggregator service (not inline).
"""
from __future__ import annotations

import logging
import os
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, File, Form, UploadFile

from .schemas import AggregateRequest, GatewayResponse, InferenceResponse

logger = logging.getLogger(__name__)


def create_gateway_app(
    service_name: str,
    input_mode: str = "json",
) -> FastAPI:
    """Create a standard gateway FastAPI app.

    input_mode: "json" for timeseries/tabular, "image" for image upload
    """
    app = FastAPI(title=f"{service_name} Gateway")
    app.state.inference_services: list[str] = []
    app.state.aggregator_url: str = ""
    app.state.timeout: float = 30.0
    app.state.monitor = None

    @app.on_event("startup")
    async def startup() -> None:
        services_str = os.environ.get("INFERENCE_SERVICES", "")
        app.state.inference_services = [s.strip() for s in services_str.split(",") if s.strip()]
        app.state.aggregator_url = os.environ.get("AGGREGATOR_URL", "http://localhost:8005/aggregate")
        app.state.timeout = float(os.environ.get("REQUEST_TIMEOUT_SECONDS", "30"))
        logger.info(f"Gateway configured with {len(app.state.inference_services)} inference services")

        try:
            from rohe.monitoring.sdk import RoheMonitor
            app.state.monitor = RoheMonitor.from_env()
        except Exception:
            pass

    if input_mode == "json":
        @app.post("/predict", response_model=GatewayResponse)
        async def predict_json(query_id: str = "", data: Any = None) -> GatewayResponse:
            if not query_id:
                query_id = str(uuid.uuid4())
            return await _fan_out_json(app, query_id, data)
    else:
        @app.post("/predict", response_model=GatewayResponse)
        async def predict_image(
            image: UploadFile = File(...),
            query_id: str = Form(""),
        ) -> GatewayResponse:
            if not query_id:
                query_id = str(uuid.uuid4())
            image_bytes = await image.read()
            return await _fan_out_image(app, query_id, image_bytes)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": service_name,
            "inference_services": len(app.state.inference_services),
        }

    return app


async def _fan_out_json(app: FastAPI, query_id: str, data: Any) -> GatewayResponse:
    """Fan out JSON request to all inference services."""
    results: list[InferenceResponse] = []
    async with httpx.AsyncClient(timeout=app.state.timeout) as client:
        for url in app.state.inference_services:
            try:
                resp = await client.post(
                    f"{url}/predict",
                    json={"query_id": query_id, "data": data},
                )
                if resp.status_code == 200:
                    results.append(InferenceResponse(**resp.json()))
            except (httpx.TimeoutException, httpx.ConnectError):
                logger.warning(f"Service {url} unavailable")

    return await _aggregate_and_respond(app, query_id, results)


async def _fan_out_image(app: FastAPI, query_id: str, image_bytes: bytes) -> GatewayResponse:
    """Fan out image to all inference services."""
    results: list[InferenceResponse] = []
    async with httpx.AsyncClient(timeout=app.state.timeout) as client:
        for url in app.state.inference_services:
            try:
                resp = await client.post(
                    f"{url}/predict/image",
                    files={"image": ("image.jpg", image_bytes, "image/jpeg")},
                    data={"query_id": query_id},
                )
                if resp.status_code == 200:
                    results.append(InferenceResponse(**resp.json()))
            except (httpx.TimeoutException, httpx.ConnectError):
                logger.warning(f"Service {url} unavailable")

    return await _aggregate_and_respond(app, query_id, results)


async def _aggregate_and_respond(
    app: FastAPI,
    query_id: str,
    results: list[InferenceResponse],
) -> GatewayResponse:
    """Call aggregator service and build gateway response."""
    if not results:
        return GatewayResponse(
            query_id=query_id, ensemble_result={}, individual_results=[], model_count=0,
        )

    # Call aggregator service
    strategy = os.environ.get("AGGREGATION_STRATEGY", "confidence_avg")
    try:
        agg_request = AggregateRequest(
            query_id=query_id,
            results=results,
            strategy=strategy,
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                app.state.aggregator_url,
                json=agg_request.model_dump(),
            )
            if resp.status_code == 200:
                ensemble = resp.json().get("ensemble_predictions", {})
            else:
                ensemble = _fallback_aggregate(results)
    except (httpx.TimeoutException, httpx.ConnectError):
        logger.warning("Aggregator unavailable, using fallback")
        ensemble = _fallback_aggregate(results)

    return GatewayResponse(
        query_id=query_id,
        ensemble_result=ensemble,
        individual_results=results,
        model_count=len(results),
    )


def _fallback_aggregate(results: list[InferenceResponse]) -> dict[str, float]:
    """Simple averaging fallback when aggregator is unavailable."""
    all_classes: set[str] = set()
    for r in results:
        all_classes.update(r.predictions.keys())
    return {
        cls: round(sum(r.predictions.get(cls, 0.0) for r in results) / len(results), 4)
        for cls in all_classes
    }
