"""Reusable DataHub service factory.

The DataHub is the data plane for the orchestrated pipeline. It stores
raw and preprocessed data keyed by (query_id, data_key). Services fetch
their own input from DataHub using data references passed by the orchestrator.

Storage is in-memory with LRU eviction. For production, back with Redis or
object storage.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class StoreRequest(BaseModel):
    """Request to store data in the DataHub."""

    query_id: str
    data_key: str  # e.g. "video", "timeseries", "video_preprocessed"
    data: Any  # raw bytes reference, sensor values, sample ID, etc.
    metadata: dict[str, str] = {}


class StoreResponse(BaseModel):
    """Response from storing data."""

    model_config = ConfigDict(frozen=True)

    query_id: str
    data_key: str
    stored_at: float


class FetchResponse(BaseModel):
    """Response from fetching a specific data entry."""

    model_config = ConfigDict(frozen=True)

    query_id: str
    data_key: str
    data: Any  # the stored data
    metadata: dict[str, str] = {}
    stored_at: float


class FetchAllResponse(BaseModel):
    """Response from fetching all entries for a query."""

    model_config = ConfigDict(frozen=True)

    query_id: str
    entries: dict[str, Any]  # data_key -> {data, metadata, stored_at}


def create_data_hub_app(
    max_cache_size: int = 10_000,
) -> FastAPI:
    """Create a DataHub FastAPI application."""

    app = FastAPI(title="DataHub")

    # In-memory cache: {query_id: {data_key: {data, metadata, stored_at}}}
    cache: dict[str, dict[str, dict[str, Any]]] = {}

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

        logger.debug(
            f"Stored data_key='{request.data_key}' for query_id={request.query_id}"
        )

        return StoreResponse(
            query_id=request.query_id,
            data_key=request.data_key,
            stored_at=stored_at,
        )

    @app.get("/fetch/{query_id}/{data_key}", response_model=FetchResponse)
    async def fetch_by_key(query_id: str, data_key: str) -> FetchResponse:
        """Fetch a specific data entry by query_id and data_key."""
        if query_id not in cache:
            raise HTTPException(
                status_code=404, detail=f"No data for query_id={query_id}"
            )
        if data_key not in cache[query_id]:
            raise HTTPException(
                status_code=404,
                detail=f"No data_key='{data_key}' for query_id={query_id}",
            )

        entry = cache[query_id][data_key]
        return FetchResponse(
            query_id=query_id,
            data_key=data_key,
            data=entry["data"],
            metadata=entry.get("metadata", {}),
            stored_at=entry["stored_at"],
        )

    @app.get("/fetch/{query_id}", response_model=FetchAllResponse)
    async def fetch_all(query_id: str) -> FetchAllResponse:
        """Fetch all stored data entries for a query_id."""
        if query_id not in cache:
            raise HTTPException(
                status_code=404, detail=f"No data for query_id={query_id}"
            )

        return FetchAllResponse(
            query_id=query_id,
            entries=cache[query_id],
        )

    @app.delete("/evict/{query_id}")
    async def evict(query_id: str) -> dict[str, str]:
        """Remove all cached data for a query_id."""
        if query_id in cache:
            del cache[query_id]
            return {"status": "evicted", "query_id": query_id}
        return {"status": "not_found", "query_id": query_id}

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "data-hub",
            "cache_size": len(cache),
        }

    return app
