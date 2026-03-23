"""Reusable gateway service factory.

The gateway is dumb -- it does three things:
  1. Store raw data in DataHub
  2. Forward a control message to the orchestrator
  3. Return the orchestrator's response to the client

NO orchestration logic, NO fan-out, NO aggregation.
"""
import logging
import os
import uuid
from typing import Any, Optional

import httpx
from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel

from .schemas import GatewayResponse, OrchestrateRequest, OrchestrateResponse

logger = logging.getLogger(__name__)


class GatewayPredictRequest(BaseModel):
    """Request body for the gateway predict endpoint."""

    query_id: str = ""
    data: Any = None  # noqa: ANN401 -- opaque, passed to DataHub (None for streaming)
    modalities: Optional[list[str]] = None
    window_length: int = 0  # >0 = extract from DataHub stream buffer, 0 = use inline data
    time_constraint_ms: float = 500.0


def create_gateway_app(
    service_name: str,
    input_mode: str = "json",
) -> FastAPI:
    """Create a standard gateway FastAPI app.

    input_mode: "json" for timeseries/tabular, "image" for image upload
    """
    app = FastAPI(title=f"{service_name} Gateway")
    app.state.orchestrator_url = ""
    app.state.data_hub_url = ""
    app.state.pipeline_id = ""
    app.state.timeout = 30.0

    @app.on_event("startup")
    async def startup() -> None:
        app.state.orchestrator_url = os.environ.get(
            "ORCHESTRATOR_URL", "http://orchestrator:9000"
        )
        app.state.data_hub_url = os.environ.get(
            "DATA_HUB_URL", "http://data-hub:8000"
        )
        app.state.pipeline_id = os.environ.get("PIPELINE_ID", service_name)
        app.state.timeout = float(os.environ.get("REQUEST_TIMEOUT_SECONDS", "30"))
        logger.info(
            f"Gateway configured: orchestrator={app.state.orchestrator_url}, "
            f"datahub={app.state.data_hub_url}, pipeline={app.state.pipeline_id}"
        )

    if input_mode == "json":
        @app.post("/predict", response_model=GatewayResponse)
        async def predict_json(request: GatewayPredictRequest) -> GatewayResponse:
            query_id = request.query_id or str(uuid.uuid4())
            return await _handle_request(
                app, query_id, request.data,
                modalities=request.modalities or [app.state.pipeline_id],
                window_length=request.window_length,
                time_constraint_ms=request.time_constraint_ms,
            )
    else:
        @app.post("/predict", response_model=GatewayResponse)
        async def predict_image(
            image: UploadFile = File(...),
            query_id: str = Form(""),
            time_constraint_ms: float = Form(500.0),
        ) -> GatewayResponse:
            if not query_id:
                query_id = str(uuid.uuid4())
            image_bytes = await image.read()
            return await _handle_request(
                app, query_id, image_bytes,
                modalities=["image"],
                time_constraint_ms=time_constraint_ms,
            )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": service_name,
            "orchestrator_url": app.state.orchestrator_url,
            "data_hub_url": app.state.data_hub_url,
        }

    return app


async def _handle_request(
    app: FastAPI,
    query_id: str,
    data: Any,  # noqa: ANN401 -- opaque
    modalities: list[str],
    window_length: int = 0,
    time_constraint_ms: float = 500.0,
) -> GatewayResponse:
    """Store data in DataHub (if provided), forward to orchestrator, return response."""
    async with httpx.AsyncClient(timeout=app.state.timeout) as client:
        # Step 1: Store raw data in DataHub (skip if streaming -- data already in stream buffer)
        if data is not None and window_length == 0:
            for modality in modalities:
                try:
                    await client.post(
                        f"{app.state.data_hub_url}/store",
                        json={
                            "query_id": query_id,
                            "data_key": modality,
                            "data": data,
                            "metadata": {"source": "gateway"},
                        },
                    )
                except (httpx.TimeoutException, httpx.ConnectError):
                    logger.warning(f"DataHub unavailable, could not store {modality}")

        # Step 2: Forward control message to orchestrator
        orchestrate_request = OrchestrateRequest(
            query_id=query_id,
            pipeline_id=app.state.pipeline_id,
            modalities=modalities,
            window_length=window_length,
            time_constraint_ms=time_constraint_ms,
            data_hub_url=app.state.data_hub_url,
        )

        try:
            resp = await client.post(
                f"{app.state.orchestrator_url}/orchestrate",
                json=orchestrate_request.model_dump(),
            )
            if resp.status_code == 200:
                result = OrchestrateResponse(**resp.json())
                return GatewayResponse(
                    query_id=result.query_id,
                    ensemble_result=result.ensemble_result,
                    individual_results=result.individual_results,
                    model_count=result.model_count,
                )
        except (httpx.TimeoutException, httpx.ConnectError):
            logger.warning("Orchestrator unavailable")

    # Fallback: orchestrator unreachable
    return GatewayResponse(
        query_id=query_id,
        ensemble_result={},
        individual_results=[],
        model_count=0,
    )
