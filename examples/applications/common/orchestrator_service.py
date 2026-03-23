"""Orchestrator service for example applications.

Uses the production InferenceOrchestrator (v2) from rohe.orchestration.
Loads ExecutionPlans from YAML files and/or Redis, exposes plan management API.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

from .schemas import OrchestrateRequest, OrchestrateResponse

logger = logging.getLogger(__name__)


def create_orchestrator_app() -> FastAPI:
    """Create the orchestrator FastAPI application."""
    app = FastAPI(title="Orchestrator")
    app.state.orchestrator = None  # InferenceOrchestrator
    app.state.plan_store = None  # ExecutionPlanStore (Redis)

    @app.on_event("startup")
    async def startup() -> None:
        from rohe.models.execution_plan import ExecutionPlan
        from rohe.orchestration.inference.orchestrator_v2 import (
            InferenceOrchestrator,
            OrchestratorConfig,
        )
        from rohe.orchestration.inference.service_registry import InMemoryServiceRegistry

        # Create orchestrator with in-memory registry (services discovered via ExecutionPlan)
        config = OrchestratorConfig(
            default_timeout_seconds=float(os.environ.get("REQUEST_TIMEOUT_SECONDS", "30")),
            evict_after_query=os.environ.get("EVICT_AFTER_QUERY", "true").lower() == "true",
        )
        registry = InMemoryServiceRegistry()
        orchestrator = InferenceOrchestrator(registry=registry, config=config)
        app.state.orchestrator = orchestrator

        # Connect to Redis
        redis_url = os.environ.get("REDIS_URL", "")
        if redis_url:
            try:
                from .execution_plan_store import ExecutionPlanStore
                app.state.plan_store = ExecutionPlanStore(redis_url=redis_url)
                _load_plans_from_redis(app, orchestrator)
            except Exception as e:
                logger.warning(f"Redis unavailable: {e}")

        # Load from YAML files
        plans_dir = os.environ.get("EXECUTION_PLANS_DIR", "/config/plans")
        if Path(plans_dir).is_dir():
            _load_plans_from_dir(orchestrator, plans_dir)

        plan_file = os.environ.get("EXECUTION_PLAN_FILE", "")
        if plan_file and Path(plan_file).is_file():
            _load_plan_from_file(orchestrator, plan_file)

        # Seed Redis with file-loaded plans
        if app.state.plan_store:
            for pid, plan in (orchestrator._plans or {}).items():
                app.state.plan_store.save_plan(plan.model_dump(mode="json"))

        logger.info(f"Orchestrator ready: {len(orchestrator._plans)} plans loaded")

    # -- Orchestration endpoint --

    @app.post("/orchestrate", response_model=OrchestrateResponse)
    async def orchestrate(request: OrchestrateRequest) -> OrchestrateResponse:
        """Execute the full inference pipeline for a query."""
        orch = app.state.orchestrator
        if orch is None:
            return OrchestrateResponse(query_id=request.query_id, ensemble_result={}, model_count=0)

        result = await orch.orchestrate(
            query_id=request.query_id,
            pipeline_id=request.pipeline_id,
            modalities=request.modalities,
            time_constraint_ms=request.time_constraint_ms,
            data_hub_url=request.data_hub_url,
            window_length=request.window_length,
        )
        return OrchestrateResponse(**result)

    # -- Plan management API --

    @app.get("/plans")
    async def list_plans() -> dict[str, Any]:
        orch = app.state.orchestrator
        if orch is None:
            return {}
        return {
            pid: {
                "version": plan.version,
                "modalities": list(plan.modality_ensembles.keys()),
                "phases": len(plan.execution_phases),
            }
            for pid, plan in orch._plans.items()
        }

    @app.get("/plans/{pipeline_id}")
    async def get_plan(pipeline_id: str) -> dict[str, Any]:
        orch = app.state.orchestrator
        if orch is None:
            raise HTTPException(status_code=503, detail="Orchestrator not ready")
        plan = orch.get_plan(pipeline_id)
        if plan is None:
            raise HTTPException(status_code=404, detail=f"Plan '{pipeline_id}' not found")
        return plan.model_dump(mode="json")

    @app.put("/plans/{pipeline_id}")
    async def update_plan(pipeline_id: str, plan_data: dict[str, Any]) -> dict[str, str]:
        from rohe.models.execution_plan import ExecutionPlan
        plan_data["pipeline_id"] = pipeline_id
        plan = ExecutionPlan.model_validate(plan_data)
        app.state.orchestrator.load_plan(plan)
        if app.state.plan_store:
            app.state.plan_store.save_plan(plan.model_dump(mode="json"))
        return {"status": "updated", "pipeline_id": pipeline_id, "version": str(plan.version)}

    @app.patch("/plans/{pipeline_id}/ensemble/{modality}")
    async def patch_modality_ensemble(
        pipeline_id: str, modality: str, ensemble_data: dict[str, Any],
    ) -> dict[str, str]:
        from rohe.models.execution_plan import ModalityEnsemble
        orch = app.state.orchestrator
        if orch is None:
            raise HTTPException(status_code=503, detail="Orchestrator not ready")
        plan = orch.get_plan(pipeline_id)
        if plan is None:
            raise HTTPException(status_code=404, detail=f"Plan '{pipeline_id}' not found")
        if modality not in plan.modality_ensembles:
            raise HTTPException(status_code=404, detail=f"Modality '{modality}' not in plan")

        plan.modality_ensembles[modality] = ModalityEnsemble.model_validate(ensemble_data)
        plan._bump_version()
        if app.state.plan_store:
            app.state.plan_store.save_plan(plan.model_dump(mode="json"))
        return {"status": "patched", "pipeline_id": pipeline_id, "modality": modality}

    @app.get("/health")
    async def health() -> dict[str, Any]:
        orch = app.state.orchestrator
        return {
            "status": "ok" if orch else "not_ready",
            "service": "orchestrator",
            "plans_loaded": len(orch._plans) if orch else 0,
            "redis_connected": app.state.plan_store is not None,
            "engine": "InferenceOrchestrator_v2",
        }

    return app


# -- Plan loading helpers --

def _load_plans_from_redis(app: FastAPI, orchestrator: Any) -> None:
    from rohe.models.execution_plan import ExecutionPlan
    store = app.state.plan_store
    if store is None:
        return
    for pipeline_id in store.list_plans():
        plan_dict = store.get_plan(pipeline_id)
        if plan_dict:
            try:
                plan = ExecutionPlan.model_validate(plan_dict)
                orchestrator.load_plan(plan)
            except Exception as e:
                logger.warning(f"Failed to load plan '{pipeline_id}' from Redis: {e}")


def _load_plans_from_dir(orchestrator: Any, plans_dir: str) -> None:
    from rohe.models.execution_plan import ExecutionPlan
    for path in Path(plans_dir).glob("*.yaml"):
        try:
            plan = ExecutionPlan.from_yaml_file(str(path))
            orchestrator.load_plan(plan)
        except Exception as e:
            logger.warning(f"Failed to load plan from {path}: {e}")


def _load_plan_from_file(orchestrator: Any, path: str) -> None:
    from rohe.models.execution_plan import ExecutionPlan
    try:
        plan = ExecutionPlan.from_yaml_file(path)
        orchestrator.load_plan(plan)
    except Exception as e:
        logger.warning(f"Failed to load plan from {path}: {e}")
