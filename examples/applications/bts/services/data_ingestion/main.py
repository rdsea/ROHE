"""BTS data ingestion and normalization service."""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from pydantic import BaseModel

logger = logging.getLogger(__name__)
app = FastAPI(title="BTS Data Ingestion")


class IngestRequest(BaseModel):
    query_id: str
    sensor_values: list[float]


class IngestResponse(BaseModel):
    query_id: str
    normalized_values: list[float]


preprocessor = None


@app.on_event("startup")
async def startup() -> None:
    global preprocessor
    config_path = os.environ.get("PREPROCESSOR_CONFIG", "/config/preprocessor.yaml")
    try:
        from rohe.common.preprocessor_loader import PreprocessorLoader
        preprocessor = PreprocessorLoader.load(config_path)
        logger.info(f"Loaded preprocessor: {preprocessor.get_preprocessor_info()}")
    except Exception:
        logger.warning("No preprocessor config, using passthrough")


@app.post("/ingest")
async def ingest(request: IngestRequest) -> IngestResponse:
    if preprocessor:
        normalized = preprocessor.preprocess(request.sensor_values)
    else:
        normalized = request.sensor_values
    return IngestResponse(query_id=request.query_id, normalized_values=normalized)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "data-ingestion"}
