"""FastAPI service for the platform orchestrator.

This replaces the dummy orchestrator in production. It wraps the
AdaptiveOrchestrator via OrchestratorBridge and exposes the same
POST /orchestrate interface that the gateway expects.

Usage:
  uvicorn rohe.orchestration.inference.orchestrator_api:app --port 9000

Environment variables:
  ORCHESTRATOR_CONFIG: path to orchestrator YAML config
  REDIS_URL: Redis URL for plan persistence
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI

from .orchestrator_bridge import OrchestratorBridge

logger = logging.getLogger(__name__)

app = FastAPI(title="ROHE Platform Orchestrator")
bridge: OrchestratorBridge | None = None


class OrchestrateRequest:
    """Matches the schema from examples/applications/common/schemas.py."""

    pass


@app.on_event("startup")
async def startup() -> None:
    global bridge
    try:
        bridge = OrchestratorBridge(
            config_path=os.environ.get("ORCHESTRATOR_CONFIG", ""),
            redis_url=os.environ.get("REDIS_URL", ""),
        )
        bridge.initialize()
        logger.info("Platform orchestrator initialized")
    except Exception as e:
        logger.error(f"Platform orchestrator failed to initialize: {e}")
        bridge = None


@app.post("/orchestrate")
async def orchestrate(request: dict[str, Any]) -> dict[str, Any]:
    """Execute orchestration using the platform AdaptiveOrchestrator."""
    if bridge is None:
        return {
            "query_id": request.get("query_id", ""),
            "ensemble_result": {},
            "individual_results": [],
            "model_count": 0,
        }

    return bridge.orchestrate(
        query_id=request.get("query_id", ""),
        pipeline_id=request.get("pipeline_id", ""),
        modalities=request.get("modalities", []),
        time_constraint_ms=request.get("time_constraint_ms", 500.0),
        data_hub_url=request.get("data_hub_url", ""),
    )


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok" if bridge else "not_initialized",
        "service": "platform-orchestrator",
    }
