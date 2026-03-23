"""Reusable preprocessor service factory.

Preprocessors are called by the orchestrator with data references.
They fetch raw data from DataHub, apply preprocessing, and store
the result back to DataHub under a new data_key.

Supports two request modes:
  1. POST /preprocess (PreprocessTaskRequest) -- data reference, orchestrator-driven
  2. POST /preprocess/direct -- inline data, for direct testing
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException

from .schemas import PreprocessTaskRequest, PreprocessTaskResponse

logger = logging.getLogger(__name__)


def create_preprocessor_app(
    service_name: str,
    preprocess_fn: Any = None,
) -> FastAPI:
    """Create a standard preprocessor FastAPI app.

    preprocess_fn: optional callable(data) -> processed_data.
                   If None, loads via PreprocessorLoader from config.
    """
    app = FastAPI(title=f"{service_name} Preprocessor")
    app.state.preprocessor = None
    app.state.service_name = service_name
    app.state.preprocess_fn = preprocess_fn

    @app.on_event("startup")
    async def startup() -> None:
        if app.state.preprocess_fn is not None:
            logger.info(f"Using custom preprocess function for {service_name}")
            return

        config_path = os.environ.get("PREPROCESSOR_CONFIG", "/config/preprocessor.yaml")
        try:
            from rohe.common.preprocessor_loader import PreprocessorLoader
            app.state.preprocessor = PreprocessorLoader.load(config_path)
            logger.info(f"Loaded preprocessor: {app.state.preprocessor.get_preprocessor_info()}")
        except Exception:
            logger.warning(f"Could not load preprocessor from {config_path}, using passthrough")

    # -- Orchestrator-driven endpoint (data reference) --

    @app.post("/preprocess", response_model=PreprocessTaskResponse)
    async def preprocess_from_datahub(
        request: PreprocessTaskRequest,
    ) -> PreprocessTaskResponse:
        """Fetch raw data from DataHub, preprocess, store result back."""
        # Fetch raw data -- from stream buffer or query-scoped storage
        if request.window_length > 0:
            raw_data = await _fetch_stream_window(
                data_hub_url=request.data_hub_url,
                modality=request.data_key,
                window_length=request.window_length,
            )
        else:
            raw_data = await _fetch_from_datahub(
                data_hub_url=request.data_hub_url,
                query_id=request.query_id,
                data_key=request.data_key,
            )

        # Preprocess
        processed_data = _apply_preprocessing(app, raw_data)

        # Store result back to DataHub
        await _store_to_datahub(
            data_hub_url=request.data_hub_url,
            query_id=request.query_id,
            data_key=request.output_data_key,
            data=processed_data,
        )

        return PreprocessTaskResponse(
            query_id=request.query_id,
            output_data_key=request.output_data_key,
            status="ok",
        )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        has_preprocessor = (
            app.state.preprocessor is not None or app.state.preprocess_fn is not None
        )
        return {
            "status": "ok" if has_preprocessor else "passthrough",
            "service": service_name,
        }

    return app


def _apply_preprocessing(app: FastAPI, data: Any) -> Any:
    """Apply preprocessing using the loaded preprocessor or custom function."""
    if app.state.preprocess_fn is not None:
        return app.state.preprocess_fn(data)
    if app.state.preprocessor is not None:
        return app.state.preprocessor.preprocess(data)
    # Passthrough if no preprocessor configured
    return data


async def _fetch_stream_window(
    data_hub_url: str,
    modality: str,
    window_length: int,
) -> Any:
    """Fetch a window of recent samples from DataHub's stream buffer."""
    url = f"{data_hub_url}/stream/{modality}/window?length={window_length}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"DataHub stream window fetch failed: {url} returned {resp.status_code}",
        )
    return resp.json().get("samples", [])


async def _fetch_from_datahub(
    data_hub_url: str,
    query_id: str,
    data_key: str,
) -> Any:
    """Fetch data from DataHub."""
    url = f"{data_hub_url}/fetch/{query_id}/{data_key}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"DataHub fetch failed: {url} returned {resp.status_code}",
        )
    return resp.json().get("data")


async def _store_to_datahub(
    data_hub_url: str,
    query_id: str,
    data_key: str,
    data: Any,
) -> None:
    """Store processed data back to DataHub."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{data_hub_url}/store",
            json={
                "query_id": query_id,
                "data_key": data_key,
                "data": data,
                "metadata": {"source": "preprocessor"},
            },
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"DataHub store failed: returned {resp.status_code}",
        )
