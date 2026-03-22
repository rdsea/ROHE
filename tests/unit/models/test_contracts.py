from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from rohe.models.contracts import MetricThreshold, PerformanceSLO, QualitySLO, ServiceContract


class TestMetricThreshold:
    def test_gt_not_violated(self):
        t = MetricThreshold(operator=">=", value=0.95)
        assert not t.is_violated(0.96)
        assert not t.is_violated(0.95)

    def test_gt_violated(self):
        t = MetricThreshold(operator=">=", value=0.95)
        assert t.is_violated(0.94)

    def test_lt_not_violated(self):
        t = MetricThreshold(operator="<", value=100.0)
        assert not t.is_violated(50.0)

    def test_lt_violated(self):
        t = MetricThreshold(operator="<", value=100.0)
        assert t.is_violated(100.0)
        assert t.is_violated(150.0)

    def test_eq_operators(self):
        t_eq = MetricThreshold(operator="==", value=1.0)
        assert not t_eq.is_violated(1.0)
        assert t_eq.is_violated(0.99)

        t_neq = MetricThreshold(operator="!=", value=0.0)
        assert not t_neq.is_violated(1.0)
        assert t_neq.is_violated(0.0)

    def test_lte_operator(self):
        t = MetricThreshold(operator="<=", value=200.0, window="5m")
        assert not t.is_violated(200.0)
        assert not t.is_violated(150.0)
        assert t.is_violated(201.0)

    def test_default_action(self):
        t = MetricThreshold(operator=">=", value=0.9)
        assert t.action_on_violation == "alert"

    def test_custom_action(self):
        t = MetricThreshold(operator=">=", value=0.9, action_on_violation="reroute")
        assert t.action_on_violation == "reroute"

    def test_frozen(self):
        t = MetricThreshold(operator=">=", value=0.9)
        with pytest.raises(Exception):
            t.value = 0.8  # type: ignore[misc]


class TestServiceContract:
    def _make_contract(self, **kwargs):
        defaults = {
            "contract_id": "c-001",
            "tenant_id": "t-001",
            "pipeline_id": "p-001",
            "effective_from": datetime(2024, 1, 1),
            "performance_slo": PerformanceSLO(response_time_p99_ms=200.0),
            "quality_slo": QualitySLO(
                builtin_metrics={"accuracy": MetricThreshold(operator=">=", value=0.9)}
            ),
        }
        defaults.update(kwargs)
        return ServiceContract(**defaults)

    def test_active_contract(self):
        c = self._make_contract()
        assert c.is_active(datetime(2024, 6, 1))

    def test_not_yet_active(self):
        c = self._make_contract(effective_from=datetime(2025, 1, 1))
        assert not c.is_active(datetime(2024, 6, 1))

    def test_expired_contract(self):
        c = self._make_contract(
            effective_from=datetime(2024, 1, 1),
            effective_until=datetime(2024, 6, 1),
        )
        assert not c.is_active(datetime(2024, 7, 1))

    def test_no_expiry(self):
        c = self._make_contract()
        assert c.effective_until is None
        assert c.is_active(datetime(2030, 1, 1))

    def test_serialization(self):
        c = self._make_contract()
        json_str = c.model_dump_json()
        restored = ServiceContract.model_validate_json(json_str)
        assert restored.contract_id == c.contract_id
        assert restored.performance_slo.response_time_p99_ms == 200.0
