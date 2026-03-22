from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel

from rohe.models.contracts import MetricThreshold, ServiceContract
from rohe.models.metrics import CDMDefinition
from rohe.quality.evaluator import ExpressionEvaluator
from rohe.repositories.base import ContractRepository, MetricRepository

logger = logging.getLogger(__name__)


class ViolationEvent(BaseModel):
    """Event generated when a contract threshold is violated."""

    event_id: str
    timestamp: datetime
    contract_id: str
    tenant_id: str
    pipeline_id: str
    metric_name: str
    threshold_operator: str
    threshold_value: float
    actual_value: float
    severity: str  # "warning" or "critical"
    recommended_action: str


class ContractChecker:
    """Rule-based SLA checker that evaluates contracts against current metrics.

    Periodically called to check all active contracts. Generates ViolationEvent
    for each threshold breach.
    """

    def __init__(
        self,
        contract_repo: ContractRepository,
        metric_repo: MetricRepository,
        evaluator: ExpressionEvaluator,
    ) -> None:
        self._contract_repo = contract_repo
        self._metric_repo = metric_repo
        self._evaluator = evaluator

    def check_all_contracts(self) -> list[ViolationEvent]:
        """Check all active contracts and return violation events."""
        now = datetime.now(tz=timezone.utc)
        contracts = self._contract_repo.list_contracts(is_active=True)
        violations: list[ViolationEvent] = []

        for contract_data in contracts:
            try:
                contract = ServiceContract.model_validate(contract_data)
                if not contract.is_active(now):
                    continue
                contract_violations = self._check_contract(contract)
                violations.extend(contract_violations)
            except Exception:
                logger.exception(f"Error checking contract {contract_data.get('contract_id', '?')}")

        if violations:
            logger.warning(f"Found {len(violations)} SLA violations across {len(contracts)} contracts")
        return violations

    def _check_contract(self, contract: ServiceContract) -> list[ViolationEvent]:
        """Check a single contract against current metrics."""
        violations: list[ViolationEvent] = []

        # Check builtin metric thresholds
        if contract.quality_slo.builtin_metrics:
            for metric_name, threshold in contract.quality_slo.builtin_metrics.items():
                violation = self._check_threshold(
                    contract, metric_name, threshold
                )
                if violation is not None:
                    violations.append(violation)

        # Check CDM thresholds
        if contract.quality_slo.cdm_thresholds:
            for cdm_name, threshold in contract.quality_slo.cdm_thresholds.items():
                violation = self._check_cdm_threshold(
                    contract, cdm_name, threshold
                )
                if violation is not None:
                    violations.append(violation)

        return violations

    def _check_threshold(
        self,
        contract: ServiceContract,
        metric_name: str,
        threshold: MetricThreshold,
    ) -> ViolationEvent | None:
        """Check a builtin metric threshold."""
        metrics = self._metric_repo.query_metrics(
            filters={"pipeline_id": contract.pipeline_id, "name": metric_name},
            limit=1000,
        )
        if not metrics:
            return None

        values = [float(m["value"]) for m in metrics if "value" in m]
        if not values:
            return None

        actual_value = sum(values) / len(values)

        if threshold.is_violated(actual_value):
            return self._create_violation(contract, metric_name, threshold, actual_value)
        return None

    def _check_cdm_threshold(
        self,
        contract: ServiceContract,
        cdm_name: str,
        threshold: MetricThreshold,
    ) -> ViolationEvent | None:
        """Check a CDM threshold by evaluating its expression tree."""
        cdm = self._contract_repo.get_cdm(cdm_name)
        if cdm is None:
            logger.warning(f"CDM '{cdm_name}' referenced in contract '{contract.contract_id}' not found")
            return None

        cdm_def = CDMDefinition.model_validate(cdm)
        self._evaluator.register_cdm(cdm_def)

        metrics = self._metric_repo.query_metrics(
            filters={"pipeline_id": contract.pipeline_id},
            limit=10000,
        )

        try:
            actual_value = self._evaluator.evaluate(cdm_def.expression, metrics)
        except Exception:
            logger.exception(f"Error evaluating CDM '{cdm_name}'")
            return None

        if threshold.is_violated(actual_value):
            return self._create_violation(contract, cdm_name, threshold, actual_value)
        return None

    @staticmethod
    def _create_violation(
        contract: ServiceContract,
        metric_name: str,
        threshold: MetricThreshold,
        actual_value: float,
    ) -> ViolationEvent:
        """Create a ViolationEvent."""
        return ViolationEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(tz=timezone.utc),
            contract_id=contract.contract_id,
            tenant_id=contract.tenant_id,
            pipeline_id=contract.pipeline_id,
            metric_name=metric_name,
            threshold_operator=threshold.operator,
            threshold_value=threshold.value,
            actual_value=actual_value,
            severity="critical" if abs(actual_value - threshold.value) > threshold.value * 0.1 else "warning",
            recommended_action=threshold.action_on_violation,
        )
