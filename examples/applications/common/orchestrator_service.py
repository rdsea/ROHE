"""Lightweight orchestrator service for example applications.

Implements the control flow for the inference pipeline:
  1. Load ExecutionPlan (from file or Redis)
  2. For each execution phase:
     a. Dispatch preprocessing tasks (via data references)
     b. Dispatch inference tasks to ensemble members (parallel, via data references)
     c. Evaluate results and decide whether to run next phase
  3. Call aggregator with collected results
  4. Return final result to gateway
  5. Optionally evict data from DataHub

The orchestrator never touches actual data -- only data references.
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI

from .schemas import (
    AggregateRequest,
    InferenceResponse,
    InferenceTaskRequest,
    OrchestrateRequest,
    OrchestrateResponse,
    PreprocessTaskRequest,
)

logger = logging.getLogger(__name__)


def create_orchestrator_app() -> FastAPI:
    """Create the orchestrator FastAPI application."""
    app = FastAPI(title="Orchestrator")
    app.state.execution_plans: dict[str, Any] = {}  # pipeline_id -> ExecutionPlan
    app.state.plan_store = None  # ExecutionPlanStore (Redis-backed)
    app.state.timeout: float = 30.0
    app.state.evict_after_query: bool = True

    @app.on_event("startup")
    async def startup() -> None:
        app.state.timeout = float(os.environ.get("REQUEST_TIMEOUT_SECONDS", "30"))
        app.state.evict_after_query = os.environ.get("EVICT_AFTER_QUERY", "true").lower() == "true"

        # Connect to Redis for plan persistence (optional)
        redis_url = os.environ.get("REDIS_URL", "")
        if redis_url:
            try:
                from .execution_plan_store import ExecutionPlanStore
                app.state.plan_store = ExecutionPlanStore(redis_url=redis_url)
                _load_plans_from_redis(app)
            except Exception as e:
                logger.warning(f"Redis unavailable, falling back to file-based plans: {e}")

        # Load execution plans from YAML files (supplements or seeds Redis)
        plans_dir = os.environ.get("EXECUTION_PLANS_DIR", "/config/plans")
        if Path(plans_dir).is_dir():
            _load_plans_from_dir(app, plans_dir)

        # Load from individual file
        plan_file = os.environ.get("EXECUTION_PLAN_FILE", "")
        if plan_file and Path(plan_file).is_file():
            _load_plan_from_file(app, plan_file)

        # Persist any file-loaded plans to Redis (seed)
        if app.state.plan_store:
            for plan in app.state.execution_plans.values():
                app.state.plan_store.save_plan(plan.model_dump(mode="json"))

        logger.info(f"Orchestrator loaded {len(app.state.execution_plans)} execution plans")

    @app.post("/orchestrate", response_model=OrchestrateResponse)
    async def orchestrate(request: OrchestrateRequest) -> OrchestrateResponse:
        """Execute the full inference pipeline for a query."""
        plan = app.state.execution_plans.get(request.pipeline_id)
        if plan is None:
            logger.warning(f"No execution plan for pipeline '{request.pipeline_id}'")
            return OrchestrateResponse(
                query_id=request.query_id,
                ensemble_result={},
                model_count=0,
            )

        data_hub_url = request.data_hub_url or plan.data_hub_url
        all_results: list[InferenceResponse] = []

        # Execute phases sequentially
        for phase in plan.execution_phases:
            # Check conditional phase
            if phase.is_conditional and phase.condition and all_results:
                if not _should_run_phase(phase, all_results):
                    logger.debug(f"Skipping conditional phase {phase.phase_id}")
                    continue

            # Process all modalities in this phase concurrently
            phase_results = await _execute_phase(
                plan=plan,
                phase_modalities=phase.modalities,
                query_id=request.query_id,
                data_hub_url=data_hub_url,
                timeout=app.state.timeout,
            )
            all_results.extend(phase_results)

        # Aggregate results
        ensemble_result: dict[str, float] = {}
        if all_results:
            ensemble_result = await _aggregate_results(
                aggregator_url=plan.aggregator_url,
                query_id=request.query_id,
                results=all_results,
                timeout=app.state.timeout,
            )

        # Evict data from DataHub
        if app.state.evict_after_query:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.delete(f"{data_hub_url}/evict/{request.query_id}")
            except (httpx.TimeoutException, httpx.ConnectError):
                logger.debug(f"DataHub eviction failed for query_id={request.query_id}")

        return OrchestrateResponse(
            query_id=request.query_id,
            ensemble_result=ensemble_result,
            individual_results=all_results,
            model_count=len(all_results),
        )

    # -- Plan management API --

    @app.get("/plans")
    async def list_plans() -> dict[str, Any]:
        """List loaded execution plans."""
        return {
            pid: {
                "version": plan.version,
                "modalities": list(plan.modality_ensembles.keys()),
                "phases": len(plan.execution_phases),
            }
            for pid, plan in app.state.execution_plans.items()
        }

    @app.get("/plans/{pipeline_id}")
    async def get_plan(pipeline_id: str) -> dict[str, Any]:
        """Get full execution plan for a pipeline."""
        from fastapi import HTTPException
        plan = app.state.execution_plans.get(pipeline_id)
        if plan is None:
            raise HTTPException(status_code=404, detail=f"Plan '{pipeline_id}' not found")
        return plan.model_dump(mode="json")

    @app.put("/plans/{pipeline_id}")
    async def update_plan(pipeline_id: str, plan_data: dict[str, Any]) -> dict[str, str]:
        """Update an execution plan at runtime.

        This is the endpoint the platform orchestrator calls to modify ensembles.
        """
        from rohe.models.execution_plan import ExecutionPlan
        plan_data["pipeline_id"] = pipeline_id
        plan = ExecutionPlan.model_validate(plan_data)
        app.state.execution_plans[pipeline_id] = plan

        # Persist to Redis
        if app.state.plan_store:
            app.state.plan_store.save_plan(plan.model_dump(mode="json"))

        logger.info(f"Updated plan '{pipeline_id}' to v{plan.version}")
        return {"status": "updated", "pipeline_id": pipeline_id, "version": str(plan.version)}

    @app.patch("/plans/{pipeline_id}/ensemble/{modality}")
    async def patch_modality_ensemble(
        pipeline_id: str, modality: str, ensemble_data: dict[str, Any],
    ) -> dict[str, str]:
        """Patch a specific modality ensemble (add/remove members, change strategy)."""
        from fastapi import HTTPException
        from rohe.models.execution_plan import ModalityEnsemble
        plan = app.state.execution_plans.get(pipeline_id)
        if plan is None:
            raise HTTPException(status_code=404, detail=f"Plan '{pipeline_id}' not found")
        if modality not in plan.modality_ensembles:
            raise HTTPException(status_code=404, detail=f"Modality '{modality}' not in plan")

        updated_ensemble = ModalityEnsemble.model_validate(ensemble_data)
        plan.modality_ensembles[modality] = updated_ensemble
        plan._bump_version()

        if app.state.plan_store:
            app.state.plan_store.save_plan(plan.model_dump(mode="json"))

        logger.info(f"Patched '{modality}' ensemble in plan '{pipeline_id}' -> v{plan.version}")
        return {"status": "patched", "pipeline_id": pipeline_id, "modality": modality}

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "orchestrator",
            "plans_loaded": len(app.state.execution_plans),
            "redis_connected": app.state.plan_store is not None,
        }

    return app


async def _execute_phase(
    plan: Any,  # ExecutionPlan
    phase_modalities: list[str],
    query_id: str,
    data_hub_url: str,
    timeout: float,
) -> list[InferenceResponse]:
    """Execute all modalities in a phase concurrently."""
    tasks = []
    for modality in phase_modalities:
        ensemble = plan.modality_ensembles.get(modality)
        if ensemble is None:
            logger.warning(f"No ensemble for modality '{modality}' in plan '{plan.pipeline_id}'")
            continue
        tasks.append(
            _execute_modality(
                ensemble=ensemble,
                query_id=query_id,
                data_hub_url=data_hub_url,
                timeout=timeout,
            )
        )

    if not tasks:
        return []

    phase_results = await asyncio.gather(*tasks, return_exceptions=True)
    results: list[InferenceResponse] = []
    for r in phase_results:
        if isinstance(r, list):
            results.extend(r)
        elif isinstance(r, Exception):
            logger.warning(f"Modality execution failed: {r}")
    return results


async def _execute_modality(
    ensemble: Any,  # ModalityEnsemble
    query_id: str,
    data_hub_url: str,
    timeout: float,
) -> list[InferenceResponse]:
    """Execute preprocessing + inference for a single modality."""
    data_key = ensemble.modality  # raw data key

    # Step 1: Preprocessing (if configured)
    if ensemble.preprocessor is not None:
        preproc = ensemble.preprocessor
        preproc_request = PreprocessTaskRequest(
            query_id=query_id,
            modality=ensemble.modality,
            data_key=data_key,
            output_data_key=preproc.output_data_key,
            data_hub_url=data_hub_url,
        )
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    preproc.service_url,
                    json=preproc_request.model_dump(),
                )
                if resp.status_code == 200:
                    data_key = preproc.output_data_key  # use preprocessed data
                else:
                    logger.warning(
                        f"Preprocessor {preproc.service_url} returned {resp.status_code}"
                    )
        except (httpx.TimeoutException, httpx.ConnectError):
            logger.warning(f"Preprocessor {preproc.service_url} unavailable")

    # Step 2: Dispatch inference to active ensemble members (parallel)
    active_members = ensemble.get_active_members()
    if not active_members:
        return []

    async def _call_inference(member: Any) -> InferenceResponse | None:
        request = InferenceTaskRequest(
            query_id=query_id,
            inf_id=f"{query_id}-{member.instance_id}",
            modality=ensemble.modality,
            data_key=data_key,
            data_hub_url=data_hub_url,
            instance_id=member.instance_id,
            model_id=member.model_id,
            device_id=member.device_type,
        )
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    member.inference_url,
                    json=request.model_dump(),
                )
                if resp.status_code == 200:
                    return InferenceResponse(**resp.json())
                logger.warning(
                    f"Inference {member.inference_url} returned {resp.status_code}"
                )
        except (httpx.TimeoutException, httpx.ConnectError):
            logger.warning(f"Inference {member.inference_url} unavailable")
        return None

    inference_tasks = [_call_inference(m) for m in active_members]
    raw_results = await asyncio.gather(*inference_tasks)
    return [r for r in raw_results if r is not None]


def _should_run_phase(
    phase: Any,  # ExecutionPhase
    previous_results: list[InferenceResponse],
) -> bool:
    """Evaluate whether a conditional phase should run."""
    condition = phase.condition
    if condition is None:
        return True

    # Filter results from source modalities
    source_results = [
        r for r in previous_results
        if r.modality in condition.source_modalities
    ]
    if not source_results:
        return True  # no data to evaluate, run the phase

    if condition.trigger == "confidence_below":
        avg_confidence = sum(r.confidence for r in source_results) / len(source_results)
        return avg_confidence < condition.threshold

    if condition.trigger == "agreement_below":
        # Check if top predictions agree
        top_preds = [next(iter(r.predictions), "") for r in source_results]
        if not top_preds:
            return True
        agreement = top_preds.count(top_preds[0]) / len(top_preds)
        return agreement < condition.threshold

    return True


async def _aggregate_results(
    aggregator_url: str,
    query_id: str,
    results: list[InferenceResponse],
    timeout: float,
) -> dict[str, float]:
    """Call the aggregator service with all results."""
    agg_request = AggregateRequest(
        query_id=query_id,
        results=results,
        strategy="confidence_weighted",
    )
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                aggregator_url,
                json=agg_request.model_dump(),
            )
            if resp.status_code == 200:
                return resp.json().get("ensemble_predictions", {})
    except (httpx.TimeoutException, httpx.ConnectError):
        logger.warning(f"Aggregator {aggregator_url} unavailable")

    # Fallback: simple average
    all_classes: set[str] = set()
    for r in results:
        all_classes.update(r.predictions.keys())
    return {
        cls: round(sum(r.predictions.get(cls, 0.0) for r in results) / len(results), 4)
        for cls in all_classes
    }


def _load_plans_from_redis(app: FastAPI) -> None:
    """Load all execution plans from Redis."""
    from rohe.models.execution_plan import ExecutionPlan

    store = app.state.plan_store
    if store is None:
        return
    for pipeline_id in store.list_plans():
        plan_dict = store.get_plan(pipeline_id)
        if plan_dict:
            try:
                plan = ExecutionPlan.model_validate(plan_dict)
                app.state.execution_plans[plan.pipeline_id] = plan
                logger.info(f"Loaded plan from Redis: {plan.pipeline_id} v{plan.version}")
            except Exception as e:
                logger.warning(f"Failed to load plan '{pipeline_id}' from Redis: {e}")


def _load_plans_from_dir(app: FastAPI, plans_dir: str) -> None:
    """Load all YAML execution plans from a directory."""
    from rohe.models.execution_plan import ExecutionPlan

    for path in Path(plans_dir).glob("*.yaml"):
        try:
            plan = ExecutionPlan.from_yaml_file(str(path))
            app.state.execution_plans[plan.pipeline_id] = plan
            logger.info(f"Loaded plan: {plan.pipeline_id} v{plan.version}")
        except Exception as e:
            logger.warning(f"Failed to load plan from {path}: {e}")


def _load_plan_from_file(app: FastAPI, path: str) -> None:
    """Load a single YAML execution plan."""
    from rohe.models.execution_plan import ExecutionPlan

    try:
        plan = ExecutionPlan.from_yaml_file(path)
        app.state.execution_plans[plan.pipeline_id] = plan
        logger.info(f"Loaded plan: {plan.pipeline_id} v{plan.version}")
    except Exception as e:
        logger.warning(f"Failed to load plan from {path}: {e}")
