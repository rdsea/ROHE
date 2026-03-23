"""Quality Service: periodic SLA evaluation with auto-remediation.

Combines Tier 1 (rule-based thresholds) and Tier 2 (statistical anomaly
detection) to evaluate pipeline quality. When violations are detected,
it automatically adjusts the ExecutionPlan via remediation strategies.

The service runs as a periodic background task in the orchestrator or
as a standalone service.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from rohe.models.contracts import MetricThreshold, ServiceContract
from rohe.models.execution_plan import EnsembleMember, ExecutionPlan
from rohe.quality.anomaly import MetricAnomalyChecker
from rohe.quality.rules import ContractChecker, ViolationEvent

logger = logging.getLogger(__name__)


class RemediationAction(BaseModel):
    """A remediation action applied to an ExecutionPlan."""

    timestamp: datetime
    pipeline_id: str
    trigger: str  # violation metric name
    strategy: str  # remediation strategy name
    description: str
    plan_version_before: int
    plan_version_after: int


class QualityService:
    """Periodic quality evaluation with auto-remediation.

    Combines:
    - Tier 1: ContractChecker (rule-based threshold evaluation)
    - Tier 2: MetricAnomalyChecker (statistical anomaly detection)
    - Remediation: adjust ExecutionPlan when violations detected

    Usage:
        service = QualityService(
            contract_checker=checker,
            plan_store=redis_cache,
        )
        actions = service.evaluate_and_remediate()
    """

    def __init__(
        self,
        contract_checker: ContractChecker | None = None,
        anomaly_checker: MetricAnomalyChecker | None = None,
        plan_store: Any = None,  # RedisCache
        max_remediation_per_cycle: int = 3,
    ) -> None:
        self._contract_checker = contract_checker
        self._anomaly_checker = anomaly_checker or MetricAnomalyChecker()
        self._plan_store = plan_store
        self._max_remediation = max_remediation_per_cycle
        self._action_log: list[RemediationAction] = []

    def evaluate_and_remediate(self) -> list[RemediationAction]:
        """Run one evaluation cycle: check contracts, detect anomalies, remediate.

        Returns list of remediation actions taken.
        """
        actions: list[RemediationAction] = []

        # Tier 1: Rule-based contract checking
        violations: list[ViolationEvent] = []
        if self._contract_checker:
            violations = self._contract_checker.check_all_contracts()

        # Group violations by pipeline and apply remediation
        violations_by_pipeline: dict[str, list[ViolationEvent]] = {}
        for v in violations:
            violations_by_pipeline.setdefault(v.pipeline_id, []).append(v)

        for pipeline_id, pipeline_violations in violations_by_pipeline.items():
            if len(actions) >= self._max_remediation:
                logger.warning(f"Max remediation limit ({self._max_remediation}) reached, skipping remaining")
                break

            plan = self._load_plan(pipeline_id)
            if plan is None:
                continue

            for violation in pipeline_violations:
                action = self._remediate(plan, violation)
                if action:
                    actions.append(action)
                    self._save_plan(plan)

        self._action_log.extend(actions)
        return actions

    def evaluate_metrics(
        self,
        pipeline_id: str,
        metrics_by_name: dict[str, list[float]],
    ) -> dict[str, Any]:
        """Run Tier 2 anomaly detection on a set of metrics.

        Returns anomaly analysis results per metric.
        """
        return self._anomaly_checker.check_metrics(metrics_by_name)

    def get_action_log(self) -> list[RemediationAction]:
        """Return all remediation actions taken since startup."""
        return list(self._action_log)

    def _remediate(
        self,
        plan: ExecutionPlan,
        violation: ViolationEvent,
    ) -> RemediationAction | None:
        """Apply remediation strategy based on the violation's recommended action."""
        action = violation.recommended_action
        version_before = plan.version

        if action == "reroute":
            return self._strategy_increase_ensemble(plan, violation)
        if action == "degrade":
            return self._strategy_remove_slow_models(plan, violation)
        if action == "alert":
            logger.warning(
                f"SLA violation alert: {violation.pipeline_id}/{violation.metric_name} "
                f"= {violation.actual_value} (threshold: {violation.threshold_operator} "
                f"{violation.threshold_value})"
            )
            return None
        if action == "reject":
            logger.error(
                f"SLA violation REJECT: {violation.pipeline_id}/{violation.metric_name} "
                f"= {violation.actual_value} -- pipeline should be disabled"
            )
            return None

        return None

    def _strategy_increase_ensemble(
        self,
        plan: ExecutionPlan,
        violation: ViolationEvent,
    ) -> RemediationAction | None:
        """Remediation: increase ensemble size to improve accuracy.

        When accuracy/confidence is below threshold, activate more models
        or increase ensemble_size to get more diverse predictions.
        """
        version_before = plan.version
        changes: list[str] = []

        for modality, ensemble in plan.modality_ensembles.items():
            inactive = [m for m in ensemble.ensemble_members if not m.is_active]
            if inactive:
                # Activate one inactive member
                member_to_activate = inactive[0]
                plan.set_member_active(modality, member_to_activate.instance_id, is_active=True)
                changes.append(f"activated {member_to_activate.service_id} in {modality}")
            elif ensemble.ensemble_size < len(ensemble.ensemble_members):
                # Increase ensemble_size
                ensemble.ensemble_size = min(
                    ensemble.ensemble_size + 1,
                    len(ensemble.ensemble_members),
                )
                plan._bump_version()
                changes.append(f"increased ensemble_size to {ensemble.ensemble_size} in {modality}")

        if not changes:
            return None

        return RemediationAction(
            timestamp=datetime.now(timezone.utc),
            pipeline_id=plan.pipeline_id,
            trigger=violation.metric_name,
            strategy="increase_ensemble",
            description="; ".join(changes),
            plan_version_before=version_before,
            plan_version_after=plan.version,
        )

    def _strategy_remove_slow_models(
        self,
        plan: ExecutionPlan,
        violation: ViolationEvent,
    ) -> RemediationAction | None:
        """Remediation: deactivate slowest models to reduce latency.

        When latency exceeds threshold, deactivate the model with the
        highest weight (proxy for slowest/heaviest). Keep at least 1 active.
        """
        version_before = plan.version
        changes: list[str] = []

        for modality, ensemble in plan.modality_ensembles.items():
            active = ensemble.get_active_members()
            if len(active) <= 1:
                continue

            # Find lowest-weight member (proxy for least valuable)
            lowest = min(active, key=lambda m: m.weight)
            plan.set_member_active(modality, lowest.instance_id, is_active=False)
            changes.append(f"deactivated {lowest.service_id} in {modality}")

        if not changes:
            return None

        return RemediationAction(
            timestamp=datetime.now(timezone.utc),
            pipeline_id=plan.pipeline_id,
            trigger=violation.metric_name,
            strategy="remove_slow_models",
            description="; ".join(changes),
            plan_version_before=version_before,
            plan_version_after=plan.version,
        )

    def _load_plan(self, pipeline_id: str) -> ExecutionPlan | None:
        """Load ExecutionPlan from Redis."""
        if self._plan_store is None:
            return None
        try:
            data = self._plan_store.get(f"rohe:plan:{pipeline_id}")
            if data:
                return ExecutionPlan.model_validate(data)
        except Exception as e:
            logger.warning(f"Failed to load plan '{pipeline_id}': {e}")
        return None

    def _save_plan(self, plan: ExecutionPlan) -> None:
        """Save updated ExecutionPlan to Redis."""
        if self._plan_store is None:
            return
        try:
            self._plan_store.set(
                f"rohe:plan:{plan.pipeline_id}",
                json.loads(plan.model_dump_json()),
            )
            self._plan_store.publish(
                "rohe:plan:updates",
                {"pipeline_id": plan.pipeline_id, "version": plan.version},
            )
            logger.info(f"Saved remediated plan '{plan.pipeline_id}' v{plan.version}")
        except Exception as e:
            logger.warning(f"Failed to save plan '{plan.pipeline_id}': {e}")
