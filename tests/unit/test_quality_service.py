"""Tests for Tier 2 anomaly detection and QualityService remediation."""
from __future__ import annotations

import pytest

from rohe.quality.anomaly import AnomalyDetector, MetricAnomalyChecker
from rohe.quality.service import QualityService, RemediationAction
from rohe.quality.rules import ViolationEvent
from rohe.models.execution_plan import (
    EnsembleMember, ExecutionPlan, ExecutionPhase, ModalityEnsemble,
)


try:
    import sklearn
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


@pytest.mark.skipif(not HAS_SKLEARN, reason="scikit-learn required")
class TestAnomalyDetector:
    def test_detect_normal_data(self) -> None:
        detector = AnomalyDetector(method="isolation_forest", contamination=0.1)
        values = [1.0, 1.1, 0.9, 1.0, 1.05, 0.95, 1.02, 0.98, 1.01, 0.99]
        anomalies = detector.detect(values)
        assert len(anomalies) == 10
        # Most should be normal
        assert sum(anomalies) <= 3

    def test_scores_separate_outliers(self) -> None:
        import random
        rng = random.Random(42)
        detector = AnomalyDetector(method="isolation_forest", contamination=0.1)
        normal = [rng.gauss(10.0, 1.0) for _ in range(50)]
        outliers = [500.0, 600.0, 700.0]
        values = normal + outliers
        scores = detector.fit_score(values)
        # Outlier scores should be lower (more negative) than normal scores
        normal_mean_score = sum(scores[:50]) / 50
        outlier_mean_score = sum(scores[-3:]) / 3
        assert outlier_mean_score < normal_mean_score, (
            f"Outlier scores ({outlier_mean_score:.4f}) should be lower "
            f"than normal scores ({normal_mean_score:.4f})"
        )

    def test_anomaly_rate(self) -> None:
        detector = AnomalyDetector(method="isolation_forest", contamination=0.1)
        values = [1.0] * 18 + [100.0, 200.0]
        rate = detector.anomaly_rate(values)
        assert 0.0 <= rate <= 1.0

    def test_too_few_values(self) -> None:
        detector = AnomalyDetector()
        assert detector.detect([1.0, 2.0]) == [False, False]
        assert detector.anomaly_rate([1.0]) == 0.0

    def test_lof_method(self) -> None:
        detector = AnomalyDetector(method="lof", contamination=0.1)
        values = [1.0] * 20 + [100.0]
        anomalies = detector.detect(values)
        assert len(anomalies) == 21

    def test_unknown_method_raises(self) -> None:
        detector = AnomalyDetector(method="unknown")
        with pytest.raises(ValueError, match="Unknown method"):
            detector.detect([1.0] * 10)


@pytest.mark.skipif(not HAS_SKLEARN, reason="scikit-learn required")
class TestMetricAnomalyChecker:
    def test_check_multiple_metrics(self) -> None:
        checker = MetricAnomalyChecker(contamination=0.1)
        results = checker.check_metrics({
            "latency": [10.0] * 20 + [500.0],
            "accuracy": [0.9] * 20,
        })
        assert "latency" in results
        assert "accuracy" in results
        assert results["latency"]["total"] == 21
        assert results["accuracy"]["total"] == 20

    def test_empty_metrics(self) -> None:
        checker = MetricAnomalyChecker()
        results = checker.check_metrics({"empty": []})
        assert results == {}


def _make_plan(n_active: int = 3, n_inactive: int = 1) -> ExecutionPlan:
    members = []
    for i in range(n_active):
        members.append(EnsembleMember(
            service_id=f"model_{i}", instance_id=f"model_{i}-001",
            inference_url=f"http://model-{i}:8000/inference",
            model_id=f"model_{i}", device_type="cpu",
            weight=1.0 - i * 0.1, is_active=True,
        ))
    for i in range(n_inactive):
        members.append(EnsembleMember(
            service_id=f"inactive_{i}", instance_id=f"inactive_{i}-001",
            inference_url=f"http://inactive-{i}:8000/inference",
            model_id=f"inactive_{i}", device_type="cpu",
            weight=0.5, is_active=False,
        ))
    return ExecutionPlan(
        pipeline_id="test",
        modality_ensembles={
            "default": ModalityEnsemble(
                modality="default",
                ensemble_members=members,
                ensemble_size=n_active,
            ),
        },
        execution_phases=[ExecutionPhase(phase_id=0, modalities=["default"])],
    )


def _make_violation(action: str = "reroute", metric: str = "confidence") -> ViolationEvent:
    from datetime import datetime, timezone
    return ViolationEvent(
        event_id="test-001",
        timestamp=datetime.now(timezone.utc),
        contract_id="contract-001",
        tenant_id="tenant-001",
        pipeline_id="test",
        metric_name=metric,
        threshold_operator=">=",
        threshold_value=0.80,
        actual_value=0.65,
        severity="critical",
        recommended_action=action,
    )


class TestQualityServiceRemediation:
    def test_increase_ensemble_activates_inactive(self) -> None:
        plan = _make_plan(n_active=2, n_inactive=1)
        service = QualityService()
        action = service._strategy_increase_ensemble(plan, _make_violation("reroute"))
        assert action is not None
        assert action.strategy == "increase_ensemble"
        assert "activated" in action.description
        # Inactive member should now be active
        active = plan.modality_ensembles["default"].get_active_members()
        assert len(active) == 3

    def test_increase_ensemble_no_inactive(self) -> None:
        plan = _make_plan(n_active=3, n_inactive=0)
        plan.modality_ensembles["default"].ensemble_size = 2
        service = QualityService()
        action = service._strategy_increase_ensemble(plan, _make_violation("reroute"))
        assert action is not None
        assert "increased ensemble_size" in action.description
        assert plan.modality_ensembles["default"].ensemble_size == 3

    def test_remove_slow_deactivates_lowest_weight(self) -> None:
        plan = _make_plan(n_active=3, n_inactive=0)
        service = QualityService()
        action = service._strategy_remove_slow_models(plan, _make_violation("degrade"))
        assert action is not None
        assert action.strategy == "remove_slow_models"
        assert "deactivated" in action.description
        active = plan.modality_ensembles["default"].get_active_members()
        assert len(active) == 2

    def test_remove_slow_keeps_minimum_one(self) -> None:
        plan = _make_plan(n_active=1, n_inactive=0)
        service = QualityService()
        action = service._strategy_remove_slow_models(plan, _make_violation("degrade"))
        assert action is None  # Can't deactivate the last model

    def test_alert_action_returns_none(self) -> None:
        plan = _make_plan()
        service = QualityService()
        action = service._remediate(plan, _make_violation("alert"))
        assert action is None

    def test_action_log(self) -> None:
        plan = _make_plan(n_active=2, n_inactive=1)
        service = QualityService()
        service._strategy_increase_ensemble(plan, _make_violation())
        # The service's evaluate_and_remediate would add to log
        # For unit test, verify log structure
        assert service.get_action_log() == []  # Direct calls don't go through evaluate
