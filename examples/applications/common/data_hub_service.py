"""Reusable DataHub service factory.

The DataHub is the data plane for the orchestrated pipeline. It provides
two storage modes:

1. **Query-scoped storage** (existing): keyed by (query_id, data_key).
   Used for per-request data and preprocessed results.

2. **Stream buffers** (new): rolling buffers per modality.
   Data streamers push samples continuously. Preprocessors extract
   windows of N recent samples for inference.
"""
from __future__ import annotations

import logging
import time
from collections import deque
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


# -- Query-scoped models --

class StoreRequest(BaseModel):
    """Store data for a specific query."""

    query_id: str
    data_key: str
    data: Any
    metadata: dict[str, str] = {}


class StoreResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    query_id: str
    data_key: str
    stored_at: float


class FetchResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    query_id: str
    data_key: str
    data: Any
    metadata: dict[str, str] = {}
    stored_at: float


class FetchAllResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    query_id: str
    entries: dict[str, Any]


# -- Stream buffer models --

class StreamPushRequest(BaseModel):
    """Push a sample to a modality's rolling buffer."""

    modality: str
    data: Any  # single sample (list[float] for sensors, str for frame ref, etc.)
    timestamp: float = 0.0  # 0 = auto-assign


class StreamPushResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    modality: str
    buffer_size: int
    timestamp: float


class StreamWindowResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    modality: str
    window_length: int
    samples: list[Any]
    timestamps: list[float]


def create_data_hub_app(
    max_cache_size: int = 10_000,
    max_stream_buffer_size: int = 10_000,
) -> FastAPI:
    """Create a DataHub FastAPI application."""

    app = FastAPI(title="DataHub")

    # Query-scoped cache: {query_id: {data_key: {data, metadata, stored_at}}}
    cache: dict[str, dict[str, dict[str, Any]]] = {}

    # Stream buffers: {modality: deque of {data, timestamp}}
    stream_buffers: dict[str, deque] = {}

    # ---- Query-scoped endpoints ----

    @app.post("/store", response_model=StoreResponse)
    async def store(request: StoreRequest) -> StoreResponse:
        """Store data for a given query_id and data_key."""
        if len(cache) >= max_cache_size:
            oldest_key = next(iter(cache))
            del cache[oldest_key]
            logger.warning(f"Cache full, evicted query_id={oldest_key}")

        stored_at = time.time()
        if request.query_id not in cache:
            cache[request.query_id] = {}

        cache[request.query_id][request.data_key] = {
            "data": request.data,
            "metadata": request.metadata,
            "stored_at": stored_at,
        }

        return StoreResponse(
            query_id=request.query_id,
            data_key=request.data_key,
            stored_at=stored_at,
        )

    @app.get("/fetch/{query_id}/{data_key}", response_model=FetchResponse)
    async def fetch_by_key(query_id: str, data_key: str) -> FetchResponse:
        """Fetch a specific data entry by query_id and data_key."""
        if query_id not in cache or data_key not in cache.get(query_id, {}):
            raise HTTPException(
                status_code=404,
                detail=f"No data_key='{data_key}' for query_id={query_id}",
            )
        entry = cache[query_id][data_key]
        return FetchResponse(
            query_id=query_id, data_key=data_key,
            data=entry["data"], metadata=entry.get("metadata", {}),
            stored_at=entry["stored_at"],
        )

    @app.get("/fetch/{query_id}", response_model=FetchAllResponse)
    async def fetch_all(query_id: str) -> FetchAllResponse:
        """Fetch all data entries for a query_id."""
        if query_id not in cache:
            raise HTTPException(status_code=404, detail=f"No data for query_id={query_id}")
        return FetchAllResponse(query_id=query_id, entries=cache[query_id])

    @app.delete("/evict/{query_id}")
    async def evict(query_id: str) -> dict[str, str]:
        """Remove all cached data for a query_id."""
        if query_id in cache:
            del cache[query_id]
            return {"status": "evicted", "query_id": query_id}
        return {"status": "not_found", "query_id": query_id}

    # ---- Stream buffer endpoints ----

    @app.post("/stream/push", response_model=StreamPushResponse)
    async def stream_push(request: StreamPushRequest) -> StreamPushResponse:
        """Push a sample to a modality's rolling buffer."""
        if request.modality not in stream_buffers:
            stream_buffers[request.modality] = deque(maxlen=max_stream_buffer_size)

        ts = request.timestamp if request.timestamp > 0 else time.time()
        stream_buffers[request.modality].append({"data": request.data, "timestamp": ts})

        return StreamPushResponse(
            modality=request.modality,
            buffer_size=len(stream_buffers[request.modality]),
            timestamp=ts,
        )

    @app.get("/stream/{modality}/window", response_model=StreamWindowResponse)
    async def stream_window(modality: str, length: int = 128) -> StreamWindowResponse:
        """Get the last N samples from a modality's stream buffer."""
        if modality not in stream_buffers or not stream_buffers[modality]:
            raise HTTPException(
                status_code=404, detail=f"No stream data for modality='{modality}'"
            )

        buf = stream_buffers[modality]
        window = list(buf)[-length:]  # last N samples

        return StreamWindowResponse(
            modality=modality,
            window_length=len(window),
            samples=[s["data"] for s in window],
            timestamps=[s["timestamp"] for s in window],
        )

    @app.get("/stream/{modality}/info")
    async def stream_info(modality: str) -> dict[str, Any]:
        """Get info about a modality's stream buffer."""
        if modality not in stream_buffers:
            raise HTTPException(status_code=404, detail=f"No stream for '{modality}'")
        buf = stream_buffers[modality]
        return {
            "modality": modality,
            "buffer_size": len(buf),
            "max_size": max_stream_buffer_size,
            "oldest_timestamp": buf[0]["timestamp"] if buf else None,
            "newest_timestamp": buf[-1]["timestamp"] if buf else None,
        }

    @app.get("/stream/modalities")
    async def list_stream_modalities() -> dict[str, Any]:
        """List all active stream modalities and their buffer sizes."""
        return {
            mod: len(buf) for mod, buf in stream_buffers.items()
        }

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "data-hub",
            "cache_size": len(cache),
            "stream_modalities": len(stream_buffers),
        }

    return app
