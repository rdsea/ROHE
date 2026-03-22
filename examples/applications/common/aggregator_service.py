"""Reusable aggregator service factory.

All apps use this to create their aggregator. Strategy is configurable
via AGGREGATION_STRATEGY env var.
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI

from .aggregation import aggregate_predictions
from .schemas import AggregateRequest, AggregateResponse

def create_aggregator_app(service_name: str = "aggregator") -> FastAPI:
    app = FastAPI(title=f"{service_name} Service")

    @app.post("/aggregate", response_model=AggregateResponse)
    async def aggregate(request: AggregateRequest) -> AggregateResponse:
        strategy = request.strategy or os.environ.get("AGGREGATION_STRATEGY", "confidence_avg")
        return aggregate_predictions(request.query_id, request.results, strategy)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "service": service_name}

    return app
