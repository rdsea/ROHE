from __future__ import annotations

import pytest

from rohe.models.metrics import CDMDefinition, ClassSpecificMetric, Metric, MetricExpression, RuntimePerformance


class TestMetricExpression:
    def test_leaf_node(self):
        expr = MetricExpression(type="count", filters={"predicted": "car"})
        assert expr.is_leaf()
        assert expr.references_cdm() == set()

    def test_composite_node(self):
        expr = MetricExpression(
            type="ratio",
            operands=[
                MetricExpression(type="count", filters={"predicted": "human", "ground_truth": "car"}),
                MetricExpression(type="count"),
            ],
        )
        assert not expr.is_leaf()
        assert expr.references_cdm() == set()

    def test_cdm_ref_tracking(self):
        expr = MetricExpression(
            type="sum",
            operands=[
                MetricExpression(type="cdm_ref", cdm_ref="error_rate_a"),
                MetricExpression(type="cdm_ref", cdm_ref="error_rate_b"),
            ],
        )
        assert expr.references_cdm() == {"error_rate_a", "error_rate_b"}

    def test_nested_cdm_ref(self):
        expr = MetricExpression(
            type="ratio",
            operands=[
                MetricExpression(
                    type="sum",
                    operands=[MetricExpression(type="cdm_ref", cdm_ref="inner_cdm")],
                ),
                MetricExpression(type="count"),
            ],
        )
        assert expr.references_cdm() == {"inner_cdm"}

    def test_frozen_model(self):
        expr = MetricExpression(type="count")
        with pytest.raises(Exception):
            expr.type = "sum"  # type: ignore[misc]


class TestCDMDefinition:
    def test_valid_per_period(self):
        cdm = CDMDefinition(
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
            description="Misclassification rate: human predicted as car",
        )
        assert cdm.name == "error_rate_human_car"
        assert cdm.metric_type == "per_period"
        assert cdm.window == "5m"

    def test_valid_per_request(self):
        cdm = CDMDefinition(
            name="is_correct",
            metric_type="per_request",
            expression=MetricExpression(type="count", filters={"is_correct": "true"}),
        )
        assert cdm.metric_type == "per_request"
        assert cdm.window is None

    def test_serialization_roundtrip(self):
        cdm = CDMDefinition(
            name="test",
            metric_type="per_period",
            expression=MetricExpression(type="avg", filters={"model": "yolov8n"}),
            window="1h",
        )
        json_str = cdm.model_dump_json()
        restored = CDMDefinition.model_validate_json(json_str)
        assert restored == cdm


class TestMetric:
    def test_from_dict(self):
        m = Metric.from_dict({"metric_name": "accuracy", "value": 0.95, "unit": "%"})
        assert m.metric_name == "accuracy"
        assert m.value == 0.95

    def test_without_optional_fields(self):
        m = Metric(metric_name="latency", value=42.5)
        assert m.unit is None
        assert m.condition is None


class TestClassSpecificMetric:
    def test_from_dict(self):
        csm = ClassSpecificMetric.from_dict({
            "class_name": "car",
            "performance": [
                {"metric_name": "accuracy", "value": 0.92},
                {"metric_name": "confidence", "value": 0.88},
            ],
        })
        assert csm.class_name == "car"
        assert len(csm.performance) == 2


class TestRuntimePerformance:
    def test_from_dict(self):
        rp = RuntimePerformance.from_dict({
            "overall_performance": [{"metric_name": "accuracy", "value": 0.90}],
            "class_specific_performance": [
                {
                    "class_name": "car",
                    "performance": [{"metric_name": "precision", "value": 0.85}],
                }
            ],
        })
        assert rp.overall_performance is not None
        assert len(rp.overall_performance) == 1
        assert rp.class_specific_performance is not None
        assert rp.class_specific_performance[0].class_name == "car"
