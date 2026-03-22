"""Preprocessor service: applies image enhancement (sharpening) before inference."""
from __future__ import annotations

import io
import logging

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import Response
from PIL import Image, ImageFilter

logger = logging.getLogger(__name__)

app = FastAPI(title="CCTVS Preprocessor Service")

SHARPEN_PASSES = 1


@app.post("/preprocess")
async def preprocess(image: UploadFile = File(...)) -> Response:
    """Apply sharpening filter to uploaded image and return processed bytes."""
    image_bytes = await image.read()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    for _ in range(SHARPEN_PASSES):
        img = img.filter(ImageFilter.SHARPEN)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    processed_bytes = buf.getvalue()

    logger.debug(f"Preprocessed image: {len(image_bytes)} -> {len(processed_bytes)} bytes")

    return Response(content=processed_bytes, media_type="image/jpeg")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "preprocessor"}
