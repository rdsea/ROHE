"""Tests for ExecutionPlan data model and mutations."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from rohe.models.execution_plan import (
    EnsembleMember,
    ExecutionPhase,
    ExecutionPlan,
    ModalityEnsemble,
    PhaseCondition,
    PreprocessorSpec,
)


def _make_member(service_id: str, instance_id: str = "") -> EnsembleMember:
    return EnsembleMember(
        service_id=service_id,
        instance_id=instance_id or f"{service_id}-001",
        inference_url=f"http://{service_id}:8000/inference",
        model_id=service_id,
        device_type="cpu",
    )


def _make_plan() -> ExecutionPlan:
    return ExecutionPlan(
        pipeline_id="test",
        modality_ensembles={
            "timeseries": ModalityEnsemble(
                modality="timeseries",
                ensemble_members=[
                    _make_member("lstm"),
                    _make_member("gru"),
                ],
                ensemble_size=2,
            ),
        },
        execution_phases=[
            ExecutionPhase(phase_id=0, modalities=["timeseries"]),
        ],
    )


class TestEnsembleMember:
    def test_frozen(self) -> None:
        member = _make_member("lstm")
        with pytest.raises(Exception):
            member.service_id = "changed"  # type: ignore[misc]

    def test_defaults(self) -> None:
        member = _make_member("lstm")
        assert member.weight == 1.0
        assert member.is_active is True


class TestModalityEnsemble:
    def test_get_active_members(self) -> None:
        ensemble = ModalityEnsemble(
            modality="test",
            ensemble_members=[
                _make_member("a"),
                EnsembleMember(
                    service_id="b", instance_id="b-001",
                    inference_url="http://b:8000", model_id="b",
                    device_type="cpu", is_active=False,
                ),
            ],
        )
        active = ensemble.get_active_members()
        assert len(active) == 1
        assert active[0].service_id == "a"


class TestExecutionPlan:
    def test_add_member(self) -> None:
        plan = _make_plan()
        assert len(plan.modality_ensembles["timeseries"].ensemble_members) == 2
        plan.add_member("timeseries", _make_member("transformer"))
        assert len(plan.modality_ensembles["timeseries"].ensemble_members) == 3
        assert plan.version == 1

    def test_add_member_duplicate_raises(self) -> None:
        plan = _make_plan()
        with pytest.raises(ValueError, match="already exists"):
            plan.add_member("timeseries", _make_member("lstm", "lstm-001"))

    def test_add_member_unknown_modality_raises(self) -> None:
        plan = _make_plan()
        with pytest.raises(ValueError, match="not found"):
            plan.add_member("video", _make_member("x3d"))

    def test_remove_member(self) -> None:
        plan = _make_plan()
        plan.remove_member("timeseries", "gru-001")
        assert len(plan.modality_ensembles["timeseries"].ensemble_members) == 1
        assert plan.version == 1

    def test_remove_member_not_found_raises(self) -> None:
        plan = _make_plan()
        with pytest.raises(ValueError, match="not found"):
            plan.remove_member("timeseries", "nonexistent")

    def test_replace_member(self) -> None:
        plan = _make_plan()
        plan.replace_member("timeseries", "gru-001", _make_member("transformer"))
        members = plan.modality_ensembles["timeseries"].ensemble_members
        service_ids = [m.service_id for m in members]
        assert "gru" not in service_ids
        assert "transformer" in service_ids
        assert plan.version == 2  # remove + add = 2 bumps

    def test_set_member_active(self) -> None:
        plan = _make_plan()
        plan.set_member_active("timeseries", "lstm-001", is_active=False)
        lstm = [m for m in plan.modality_ensembles["timeseries"].ensemble_members if m.instance_id == "lstm-001"][0]
        assert lstm.is_active is False
        assert plan.version == 1

    def test_version_increments(self) -> None:
        plan = _make_plan()
        assert plan.version == 0
        plan.add_member("timeseries", _make_member("t1"))
        assert plan.version == 1
        plan.add_member("timeseries", _make_member("t2"))
        assert plan.version == 2

    def test_get_phase_modalities(self) -> None:
        plan = _make_plan()
        assert plan.get_phase_modalities(0) == ["timeseries"]
        assert plan.get_phase_modalities(99) == []

    def test_json_roundtrip(self) -> None:
        plan = _make_plan()
        plan.add_member("timeseries", _make_member("transformer"))
        json_str = plan.to_redis_value()
        restored = ExecutionPlan.from_redis_value(json_str)
        assert restored.pipeline_id == "test"
        assert restored.version == 1
        assert len(restored.modality_ensembles["timeseries"].ensemble_members) == 3


class TestPreprocessorSpec:
    def test_frozen(self) -> None:
        spec = PreprocessorSpec(
            service_url="http://pre:8000",
            preprocessor_id="test",
            output_data_key="processed",
        )
        with pytest.raises(Exception):
            spec.service_url = "changed"  # type: ignore[misc]


class TestExecutionPhase:
    def test_conditional_phase(self) -> None:
        phase = ExecutionPhase(
            phase_id=1,
            modalities=["gyro"],
            is_conditional=True,
            condition=PhaseCondition(
                trigger="confidence_below",
                threshold=0.65,
                source_modalities=["video"],
            ),
        )
        assert phase.is_conditional is True
        assert phase.condition is not None
        assert phase.condition.threshold == 0.65
