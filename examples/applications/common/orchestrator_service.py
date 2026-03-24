"""Orchestrator service for example applications.

Supports multiple orchestration algorithms selectable per pipeline via
the ExecutionPlan's `orchestration_algorithm` field:

  - v2: InferenceOrchestrator (async, production-ready, default)
  - adaptive: AdaptiveOrchestrator (legacy, DuckDB-based, for experiments)
  - dream: DREAM algorithm variant
  - llf: LLF algorithm variant

Algorithm can be switched at runtime via:
  PUT /plans/{pipeline_id} with orchestration_algorithm field
  PUT /config/algorithm with {"pipeline_id": "...", "algorithm": "..."}
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
    app.state.orchestrator = None  # primary v2 InferenceOrchestrator
    app.state.plan_store = None  # Redis
    app.state.algorithm_bridge = None  # for legacy algorithms

    @app.on_event("startup")
    async def startup() -> None:
        from rohe.models.execution_plan import ExecutionPlan
        from rohe.orchestration.inference.orchestrator_v2 import (
            InferenceOrchestrator,
            OrchestratorConfig,
        )
        from rohe.orchestration.inference.service_registry import InMemoryServiceRegistry

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

        # Initialize legacy algorithm bridge (for adaptive/dream/llf)
        _init_algorithm_bridge(app)

        logger.info(f"Orchestrator ready: {len(orchestrator._plans)} plans loaded")

    # -- Orchestration endpoint --

    @app.post("/orchestrate", response_model=OrchestrateResponse)
    async def orchestrate(request: OrchestrateRequest) -> OrchestrateResponse:
        """Execute inference pipeline using the algorithm specified in the ExecutionPlan."""
        orch = app.state.orchestrator
        if orch is None:
            return OrchestrateResponse(query_id=request.query_id, ensemble_result={}, model_count=0)

        # Check which algorithm the plan specifies
        plan = orch.get_plan(request.pipeline_id)
        algorithm = "v2"
        if plan:
            algorithm = plan.orchestration_algorithm

        if algorithm == "v2":
            result = await orch.orchestrate(
                query_id=request.query_id,
                pipeline_id=request.pipeline_id,
                modalities=request.modalities,
                time_constraint_ms=request.time_constraint_ms,
                data_hub_url=request.data_hub_url,
                window_length=request.window_length,
            )
        else:
            # Delegate to legacy algorithm bridge
            result = _run_legacy_algorithm(
                app, algorithm, request.query_id, request.pipeline_id,
                request.modalities, request.time_constraint_ms, request.data_hub_url,
            )

        return OrchestrateResponse(**result)

    # -- Algorithm configuration API --

    @app.put("/config/algorithm")
    async def set_algorithm(body: dict[str, Any]) -> dict[str, str]:
        """Switch orchestration algorithm for a pipeline at runtime.

        Body: {"pipeline_id": "bts", "algorithm": "adaptive"}
        Available algorithms: v2, adaptive, dream, llf
        """
        from rohe.orchestration import ORCHESTRATOR_REGISTRY

        pipeline_id = body.get("pipeline_id", "")
        algorithm = body.get("algorithm", "")

        if algorithm not in ORCHESTRATOR_REGISTRY:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown algorithm '{algorithm}'. Available: {list(ORCHESTRATOR_REGISTRY.keys())}",
            )

        orch = app.state.orchestrator
        if orch is None:
            raise HTTPException(status_code=503, detail="Orchestrator not ready")

        plan = orch.get_plan(pipeline_id)
        if plan is None:
            raise HTTPException(status_code=404, detail=f"Plan '{pipeline_id}' not found")

        plan.orchestration_algorithm = algorithm
        plan._bump_version()

        if app.state.plan_store:
            app.state.plan_store.save_plan(plan.model_dump(mode="json"))

        logger.info(f"Switched pipeline '{pipeline_id}' to algorithm '{algorithm}' (v{plan.version})")
        return {
            "status": "switched",
            "pipeline_id": pipeline_id,
            "algorithm": algorithm,
            "version": str(plan.version),
        }

    @app.get("/config/algorithms")
    async def list_algorithms() -> dict[str, Any]:
        """List available orchestration algorithms and their descriptions."""
        from rohe.orchestration import ORCHESTRATOR_REGISTRY
        from rohe.orchestration.inference.ensemble_selector import EnsembleSelectorFactory

        return {
            "orchestration_algorithms": list(ORCHESTRATOR_REGISTRY.keys()),
            "ensemble_selection_strategies": EnsembleSelectorFactory.available_strategies(),
            "descriptions": {
                "v2": "Production async orchestrator with ExecutionPlan, DataHub, and httpx",
                "adaptive": "Original AdaptiveOrchestrator with DuckDB service registry and ThreadPoolExecutor",
                "dream": "DREAM algorithm: deadline-aware recursive ensemble allocation for multimodal inference",
                "llf": "LLF algorithm: least-laxity-first scheduling for time-constrained inference",
            },
            "ensemble_descriptions": {
                "enhance_confidence": "Select services specialized in top-K most confident predictions",
                "select_by_overall_accuracy": "Select services with highest overall accuracy",
                "enhance_generalization": "Select services that improve worst-K class predictions",
            },
        }

    # -- Plan management API --

    @app.get("/plans")
    async def list_plans() -> dict[str, Any]:
        orch = app.state.orchestrator
        if orch is None:
            return {}
        return {
            pid: {
                "version": plan.version,
                "algorithm": plan.orchestration_algorithm,
                "modalities": list(plan.modality_ensembles.keys()),
                "phases": len(plan.execution_phases),
                "ensemble_strategies": {
                    mod: ens.selection_strategy
                    for mod, ens in plan.modality_ensembles.items()
                },
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
        plans = orch._plans if orch else {}
        return {
            "status": "ok" if orch else "not_ready",
            "service": "orchestrator",
            "plans_loaded": len(plans),
            "redis_connected": app.state.plan_store is not None,
            "engine": "InferenceOrchestrator_v2",
            "available_algorithms": ["v2", "adaptive", "dream", "llf"],
            "pipeline_algorithms": {
                pid: plan.orchestration_algorithm for pid, plan in plans.items()
            },
        }

    return app


# -- Legacy algorithm bridge --

def _init_algorithm_bridge(app: FastAPI) -> None:
    """Initialize the bridge for legacy algorithms (adaptive/dream/llf).

    These algorithms require DuckDB and userModule, so they may not be
    available in all environments. The bridge is optional.
    """
    orchestrator_config = os.environ.get("ORCHESTRATOR_CONFIG", "")
    redis_url = os.environ.get("REDIS_URL", "")

    if not orchestrator_config:
        logger.info("No ORCHESTRATOR_CONFIG set, legacy algorithms unavailable")
        return

    try:
        from rohe.orchestration.inference.orchestrator_bridge import OrchestratorBridge
        bridge = OrchestratorBridge(
            config_path=orchestrator_config,
            redis_url=redis_url,
        )
        bridge.initialize()
        app.state.algorithm_bridge = bridge
        logger.info("Legacy algorithm bridge initialized (adaptive/dream/llf available)")
    except Exception as e:
        logger.info(f"Legacy algorithm bridge not available: {e}")


def _run_legacy_algorithm(
    app: FastAPI,
    algorithm: str,
    query_id: str,
    pipeline_id: str,
    modalities: list[str],
    time_constraint_ms: float,
    data_hub_url: str,
) -> dict[str, Any]:
    """Run a legacy algorithm (adaptive/dream/llf) via the bridge."""
    bridge = app.state.algorithm_bridge
    if bridge is None:
        logger.warning(
            f"Legacy algorithm '{algorithm}' requested but bridge not available. "
            f"Set ORCHESTRATOR_CONFIG to enable. Falling back to v2."
        )
        # Fallback: use v2 orchestrator
        import asyncio
        orch = app.state.orchestrator
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(orch.orchestrate(
            query_id=query_id, pipeline_id=pipeline_id,
            modalities=modalities, time_constraint_ms=time_constraint_ms,
            data_hub_url=data_hub_url,
        ))

    return bridge.orchestrate(
        query_id=query_id,
        pipeline_id=pipeline_id,
        modalities=modalities,
        time_constraint_ms=time_constraint_ms,
        data_hub_url=data_hub_url,
    )


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
