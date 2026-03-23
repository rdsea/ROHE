"""Bridge between the platform AdaptiveOrchestrator and the example app pipeline.

This module adapts the legacy AdaptiveOrchestrator to the new pipeline interface:
- Receives OrchestrateRequest from the gateway (via the dummy orchestrator)
- Translates to InferenceQuery + ServiceLevelAgreement
- Runs AdaptiveOrchestrator.execute_inference()
- Translates results back to OrchestrateResponse
- Updates ExecutionPlan in Redis based on quality feedback

Usage:
  The platform orchestrator service uses this bridge instead of the dummy
  orchestrator. Deploy it as a replacement by setting ORCHESTRATOR_URL
  to point to this service.

  This bridge requires:
  - DuckDB with service registry populated
  - userModule/algorithm/ on PYTHONPATH
  - Redis for plan persistence
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

from rohe.models.contracts import ServiceLevelAgreement
from rohe.models.execution_plan import EnsembleMember, ExecutionPlan, ModalityEnsemble
from rohe.models.pipeline import InferenceQuery, InferenceResult

logger = logging.getLogger(__name__)


class OrchestratorBridge:
    """Bridges AdaptiveOrchestrator to the pipeline OrchestrateRequest interface.

    Lifecycle:
      1. On startup: load AdaptiveOrchestrator from config
      2. On each request: translate, execute, translate back
      3. After each execution: evaluate quality, update ExecutionPlan if needed
    """

    def __init__(
        self,
        config_path: str = "",
        redis_url: str = "",
    ) -> None:
        self._adaptive_orchestrator: Any = None
        self._config_path = config_path or os.environ.get(
            "ORCHESTRATOR_CONFIG", "config/orchestrator.yaml"
        )
        self._redis_url = redis_url or os.environ.get("REDIS_URL", "")
        self._plan_store: Any = None

    def initialize(self) -> None:
        """Initialize the AdaptiveOrchestrator and Redis plan store."""
        try:
            from rohe.orchestration.inference.orchestrator import AdaptiveOrchestrator
            self._adaptive_orchestrator = AdaptiveOrchestrator(
                config_path=self._config_path
            )
            logger.info("AdaptiveOrchestrator initialized")
        except Exception as e:
            logger.error(f"Failed to initialize AdaptiveOrchestrator: {e}")
            raise

        if self._redis_url:
            try:
                from rohe.repositories.redis import RedisCache
                self._plan_store = RedisCache(url=self._redis_url)
                logger.info(f"Redis plan store connected at {self._redis_url}")
            except Exception as e:
                logger.warning(f"Redis unavailable for plan store: {e}")

    def orchestrate(
        self,
        query_id: str,
        pipeline_id: str,
        modalities: list[str],
        time_constraint_ms: float,
        data_hub_url: str,
    ) -> dict[str, Any]:
        """Execute orchestration using AdaptiveOrchestrator.

        Returns dict matching OrchestrateResponse schema.
        """
        if self._adaptive_orchestrator is None:
            return {
                "query_id": query_id,
                "ensemble_result": {},
                "individual_results": [],
                "model_count": 0,
            }

        start_time = time.perf_counter()

        # Translate to legacy InferenceQuery
        inference_query = InferenceQuery(
            metadata={"pipeline_id": pipeline_id, "data_hub_url": data_hub_url},
            data_source=modalities,
            time_window=int(time_constraint_ms),
            explainability=False,
            constraint={"response_time": time_constraint_ms / 1000.0},
            query_id=query_id,
        )

        # Load SLA for this pipeline
        tenant_sla = self._load_sla(pipeline_id)

        # Execute through AdaptiveOrchestrator
        try:
            self._adaptive_orchestrator.execute_inference(
                start_time=start_time,
                inference_query=inference_query,
                tenant_sla=tenant_sla,
            )
        except Exception as e:
            logger.error(f"AdaptiveOrchestrator execution failed: {e}")
            return {
                "query_id": query_id,
                "ensemble_result": {},
                "individual_results": [],
                "model_count": 0,
            }

        # Collect results from the orchestrator's internal state
        # The AdaptiveOrchestrator stores results in DuckDB
        inference_result = self._collect_results(query_id)

        # Update ExecutionPlan based on quality feedback
        self._update_plan_from_results(pipeline_id, inference_result)

        return {
            "query_id": query_id,
            "ensemble_result": inference_result.get("predictions", {}),
            "individual_results": inference_result.get("individual_results", []),
            "model_count": inference_result.get("model_count", 0),
        }

    def _load_sla(self, pipeline_id: str) -> ServiceLevelAgreement:
        """Load SLA for a pipeline from the orchestrator's config."""
        # Default SLA -- in production, loaded from contract.yaml or DuckDB
        return ServiceLevelAgreement(
            sla_id=f"{pipeline_id}-sla",
            tenant_id="default",
            access_privileges=[pipeline_id],
            service_level_indicators=[],
            ensemble_size=4,
            ensemble_selection_strategy="enhance_confidence",
        )

    def _collect_results(self, query_id: str) -> dict[str, Any]:
        """Collect inference results from DuckDB after execution."""
        # The AdaptiveOrchestrator writes results to its monitoring table
        # This is a placeholder -- actual implementation reads from DuckDB
        return {
            "predictions": {},
            "individual_results": [],
            "model_count": 0,
        }

    def _update_plan_from_results(
        self, pipeline_id: str, results: dict[str, Any]
    ) -> None:
        """Evaluate quality and update ExecutionPlan if needed.

        This is where the platform orchestrator's intelligence feeds back
        into the ExecutionPlan. After each inference:
        1. Compare results against SLA thresholds
        2. If quality degraded: add higher-accuracy models to ensemble
        3. If latency exceeded: remove slow models, add faster ones
        4. Persist updated plan to Redis
        """
        if self._plan_store is None:
            return
        # Placeholder for quality-driven plan updates
        # The actual implementation would:
        # - Read current plan from Redis
        # - Compare inference quality to SLA
        # - Mutate ensemble (add/remove members)
        # - Write updated plan back to Redis
        logger.debug(f"Quality evaluation for {pipeline_id} (placeholder)")
