"""CCTVS image preprocessor service."""
from __future__ import annotations

import io
import logging
import os

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import Response

logger = logging.getLogger(__name__)
app = FastAPI(title="CCTVS Preprocessor")

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


@app.post("/preprocess")
async def preprocess(image: UploadFile = File(...)) -> Response:
    image_bytes = await image.read()
    if preprocessor:
        processed = preprocessor.preprocess(image_bytes)
    else:
        processed = image_bytes
    return Response(content=processed, media_type="image/jpeg")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "preprocessor"}
