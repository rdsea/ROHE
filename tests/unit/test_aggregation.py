"""Tests for aggregation strategies."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add examples/applications to path for common package import
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "examples" / "applications"))

from common.aggregation import aggregate_predictions
from common.schemas import InferenceResponse


def _make_result(model: str, predictions: dict[str, float], confidence: float) -> InferenceResponse:
    return InferenceResponse(
        query_id="q-001",
        predictions=predictions,
        confidence=confidence,
        model=model,
        response_time_ms=10.0,
    )


class TestConfidenceAvg:
    def test_basic(self):
        results = [
            _make_result("m1", {"car": 0.8, "truck": 0.2}, 0.8),
            _make_result("m2", {"car": 0.6, "truck": 0.4}, 0.6),
        ]
        agg = aggregate_predictions("q-001", results, "confidence_avg")
        assert agg.ensemble_predictions["car"] == pytest.approx(0.7, abs=0.01)
        assert agg.ensemble_predictions["truck"] == pytest.approx(0.3, abs=0.01)
        assert agg.model_count == 2
        assert agg.strategy == "confidence_avg"

    def test_missing_class_in_one_model(self):
        results = [
            _make_result("m1", {"car": 0.9}, 0.9),
            _make_result("m2", {"car": 0.6, "bus": 0.4}, 0.6),
        ]
        agg = aggregate_predictions("q-001", results, "confidence_avg")
        assert "bus" in agg.ensemble_predictions
        assert agg.ensemble_predictions["bus"] == pytest.approx(0.2, abs=0.01)

    def test_empty(self):
        agg = aggregate_predictions("q-001", [], "confidence_avg")
        assert agg.ensemble_predictions == {}
        assert agg.model_count == 0


class TestConfidenceWeighted:
    def test_higher_confidence_model_has_more_weight(self):
        results = [
            _make_result("m1", {"car": 1.0}, 0.9),
            _make_result("m2", {"car": 0.0}, 0.1),
        ]
        agg = aggregate_predictions("q-001", results, "confidence_weighted")
        assert agg.ensemble_predictions["car"] > 0.8


class TestConfidenceMax:
    def test_takes_max(self):
        results = [
            _make_result("m1", {"car": 0.5, "truck": 0.9}, 0.9),
            _make_result("m2", {"car": 0.8, "truck": 0.3}, 0.8),
        ]
        agg = aggregate_predictions("q-001", results, "confidence_max")
        assert agg.ensemble_predictions["car"] == pytest.approx(0.8, abs=0.01)
        assert agg.ensemble_predictions["truck"] == pytest.approx(0.9, abs=0.01)


class TestMajorityVote:
    def test_clear_majority(self):
        results = [
            _make_result("m1", {"car": 0.9, "truck": 0.1}, 0.9),
            _make_result("m2", {"car": 0.8, "truck": 0.2}, 0.8),
            _make_result("m3", {"truck": 0.7, "car": 0.3}, 0.7),
        ]
        agg = aggregate_predictions("q-001", results, "majority_vote")
        assert agg.ensemble_predictions["car"] > agg.ensemble_predictions.get("truck", 0)

    def test_tie(self):
        results = [
            _make_result("m1", {"car": 0.9}, 0.9),
            _make_result("m2", {"truck": 0.9}, 0.9),
        ]
        agg = aggregate_predictions("q-001", results, "majority_vote")
        assert agg.ensemble_predictions["car"] == pytest.approx(0.5)
        assert agg.ensemble_predictions["truck"] == pytest.approx(0.5)

    def test_empty_predictions(self):
        results = [_make_result("m1", {}, 0.0)]
        agg = aggregate_predictions("q-001", results, "majority_vote")
        assert agg.ensemble_predictions == {}


class TestUnknownStrategy:
    def test_falls_back_to_avg(self):
        results = [_make_result("m1", {"car": 0.8}, 0.8)]
        agg = aggregate_predictions("q-001", results, "nonexistent_strategy")
        assert "car" in agg.ensemble_predictions


class TestAggregateResponse:
    def test_sorted_by_confidence(self):
        results = [
            _make_result("m1", {"z_class": 0.1, "a_class": 0.9}, 0.9),
        ]
        agg = aggregate_predictions("q-001", results, "confidence_avg")
        keys = list(agg.ensemble_predictions.keys())
        assert keys[0] == "a_class"

    def test_avg_confidence(self):
        results = [
            _make_result("m1", {"car": 0.8}, 0.8),
            _make_result("m2", {"car": 0.6}, 0.6),
        ]
        agg = aggregate_predictions("q-001", results, "confidence_avg")
        assert agg.avg_confidence == pytest.approx(0.7)
