"""Data hub service acting as a data cache for multi-modal queries.

Stores and retrieves intermediate data (video frames, sensor readings)
for use by inference services during multi-modal processing.
"""
from __future__ import annotations

import logging
import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(title="Smart Building Data Hub")

# In-memory cache (keyed by query_id)
_cache: dict[str, dict] = {}
MAX_CACHE_SIZE = 10000


class StoreRequest(BaseModel):
    query_id: str
    modality: str
    data: list[float] | str
    metadata: dict[str, str] = {}


class StoreResponse(BaseModel):
    query_id: str
    stored_at: float
    modality: str


class FetchResponse(BaseModel):
    query_id: str
    entries: list[dict]


@app.post("/store")
async def store(request: StoreRequest) -> StoreResponse:
    """Store data for a given query_id and modality."""
    if len(_cache) >= MAX_CACHE_SIZE:
        oldest_key = next(iter(_cache))
        del _cache[oldest_key]
        logger.warning(f"Cache full, evicted entry for query_id={oldest_key}")

    stored_at = time.time()
    entry = {
        "modality": request.modality,
        "data": request.data,
        "metadata": request.metadata,
        "stored_at": stored_at,
    }

    if request.query_id not in _cache:
        _cache[request.query_id] = {"entries": []}
    _cache[request.query_id]["entries"].append(entry)

    logger.info(f"Stored {request.modality} data for query_id={request.query_id}")

    return StoreResponse(
        query_id=request.query_id,
        stored_at=stored_at,
        modality=request.modality,
    )


@app.get("/fetch/{query_id}")
async def fetch(query_id: str) -> FetchResponse:
    """Retrieve all stored data for a given query_id."""
    if query_id not in _cache:
        raise HTTPException(status_code=404, detail=f"No data found for query_id={query_id}")

    return FetchResponse(
        query_id=query_id,
        entries=_cache[query_id]["entries"],
    )


@app.delete("/evict/{query_id}")
async def evict(query_id: str) -> dict[str, str]:
    """Remove cached data for a given query_id."""
    if query_id in _cache:
        del _cache[query_id]
        return {"status": "evicted", "query_id": query_id}
    return {"status": "not_found", "query_id": query_id}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "data-hub", "cache_size": str(len(_cache))}
