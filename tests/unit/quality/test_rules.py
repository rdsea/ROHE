from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from rohe.models.contracts import MetricThreshold, PerformanceSLO, QualitySLO, ServiceContract
from rohe.models.metrics import CDMDefinition, MetricExpression
from rohe.quality.evaluator import ExpressionEvaluator
from rohe.quality.rules import ContractChecker, ViolationEvent
from rohe.repositories.base import ContractRepository, MetricRepository


class MockContractRepo(ContractRepository):
    def __init__(self, contracts: list[dict[str, Any]] | None = None, cdms: dict[str, dict[str, Any]] | None = None):
        self._contracts = contracts or []
        self._cdms = cdms or {}

    def get_contract(self, contract_id: str) -> dict[str, Any] | None:
        for c in self._contracts:
            if c["contract_id"] == contract_id:
                return c
        return None

    def list_contracts(self, tenant_id: str | None = None, pipeline_id: str | None = None, is_active: bool | None = None) -> list[dict[str, Any]]:
        return self._contracts

    def create_contract(self, contract: dict[str, Any]) -> str:
        self._contracts.append(contract)
        return contract["contract_id"]

    def update_contract(self, contract_id: str, updates: dict[str, Any]) -> bool:
        return True

    def deactivate_contract(self, contract_id: str) -> bool:
        return True

    def get_cdm(self, cdm_name: str) -> dict[str, Any] | None:
        return self._cdms.get(cdm_name)

    def list_cdms(self) -> list[dict[str, Any]]:
        return list(self._cdms.values())

    def upsert_cdm(self, cdm: dict[str, Any]) -> None:
        self._cdms[cdm["name"]] = cdm


class MockMetricRepo(MetricRepository):
    def __init__(self, metrics: list[dict[str, Any]] | None = None):
        self._metrics = metrics or []

    def insert_metric(self, metric: dict[str, Any]) -> str:
        self._metrics.append(metric)
        return "inserted"

    def insert_metrics_batch(self, metrics: list[dict[str, Any]]) -> int:
        self._metrics.extend(metrics)
        return len(metrics)

    def query_metrics(self, filters: dict[str, Any] | None = None, time_from: datetime | None = None, time_to: datetime | None = None, limit: int = 10000) -> list[dict[str, Any]]:
        result = self._metrics
        if filters:
            result = [m for m in result if all(m.get(k) == v for k, v in filters.items())]
        return result[:limit]

    def aggregate_metrics(self, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return []

    def delete_metrics(self, filters: dict[str, Any]) -> int:
        return 0


def _make_contract(
    contract_id: str = "c-001",
    accuracy_threshold: float = 0.90,
    accuracy_operator: str = ">=",
    action: str = "alert",
    cdm_thresholds: dict[str, Any] | None = None,
) -> dict[str, Any]:
    quality_slo: dict[str, Any] = {
        "builtin_metrics": {
            "accuracy": {
                "operator": accuracy_operator,
                "value": accuracy_threshold,
                "action_on_violation": action,
            }
        },
    }
    if cdm_thresholds:
        quality_slo["cdm_thresholds"] = cdm_thresholds

    return {
        "contract_id": contract_id,
        "tenant_id": "t-001",
        "pipeline_id": "p-001",
        "effective_from": (datetime.now(tz=timezone.utc) - timedelta(days=1)).isoformat(),
        "effective_until": None,
        "performance_slo": {"response_time_p99_ms": 200.0},
        "quality_slo": quality_slo,
    }


class TestContractChecker:
    def test_no_violations_when_metrics_above_threshold(self):
        contract = _make_contract(accuracy_threshold=0.90)
        metrics = [
            {"pipeline_id": "p-001", "name": "accuracy", "value": 0.95},
            {"pipeline_id": "p-001", "name": "accuracy", "value": 0.93},
            {"pipeline_id": "p-001", "name": "accuracy", "value": 0.91},
        ]
        checker = ContractChecker(
            contract_repo=MockContractRepo(contracts=[contract]),
            metric_repo=MockMetricRepo(metrics=metrics),
            evaluator=ExpressionEvaluator(),
        )
        violations = checker.check_all_contracts()
        assert len(violations) == 0

    def test_violation_when_accuracy_below_threshold(self):
        contract = _make_contract(accuracy_threshold=0.90)
        metrics = [
            {"pipeline_id": "p-001", "name": "accuracy", "value": 0.85},
            {"pipeline_id": "p-001", "name": "accuracy", "value": 0.82},
            {"pipeline_id": "p-001", "name": "accuracy", "value": 0.88},
        ]
        checker = ContractChecker(
            contract_repo=MockContractRepo(contracts=[contract]),
            metric_repo=MockMetricRepo(metrics=metrics),
            evaluator=ExpressionEvaluator(),
        )
        violations = checker.check_all_contracts()
        assert len(violations) == 1
        v = violations[0]
        assert v.contract_id == "c-001"
        assert v.metric_name == "accuracy"
        assert v.actual_value < 0.90
        assert v.recommended_action == "alert"

    def test_violation_with_reroute_action(self):
        contract = _make_contract(accuracy_threshold=0.95, action="reroute")
        metrics = [{"pipeline_id": "p-001", "name": "accuracy", "value": 0.80}]
        checker = ContractChecker(
            contract_repo=MockContractRepo(contracts=[contract]),
            metric_repo=MockMetricRepo(metrics=metrics),
            evaluator=ExpressionEvaluator(),
        )
        violations = checker.check_all_contracts()
        assert len(violations) == 1
        assert violations[0].recommended_action == "reroute"

    def test_no_metrics_produces_no_violation(self):
        contract = _make_contract()
        checker = ContractChecker(
            contract_repo=MockContractRepo(contracts=[contract]),
            metric_repo=MockMetricRepo(metrics=[]),
            evaluator=ExpressionEvaluator(),
        )
        violations = checker.check_all_contracts()
        assert len(violations) == 0

    def test_expired_contract_skipped(self):
        contract = _make_contract()
        contract["effective_from"] = (datetime.now(tz=timezone.utc) + timedelta(days=30)).isoformat()
        metrics = [{"pipeline_id": "p-001", "name": "accuracy", "value": 0.50}]
        checker = ContractChecker(
            contract_repo=MockContractRepo(contracts=[contract]),
            metric_repo=MockMetricRepo(metrics=metrics),
            evaluator=ExpressionEvaluator(),
        )
        violations = checker.check_all_contracts()
        assert len(violations) == 0

    def test_multiple_contracts_checked(self):
        c1 = _make_contract(contract_id="c-001", accuracy_threshold=0.90)
        c2 = _make_contract(contract_id="c-002", accuracy_threshold=0.80)
        metrics = [{"pipeline_id": "p-001", "name": "accuracy", "value": 0.85}]
        checker = ContractChecker(
            contract_repo=MockContractRepo(contracts=[c1, c2]),
            metric_repo=MockMetricRepo(metrics=metrics),
            evaluator=ExpressionEvaluator(),
        )
        violations = checker.check_all_contracts()
        # c1 violated (0.85 < 0.90), c2 not violated (0.85 >= 0.80)
        assert len(violations) == 1
        assert violations[0].contract_id == "c-001"

    def test_cdm_threshold_violation(self):
        error_cdm = CDMDefinition(
            name="error_rate_human_car",
            metric_type="per_period",
            expression=MetricExpression(
                type="ratio",
                operands=[
                    MetricExpression(type="count", filters={"predicted": "human", "ground_truth": "car"}),
                    MetricExpression(type="count"),
                ],
            ),
            window="5m",
        )
        contract = _make_contract(
            cdm_thresholds={
                "error_rate_human_car": {
                    "operator": "<",
                    "value": 0.05,
                    "action_on_violation": "reroute",
                }
            }
        )
        # 2 out of 5 are misclassifications = 40% error rate, threshold is 5%
        metrics = [
            {"pipeline_id": "p-001", "name": "accuracy", "value": 0.95, "predicted": "car", "ground_truth": "car"},
            {"pipeline_id": "p-001", "name": "accuracy", "value": 0.80, "predicted": "human", "ground_truth": "car"},
            {"pipeline_id": "p-001", "name": "accuracy", "value": 0.92, "predicted": "car", "ground_truth": "car"},
            {"pipeline_id": "p-001", "name": "accuracy", "value": 0.88, "predicted": "human", "ground_truth": "car"},
            {"pipeline_id": "p-001", "name": "accuracy", "value": 0.91, "predicted": "human", "ground_truth": "human"},
        ]
        checker = ContractChecker(
            contract_repo=MockContractRepo(
                contracts=[contract],
                cdms={"error_rate_human_car": error_cdm.model_dump()},
            ),
            metric_repo=MockMetricRepo(metrics=metrics),
            evaluator=ExpressionEvaluator(),
        )
        violations = checker.check_all_contracts()
        # builtin accuracy is fine (avg > 0.90), but CDM error rate = 2/5 = 0.4 > 0.05
        cdm_violations = [v for v in violations if v.metric_name == "error_rate_human_car"]
        assert len(cdm_violations) == 1
        assert cdm_violations[0].recommended_action == "reroute"
        assert cdm_violations[0].actual_value == pytest.approx(0.4)

    def test_cdm_not_found_logs_warning(self):
        contract = _make_contract(
            cdm_thresholds={"nonexistent_cdm": {"operator": "<", "value": 0.1, "action_on_violation": "alert"}}
        )
        checker = ContractChecker(
            contract_repo=MockContractRepo(contracts=[contract], cdms={}),
            metric_repo=MockMetricRepo(metrics=[{"pipeline_id": "p-001"}]),
            evaluator=ExpressionEvaluator(),
        )
        violations = checker.check_all_contracts()
        # Should not crash, just skip the missing CDM
        cdm_violations = [v for v in violations if v.metric_name == "nonexistent_cdm"]
        assert len(cdm_violations) == 0

    def test_metrics_from_wrong_pipeline_ignored(self):
        contract = _make_contract(accuracy_threshold=0.90)
        metrics = [
            {"pipeline_id": "other-pipeline", "name": "accuracy", "value": 0.50},
        ]
        checker = ContractChecker(
            contract_repo=MockContractRepo(contracts=[contract]),
            metric_repo=MockMetricRepo(metrics=metrics),
            evaluator=ExpressionEvaluator(),
        )
        violations = checker.check_all_contracts()
        assert len(violations) == 0

    def test_violation_event_fields(self):
        contract = _make_contract(accuracy_threshold=0.95, accuracy_operator=">=")
        metrics = [{"pipeline_id": "p-001", "name": "accuracy", "value": 0.80}]
        checker = ContractChecker(
            contract_repo=MockContractRepo(contracts=[contract]),
            metric_repo=MockMetricRepo(metrics=metrics),
            evaluator=ExpressionEvaluator(),
        )
        violations = checker.check_all_contracts()
        assert len(violations) == 1
        v = violations[0]
        assert v.event_id  # not empty
        assert v.timestamp is not None
        assert v.contract_id == "c-001"
        assert v.tenant_id == "t-001"
        assert v.pipeline_id == "p-001"
        assert v.threshold_operator == ">="
        assert v.threshold_value == 0.95
        assert v.severity in ("warning", "critical")

    def test_less_than_operator(self):
        contract_data = _make_contract()
        contract_data["quality_slo"]["builtin_metrics"] = {
            "latency_ms": {"operator": "<", "value": 100.0, "action_on_violation": "degrade"}
        }
        metrics = [{"pipeline_id": "p-001", "name": "latency_ms", "value": 150.0}]
        checker = ContractChecker(
            contract_repo=MockContractRepo(contracts=[contract_data]),
            metric_repo=MockMetricRepo(metrics=metrics),
            evaluator=ExpressionEvaluator(),
        )
        violations = checker.check_all_contracts()
        assert len(violations) == 1
        assert violations[0].recommended_action == "degrade"
