"""Tests for the orchestrator service phase condition evaluation."""
from __future__ import annotations

import pytest

from sys import path as sys_path
sys_path.insert(0, "examples/applications")

from common.schemas import InferenceResponse
from common.orchestrator_service import _should_run_phase
from rohe.models.execution_plan import ExecutionPhase, PhaseCondition


def _make_result(model: str, confidence: float, modality: str = "video") -> InferenceResponse:
    return InferenceResponse(
        query_id="test",
        predictions={"class_a": confidence, "class_b": 1.0 - confidence},
        confidence=confidence,
        model=model,
        response_time_ms=10.0,
        modality=modality,
    )


class TestShouldRunPhase:
    def test_unconditional_phase(self) -> None:
        phase = ExecutionPhase(phase_id=0, modalities=["video"])
        # Unconditional phases don't have conditions, _should_run_phase returns True
        assert _should_run_phase(phase, []) is True

    def test_confidence_below_triggers(self) -> None:
        phase = ExecutionPhase(
            phase_id=1,
            modalities=["timeseries"],
            is_conditional=True,
            condition=PhaseCondition(
                trigger="confidence_below",
                threshold=0.70,
                source_modalities=["video"],
            ),
        )
        # Low confidence -> should run
        results = [_make_result("model_a", 0.50, "video")]
        assert _should_run_phase(phase, results) is True

    def test_confidence_above_skips(self) -> None:
        phase = ExecutionPhase(
            phase_id=1,
            modalities=["timeseries"],
            is_conditional=True,
            condition=PhaseCondition(
                trigger="confidence_below",
                threshold=0.70,
                source_modalities=["video"],
            ),
        )
        # High confidence -> should skip
        results = [_make_result("model_a", 0.90, "video")]
        assert _should_run_phase(phase, results) is False

    def test_no_source_results_runs(self) -> None:
        phase = ExecutionPhase(
            phase_id=1,
            modalities=["timeseries"],
            is_conditional=True,
            condition=PhaseCondition(
                trigger="confidence_below",
                threshold=0.70,
                source_modalities=["video"],
            ),
        )
        # No video results -> run the phase anyway
        results = [_make_result("ts_model", 0.90, "timeseries")]
        assert _should_run_phase(phase, results) is True

    def test_agreement_below_triggers(self) -> None:
        phase = ExecutionPhase(
            phase_id=1,
            modalities=["gyro"],
            is_conditional=True,
            condition=PhaseCondition(
                trigger="agreement_below",
                threshold=0.80,
                source_modalities=["video"],
            ),
        )
        # Two models disagree on top prediction
        r1 = InferenceResponse(
            query_id="t", predictions={"a": 0.6, "b": 0.4},
            confidence=0.6, model="m1", response_time_ms=10.0, modality="video",
        )
        r2 = InferenceResponse(
            query_id="t", predictions={"b": 0.7, "a": 0.3},
            confidence=0.7, model="m2", response_time_ms=10.0, modality="video",
        )
        # top predictions: "a" and "b" -> agreement = 0.5 < 0.8 -> run
        assert _should_run_phase(phase, [r1, r2]) is True
