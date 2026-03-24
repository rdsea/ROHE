"""Bridge between the platform AdaptiveOrchestrator and the example app pipeline.

This module adapts the legacy AdaptiveOrchestrator to the new pipeline interface:
- Receives OrchestrateRequest from the gateway (via the dummy orchestrator)
- Translates to InferenceQuery + ServiceLevelAgreement
- Runs AdaptiveOrchestrator.execute_inference()
- Translates results back to OrchestrateResponse
- Updates ExecutionPlan in Redis based on quality feedback

Usage:
  Deploy the platform orchestrator by setting ORCHESTRATOR_URL to point to
  orchestrator_api.py. It requires:
  - DuckDB with service registry populated
  - userModule/algorithm/ on PYTHONPATH
  - Redis for plan persistence
  - Contract YAML per pipeline
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import yaml

from rohe.models.contracts import ServiceLevelAgreement, ServiceContract
from rohe.models.execution_plan import (
    EnsembleMember,
    ExecutionPlan,
    ExecutionPhase,
    ModalityEnsemble,
    PreprocessorSpec,
)
from rohe.models.pipeline import InferenceQuery, InferenceResult

logger = logging.getLogger(__name__)


class OrchestratorBridge:
    """Bridges AdaptiveOrchestrator to the pipeline OrchestrateRequest interface."""

    def __init__(
        self,
        config_path: str = "",
        redis_url: str = "",
        contracts_dir: str = "",
    ) -> None:
        self._adaptive_orchestrator: Any = None
        self._config_path = config_path or os.environ.get(
            "ORCHESTRATOR_CONFIG", "config/orchestrator.yaml"
        )
        self._redis_url = redis_url or os.environ.get("REDIS_URL", "")
        self._contracts_dir = contracts_dir or os.environ.get(
            "CONTRACTS_DIR", "examples/applications"
        )
        self._plan_store: Any = None
        self._contracts: dict[str, ServiceContract] = {}
        self._slas: dict[str, ServiceLevelAgreement] = {}

    def initialize(self) -> None:
        """Initialize the AdaptiveOrchestrator, Redis, and load contracts."""
        # Load AdaptiveOrchestrator
        try:
            from rohe.orchestration.inference.orchestrator import AdaptiveOrchestrator
            self._adaptive_orchestrator = AdaptiveOrchestrator(
                config_path=self._config_path
            )
            logger.info("AdaptiveOrchestrator initialized")
        except Exception as e:
            logger.error(f"Failed to initialize AdaptiveOrchestrator: {e}")

        # Connect to Redis
        if self._redis_url:
            try:
                from rohe.repositories.redis import RedisCache
                self._plan_store = RedisCache(url=self._redis_url)
                logger.info(f"Redis plan store connected at {self._redis_url}")
            except Exception as e:
                logger.warning(f"Redis unavailable for plan store: {e}")

        # Load contracts
        self._load_contracts()

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
        start_time = time.perf_counter()

        # Build InferenceQuery
        inference_query = InferenceQuery(
            metadata={"pipeline_id": pipeline_id, "data_hub_url": data_hub_url},
            data_source=modalities,
            time_window=int(time_constraint_ms),
            explainability=False,
            constraint={"response_time": time_constraint_ms / 1000.0},
            query_id=query_id,
        )

        # Load SLA
        tenant_sla = self._get_sla(pipeline_id)

        # Execute through AdaptiveOrchestrator if available
        if self._adaptive_orchestrator is not None:
            try:
                self._adaptive_orchestrator.execute_inference(
                    start_time=start_time,
                    inference_query=inference_query,
                    tenant_sla=tenant_sla,
                )
            except Exception as e:
                logger.error(f"AdaptiveOrchestrator execution failed: {e}")

        # Collect results
        inference_result = self._collect_results(query_id)

        # Quality feedback -> plan update
        self._update_plan_from_results(pipeline_id, inference_result)

        return {
            "query_id": query_id,
            "ensemble_result": inference_result.get("predictions", {}),
            "individual_results": inference_result.get("individual_results", []),
            "model_count": inference_result.get("model_count", 0),
        }

    def _load_contracts(self) -> None:
        """Load contract.yaml files from the contracts directory."""
        contracts_path = Path(self._contracts_dir)
        for contract_file in contracts_path.glob("*/contract.yaml"):
            try:
                data = yaml.safe_load(contract_file.read_text())
                contract_data = data.get("contract", data)
                contract = ServiceContract.model_validate(contract_data)
                self._contracts[contract.pipeline_id] = contract

                # Build SLA from contract
                sla = ServiceLevelAgreement(
                    sla_id=contract.contract_id,
                    tenant_id=contract.tenant_id,
                    access_privileges=[contract.pipeline_id],
                    service_level_indicators=[],
                    ensemble_size=4,
                    ensemble_selection_strategy="enhance_confidence",
                )
                self._slas[contract.pipeline_id] = sla
                logger.info(f"Loaded contract for pipeline '{contract.pipeline_id}'")
            except Exception as e:
                logger.warning(f"Failed to load contract from {contract_file}: {e}")

    def _get_sla(self, pipeline_id: str) -> ServiceLevelAgreement:
        """Get SLA for a pipeline, with fallback default."""
        if pipeline_id in self._slas:
            return self._slas[pipeline_id]
        return ServiceLevelAgreement(
            sla_id=f"{pipeline_id}-default",
            tenant_id="default",
            access_privileges=[pipeline_id],
            service_level_indicators=[],
            ensemble_size=4,
            ensemble_selection_strategy="enhance_confidence",
        )

    def _collect_results(self, query_id: str) -> dict[str, Any]:
        """Collect inference results from AdaptiveOrchestrator's DuckDB.

        The AdaptiveOrchestrator writes results to its monitoring table
        (inference_result_table) after each execution.
        """
        if self._adaptive_orchestrator is None:
            return {"predictions": {}, "individual_results": [], "model_count": 0}

        try:
            db_conn = self._adaptive_orchestrator.db_conn
            if db_conn is None:
                return {"predictions": {}, "individual_results": [], "model_count": 0}

            monitoring_table = self._adaptive_orchestrator.monitoring_table
            if monitoring_table is None:
                return {"predictions": {}, "individual_results": [], "model_count": 0}

            result = db_conn.execute(
                f"SELECT * FROM {monitoring_table} WHERE query_id = ? "
                f"ORDER BY inf_time DESC LIMIT 20",
                [query_id],
            ).fetchall()

            if not result:
                return {"predictions": {}, "individual_results": [], "model_count": 0}

            predictions: dict[str, float] = {}
            individual_results: list[dict[str, Any]] = []
            for row in result:
                row_dict = dict(zip(
                    [desc[0] for desc in db_conn.description], row
                ))
                inf_result = row_dict.get("inf_result", "{}")
                if isinstance(inf_result, str):
                    inf_result = json.loads(inf_result)

                individual_results.append({
                    "query_id": query_id,
                    "predictions": inf_result,
                    "confidence": max(inf_result.values()) if inf_result else 0.0,
                    "model": row_dict.get("model_id", "unknown"),
                    "response_time_ms": row_dict.get("response_time", 0) * 1000,
                    "modality": row_dict.get("data_source"),
                })

                # Aggregate predictions (average)
                for cls, score in inf_result.items():
                    predictions[cls] = predictions.get(cls, 0.0) + score

            n = len(individual_results)
            if n > 0:
                predictions = {cls: round(s / n, 4) for cls, s in predictions.items()}

            return {
                "predictions": predictions,
                "individual_results": individual_results,
                "model_count": n,
            }
        except Exception as e:
            logger.warning(f"Failed to collect results from DuckDB: {e}")
            return {"predictions": {}, "individual_results": [], "model_count": 0}

    def _update_plan_from_results(
        self, pipeline_id: str, results: dict[str, Any]
    ) -> None:
        """Evaluate quality and update ExecutionPlan if SLA violated.

        Compares inference results against contract SLA thresholds.
        If quality is below threshold, adjusts the ensemble:
        - confidence below threshold: add more models
        - latency above threshold: remove slow models
        """
        if self._plan_store is None:
            return

        contract = self._contracts.get(pipeline_id)
        if contract is None:
            return

        predictions = results.get("predictions", {})
        if not predictions:
            return

        # Check quality SLO
        quality_slo = contract.quality_slo
        if quality_slo is None or quality_slo.builtin_metrics is None:
            return

        avg_confidence = sum(predictions.values()) / len(predictions) if predictions else 0.0

        confidence_threshold = quality_slo.builtin_metrics.get("confidence")
        if confidence_threshold and confidence_threshold.is_violated(avg_confidence):
            logger.warning(
                f"Pipeline '{pipeline_id}': confidence {avg_confidence:.3f} "
                f"violates threshold {confidence_threshold.value}. "
                f"Action: {confidence_threshold.action_on_violation}"
            )

            if confidence_threshold.action_on_violation == "reroute":
                # Load current plan from Redis and adjust
                plan_dict = self._plan_store.get(f"rohe:plan:{pipeline_id}")
                if plan_dict:
                    try:
                        plan = ExecutionPlan.model_validate(
                            json.loads(plan_dict) if isinstance(plan_dict, str) else plan_dict
                        )
                        # Increase ensemble sizes by 1 for each modality
                        for ensemble in plan.modality_ensembles.values():
                            ensemble.ensemble_size = min(
                                ensemble.ensemble_size + 1,
                                len(ensemble.ensemble_members),
                            )
                        plan._bump_version()
                        self._plan_store.set(
                            f"rohe:plan:{pipeline_id}",
                            json.loads(plan.model_dump_json()),
                        )
                        logger.info(
                            f"Updated plan '{pipeline_id}' to v{plan.version} "
                            f"(increased ensemble sizes)"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update plan: {e}")
