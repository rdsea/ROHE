"""Tests for the production InferenceOrchestrator v2."""
from __future__ import annotations

import pytest

from rohe.models.enums import CommonMetric, InstanceStatus, TaskStatus
from rohe.models.execution_plan import (
    EnsembleMember,
    ExecutionPhase,
    ExecutionPlan,
    ModalityEnsemble,
    PhaseCondition,
    PreprocessorSpec,
)
from rohe.monitoring.inference_reporter import LoggingReporter, NoOpReporter
from rohe.orchestration.inference.ensemble_selector import (
    EnhanceConfidenceSelector,
    EnhanceGeneralizationSelector,
    EnsembleSelectorFactory,
    SelectByOverallAccuracySelector,
)
from rohe.orchestration.inference.service_registry import InMemoryServiceRegistry


class TestEnums:
    def test_task_status_is_str(self) -> None:
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.COMPLETED == "completed"

    def test_common_metric_is_str(self) -> None:
        assert CommonMetric.RESPONSE_TIME == "response_time"

    def test_instance_status_is_str(self) -> None:
        assert InstanceStatus.AVAILABLE == "available"


class TestEnsembleSelectorFactory:
    def test_create_enhance_confidence(self) -> None:
        selector = EnsembleSelectorFactory.create("enhance_confidence")
        assert isinstance(selector, EnhanceConfidenceSelector)

    def test_create_overall_accuracy(self) -> None:
        selector = EnsembleSelectorFactory.create("select_by_overall_accuracy")
        assert isinstance(selector, SelectByOverallAccuracySelector)

    def test_create_enhance_generalization(self) -> None:
        selector = EnsembleSelectorFactory.create("enhance_generalization")
        assert isinstance(selector, EnhanceGeneralizationSelector)

    def test_create_unknown_falls_back(self) -> None:
        selector = EnsembleSelectorFactory.create("nonexistent")
        assert isinstance(selector, EnhanceConfidenceSelector)

    def test_available_strategies(self) -> None:
        strategies = EnsembleSelectorFactory.available_strategies()
        assert "enhance_confidence" in strategies
        assert "select_by_overall_accuracy" in strategies
        assert "enhance_generalization" in strategies

    def test_register_custom(self) -> None:
        class CustomSelector(EnhanceConfidenceSelector):
            pass
        EnsembleSelectorFactory.register("custom", CustomSelector)
        selector = EnsembleSelectorFactory.create("custom")
        assert isinstance(selector, CustomSelector)


class TestInMemoryServiceRegistry:
    def test_empty_registry(self) -> None:
        reg = InMemoryServiceRegistry()
        assert reg.get_services() == {}
        assert reg.get_instances() == {}
        assert reg.get_sla("unknown") is None

    def test_add_sla(self) -> None:
        from rohe.models.contracts import ServiceLevelAgreement
        reg = InMemoryServiceRegistry()
        sla = ServiceLevelAgreement(
            sla_id="test", tenant_id="t1",
            access_privileges=["bts"],
            service_level_indicators=[],
        )
        reg.add_sla("t1", sla)
        assert reg.get_sla("t1") is not None
        assert reg.get_sla("t1").sla_id == "test"

    def test_refresh_is_noop(self) -> None:
        reg = InMemoryServiceRegistry()
        reg.refresh()  # should not raise


class TestInferenceReporter:
    def test_noop_reporter(self) -> None:
        reporter = NoOpReporter()
        # Should not raise
        from rohe.models.pipeline import MonitoringReport
        report = MonitoringReport(
            query_id="q1", inf_id="i1", inf_time=0.1,
            data_source="test", model_id="m1", device_id="d1",
            instance_id="inst1", response_time=0.05, inf_result={},
        )
        reporter.report(report)

    def test_logging_reporter(self) -> None:
        reporter = LoggingReporter()
        from rohe.models.pipeline import MonitoringReport
        report = MonitoringReport(
            query_id="q1", inf_id="i1", inf_time=0.1,
            data_source="test", model_id="m1", device_id="d1",
            instance_id="inst1", response_time=0.05, inf_result={},
        )
        reporter.report(report)  # should log, not raise


class TestOrchestratorV2:
    def test_load_plan(self) -> None:
        from rohe.orchestration.inference.orchestrator_v2 import InferenceOrchestrator
        reg = InMemoryServiceRegistry()
        orch = InferenceOrchestrator(registry=reg)

        plan = ExecutionPlan(
            pipeline_id="test",
            modality_ensembles={
                "ts": ModalityEnsemble(modality="ts", ensemble_members=[]),
            },
            execution_phases=[ExecutionPhase(phase_id=0, modalities=["ts"])],
        )
        orch.load_plan(plan)
        assert orch.get_plan("test") is not None
        assert orch.get_plan("nonexistent") is None

    @pytest.mark.asyncio
    async def test_orchestrate_no_plan(self) -> None:
        from rohe.orchestration.inference.orchestrator_v2 import InferenceOrchestrator
        reg = InMemoryServiceRegistry()
        orch = InferenceOrchestrator(registry=reg)

        result = await orch.orchestrate(
            query_id="q1", pipeline_id="missing", modalities=["ts"],
        )
        assert result["model_count"] == 0
        assert result["ensemble_result"] == {}

    def test_should_run_unconditional_phase(self) -> None:
        from rohe.orchestration.inference.orchestrator_v2 import InferenceOrchestrator
        reg = InMemoryServiceRegistry()
        orch = InferenceOrchestrator(registry=reg)

        phase = ExecutionPhase(phase_id=0, modalities=["ts"])
        assert orch._should_run_phase(phase, []) is True

    def test_should_run_conditional_phase_low_confidence(self) -> None:
        from rohe.orchestration.inference.orchestrator_v2 import InferenceOrchestrator
        reg = InMemoryServiceRegistry()
        orch = InferenceOrchestrator(registry=reg)

        phase = ExecutionPhase(
            phase_id=1, modalities=["extra"], is_conditional=True,
            condition=PhaseCondition(
                trigger="confidence_below", threshold=0.7,
                source_modalities=["ts"],
            ),
        )
        results = [{"confidence": 0.5, "modality": "ts", "predictions": {}}]
        assert orch._should_run_phase(phase, results) is True

    def test_should_skip_conditional_phase_high_confidence(self) -> None:
        from rohe.orchestration.inference.orchestrator_v2 import InferenceOrchestrator
        reg = InMemoryServiceRegistry()
        orch = InferenceOrchestrator(registry=reg)

        phase = ExecutionPhase(
            phase_id=1, modalities=["extra"], is_conditional=True,
            condition=PhaseCondition(
                trigger="confidence_below", threshold=0.7,
                source_modalities=["ts"],
            ),
        )
        results = [{"confidence": 0.9, "modality": "ts", "predictions": {}}]
        assert orch._should_run_phase(phase, results) is False
