"""Production inference orchestrator (v2).

Async-first orchestrator with dependency injection, proper timeouts,
and integration with ExecutionPlan, ServiceRegistry, and EnsembleSelector.

Replaces the legacy AdaptiveOrchestrator with clean architecture:
- No sys.path hacks
- No hardcoded DuckDB
- No multiprocessing.Process
- No unbounded Timer threads
- Proper async/await with httpx
- Type-safe throughout
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx
from pydantic import BaseModel

from rohe.models.execution_plan import ExecutionPlan, ModalityEnsemble
from rohe.monitoring.inference_reporter import InferenceReporter, NoOpReporter
from rohe.orchestration.inference.ensemble_selector import EnsembleSelectorFactory
from rohe.orchestration.inference.service_registry import ServiceRegistry

logger = logging.getLogger(__name__)


class OrchestratorConfig(BaseModel):
    """Configuration for the InferenceOrchestrator."""

    default_timeout_seconds: float = 30.0
    max_workers: int = 10
    overhead_fraction: float = 0.01
    refresh_interval_seconds: float = 10.0
    evict_after_query: bool = False


class InferenceOrchestrator:
    """Production-ready inference orchestrator.

    Implements the 4-step pipeline:
    1. Load execution plan + select ensemble per modality
    2. Dispatch preprocessing (via data references)
    3. Dispatch inference to ensemble members (parallel, async)
    4. Aggregate results and return

    All I/O is async via httpx.AsyncClient.
    """

    def __init__(
        self,
        registry: ServiceRegistry,
        reporter: InferenceReporter | None = None,
        config: OrchestratorConfig | None = None,
    ) -> None:
        self._registry = registry
        self._reporter = reporter or NoOpReporter()
        self._config = config or OrchestratorConfig()
        self._selector_factory = EnsembleSelectorFactory()
        self._plans: dict[str, ExecutionPlan] = {}

    def load_plan(self, plan: ExecutionPlan) -> None:
        """Register an execution plan for a pipeline."""
        self._plans[plan.pipeline_id] = plan
        logger.info(f"Loaded plan: {plan.pipeline_id} v{plan.version}")

    def get_plan(self, pipeline_id: str) -> ExecutionPlan | None:
        """Get the current execution plan for a pipeline."""
        return self._plans.get(pipeline_id)

    async def orchestrate(
        self,
        query_id: str,
        pipeline_id: str,
        modalities: list[str],
        time_constraint_ms: float = 500.0,
        data_hub_url: str = "",
        window_length: int = 0,
    ) -> dict[str, Any]:
        """Execute the full inference pipeline for a query.

        Returns dict matching OrchestrateResponse schema.
        """
        start = time.perf_counter()
        plan = self._plans.get(pipeline_id)
        if plan is None:
            logger.warning(f"No execution plan for pipeline '{pipeline_id}'")
            return self._empty_response(query_id)

        data_hub = data_hub_url or plan.data_hub_url
        timeout = min(time_constraint_ms / 1000, self._config.default_timeout_seconds)
        all_results: list[dict[str, Any]] = []

        # Execute phases sequentially, modalities within each phase concurrently
        for phase in plan.execution_phases:
            if phase.is_conditional and phase.condition and all_results:
                if not self._should_run_phase(phase, all_results):
                    logger.debug(f"Skipping conditional phase {phase.phase_id}")
                    continue

            elapsed = time.perf_counter() - start
            remaining = timeout - elapsed
            if remaining <= 0:
                logger.warning(f"Time budget exhausted after phase {phase.phase_id}")
                break

            phase_results = await self._execute_phase(
                plan=plan,
                modalities=phase.modalities,
                query_id=query_id,
                data_hub_url=data_hub,
                window_length=window_length,
                timeout=remaining,
            )
            all_results.extend(phase_results)

        # Aggregate
        ensemble_result = await self._aggregate(
            plan.aggregator_url, query_id, all_results, timeout=5.0
        )

        # Evict data from DataHub
        if self._config.evict_after_query:
            await self._evict(data_hub, query_id)

        return {
            "query_id": query_id,
            "ensemble_result": ensemble_result,
            "individual_results": all_results,
            "model_count": len(all_results),
        }

    async def _execute_phase(
        self,
        plan: ExecutionPlan,
        modalities: list[str],
        query_id: str,
        data_hub_url: str,
        window_length: int,
        timeout: float,
    ) -> list[dict[str, Any]]:
        """Execute all modalities in a phase concurrently."""
        tasks = []
        for modality in modalities:
            ensemble = plan.modality_ensembles.get(modality)
            if ensemble is None:
                continue
            tasks.append(
                self._execute_modality(
                    ensemble, query_id, data_hub_url, window_length, timeout
                )
            )

        if not tasks:
            return []

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("Phase execution timed out")
            return []

        flat: list[dict[str, Any]] = []
        for r in results:
            if isinstance(r, list):
                flat.extend(r)
            elif isinstance(r, Exception):
                logger.warning(f"Modality execution failed: {r}")
        return flat

    async def _execute_modality(
        self,
        ensemble: ModalityEnsemble,
        query_id: str,
        data_hub_url: str,
        window_length: int,
        timeout: float,
    ) -> list[dict[str, Any]]:
        """Execute preprocessing + inference for a single modality."""
        data_key = ensemble.modality

        # Step 1: Preprocessing
        if ensemble.preprocessor:
            preproc = ensemble.preprocessor
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(
                        preproc.service_url,
                        json={
                            "query_id": query_id,
                            "modality": ensemble.modality,
                            "data_key": data_key,
                            "output_data_key": preproc.output_data_key,
                            "data_hub_url": data_hub_url,
                            "window_length": window_length,
                        },
                    )
                    if resp.status_code == 200:
                        data_key = preproc.output_data_key
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                logger.warning(f"Preprocessor {preproc.service_url} failed: {e}")

        # Step 2: Dispatch inference (parallel)
        active_members = ensemble.get_active_members()
        if not active_members:
            return []

        async def call_inference(member: Any) -> dict[str, Any] | None:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(
                        member.inference_url,
                        json={
                            "query_id": query_id,
                            "inf_id": f"{query_id}-{member.instance_id}",
                            "modality": ensemble.modality,
                            "data_key": data_key,
                            "data_hub_url": data_hub_url,
                            "instance_id": member.instance_id,
                            "model_id": member.model_id,
                            "device_id": member.device_type,
                        },
                    )
                    if resp.status_code == 200:
                        return resp.json()
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                logger.warning(f"Inference {member.inference_url} failed: {e}")
            return None

        inference_tasks = [call_inference(m) for m in active_members]
        raw_results = await asyncio.gather(*inference_tasks)
        return [r for r in raw_results if r is not None]

    async def _aggregate(
        self,
        aggregator_url: str,
        query_id: str,
        results: list[dict[str, Any]],
        timeout: float = 5.0,
    ) -> dict[str, float]:
        """Call aggregator service."""
        if not results:
            return {}

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    aggregator_url,
                    json={
                        "query_id": query_id,
                        "results": results,
                        "strategy": "confidence_weighted",
                    },
                )
                if resp.status_code == 200:
                    return resp.json().get("ensemble_predictions", {})
        except (httpx.TimeoutException, httpx.ConnectError):
            logger.warning("Aggregator unavailable, using fallback")

        # Fallback: simple average
        all_classes: set[str] = set()
        for r in results:
            all_classes.update(r.get("predictions", {}).keys())
        n = len(results)
        return (
            {
                cls: round(
                    sum(r.get("predictions", {}).get(cls, 0.0) for r in results) / n, 4
                )
                for cls in all_classes
            }
            if n > 0
            else {}
        )

    async def _evict(self, data_hub_url: str, query_id: str) -> None:
        """Evict query data from DataHub."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                await client.delete(f"{data_hub_url}/evict/{query_id}")
        except (httpx.TimeoutException, httpx.ConnectError):
            pass

    def _should_run_phase(
        self, phase: Any, previous_results: list[dict[str, Any]]
    ) -> bool:
        """Evaluate whether a conditional phase should run."""
        condition = phase.condition
        if condition is None:
            return True

        source_results = [
            r
            for r in previous_results
            if r.get("modality") in condition.source_modalities
        ]
        if not source_results:
            return True

        if condition.trigger == "confidence_below":
            avg_conf = sum(r.get("confidence", 0) for r in source_results) / len(
                source_results
            )
            return avg_conf < condition.threshold

        if condition.trigger == "agreement_below":
            top_preds = [
                next(iter(r.get("predictions", {})), "") for r in source_results
            ]
            if not top_preds:
                return True
            agreement = top_preds.count(top_preds[0]) / len(top_preds)
            return agreement < condition.threshold

        return True

    @staticmethod
    def _empty_response(query_id: str) -> dict[str, Any]:
        return {
            "query_id": query_id,
            "ensemble_result": {},
            "individual_results": [],
            "model_count": 0,
        }
