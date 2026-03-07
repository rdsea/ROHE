import os
import sys
import warnings
import pytest

ROHE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROHE_PATH, 'src'))
sys.path.insert(0, ROHE_PATH)
os.environ['ROHE_PATH'] = ROHE_PATH

warnings.filterwarnings("ignore", message="Field.*has conflict with protected namespace")

from rohe.orchestration.multimodal_abstration import (
    InferenceTask, TaskList, InferenceResult, InferenceServiceProfile,
    InferenceServiceInstance, RuntimePerformance, Metric, ClassSpecificMetric,
    CommonMetric, Explainability, TaskStatus,
)
from userModule.algorithm.multimodal_workflow import assigning_phase_with_longest_sequence
from userModule.algorithm.llf_workflow import compute_laxity, assigning_phase_with_laxity
from userModule.algorithm.dream_workflow import (
    compute_urgency, compute_map_score, should_early_drop,
    assigning_phase_with_dream, STARVATION_WEIGHT,
)
from userModule.algorithm.multimodal_ensemble import select_by_overall_accuracy
from rohe.orchestration import create_orchestrator, ORCHESTRATOR_REGISTRY, _import_class

try:
    from rohe.orchestration.multimodal_orchestration import AdaptiveOrchestrator
    from rohe.orchestration.llf_orchestration import LLFOrchestrator
    from rohe.orchestration.dream_orchestration import DREAMOrchestrator
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False

requires_duckdb = pytest.mark.skipif(not HAS_DUCKDB, reason="duckdb not installed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_task(task_id, modality, allocated_time, min_exec, max_exec):
    return InferenceTask(
        task_id=task_id,
        modality=modality,
        allocated_time=allocated_time,
        min_execution_time=min_exec,
        max_execution_time=max_exec,
        status=TaskStatus.PENDING.value,
        phase=-1,
    )


def _make_task_list(tasks):
    tl = TaskList()
    for t in tasks:
        tl.add_task(t)
    return tl


def _make_service(service_id, model_id, instance_ids, overall_accuracy, modality="image"):
    return InferenceServiceProfile(
        inference_service_id=service_id,
        model_id=model_id,
        device_type="gpu",
        base_line=[Metric(metric_name="accuracy", value=overall_accuracy)],
        inference_performance=RuntimePerformance(
            overall_performance=[
                Metric(metric_name=CommonMetric.ACCURACY.value, value=overall_accuracy),
            ],
            class_specific_performance=[],
        ),
        instance_list=instance_ids,
        modality=modality,
    )


def _make_instance(instance_id, service_id, response_time, modality="image"):
    return InferenceServiceInstance(
        instance_id=instance_id,
        model_id="model_a",
        device_id="device_1",
        ip_address="127.0.0.1",
        port=8000,
        runtime_performance=[
            Metric(
                metric_name=CommonMetric.RESPONSE_TIME.value,
                value=response_time,
                condition=Explainability.DISABLED.value,
            ),
        ],
        modality=modality,
        inference_service_id=service_id,
        status="available",
    )


# ===========================================================================
# Tests for LLF workflow
# ===========================================================================

class TestLLFWorkflow:

    def test_compute_laxity_basic(self):
        task = _make_task("t1", "image", 0.3, 0.1, 0.5)
        assert compute_laxity(task, 1.0) == pytest.approx(0.7)

    def test_compute_laxity_tight(self):
        task = _make_task("t1", "image", 1.0, 0.5, 1.0)
        assert compute_laxity(task, 1.0) == pytest.approx(0.0)

    def test_assigning_phase_all_phase_zero(self):
        tasks = [
            _make_task("t1", "image", 0.8, 0.1, 1.0),
            _make_task("t2", "audio", 0.3, 0.1, 0.5),
            _make_task("t3", "text", 0.1, 0.05, 0.2),
        ]
        tl = _make_task_list(tasks)
        result = assigning_phase_with_laxity(tl, remaining_time=1.0)
        for task in result.data:
            assert task.phase == 0

    def test_assigning_phase_sorted_by_laxity_ascending(self):
        tasks = [
            _make_task("t1", "image", 0.8, 0.1, 1.0),
            _make_task("t2", "audio", 0.3, 0.1, 0.5),
            _make_task("t3", "text", 0.5, 0.05, 0.6),
        ]
        tl = _make_task_list(tasks)
        result = assigning_phase_with_laxity(tl, remaining_time=1.0)
        laxities = [compute_laxity(t, 1.0) for t in result.data]
        assert laxities == sorted(laxities)
        assert result.data[0].task_id == "t1"
        assert result.data[1].task_id == "t3"
        assert result.data[2].task_id == "t2"

    def test_single_task(self):
        tasks = [_make_task("t1", "image", 0.5, 0.1, 0.5)]
        tl = _make_task_list(tasks)
        result = assigning_phase_with_laxity(tl, remaining_time=1.0)
        assert len(result.data) == 1
        assert result.data[0].phase == 0


# ===========================================================================
# Tests for DREAM workflow
# ===========================================================================

class TestDREAMWorkflow:

    def test_compute_urgency_normal(self):
        task = _make_task("t1", "image", 0.5, 0.2, 0.8)
        urgency = compute_urgency(task, 1.0)
        assert urgency == pytest.approx(0.2 / 0.8)

    def test_compute_urgency_zero_slack(self):
        task = _make_task("t1", "image", 0.5, 1.0, 1.0)
        urgency = compute_urgency(task, 1.0)
        assert urgency == float('inf')

    def test_compute_urgency_negative_slack(self):
        task = _make_task("t1", "image", 0.5, 1.5, 2.0)
        urgency = compute_urgency(task, 1.0)
        assert urgency == float('inf')

    def test_compute_map_score(self):
        task = _make_task("t1", "image", 0.5, 0.2, 0.8)
        score = compute_map_score(task, 1.0, starvation=0.0)
        expected_urgency = 0.2 / 0.8
        expected_lat_pref = 0.5 / 1.0
        assert score == pytest.approx(expected_urgency * expected_lat_pref)

    def test_compute_map_score_with_starvation(self):
        task = _make_task("t1", "image", 0.5, 0.2, 0.8)
        score = compute_map_score(task, 1.0, starvation=3.0)
        expected_urgency = 0.2 / 0.8
        expected_lat_pref = 0.5 / 1.0
        assert score == pytest.approx(expected_urgency * expected_lat_pref + STARVATION_WEIGHT * 3.0)

    def test_should_early_drop_true(self):
        task = _make_task("t1", "image", 0.5, 1.5, 2.0)
        assert should_early_drop(task, 1.0) is True

    def test_should_early_drop_false(self):
        task = _make_task("t1", "image", 0.5, 0.3, 0.8)
        assert should_early_drop(task, 1.0) is False

    def test_should_early_drop_exact_boundary(self):
        task = _make_task("t1", "image", 0.5, 1.0, 1.0)
        assert should_early_drop(task, 1.0) is False

    def test_assigning_phase_drops_infeasible(self):
        tasks = [
            _make_task("feasible", "image", 0.3, 0.2, 0.5),
            _make_task("infeasible", "audio", 0.3, 1.5, 2.0),
        ]
        tl = _make_task_list(tasks)
        result = assigning_phase_with_dream(tl, remaining_time=1.0)
        assert len(result.data) == 1
        assert result.data[0].task_id == "feasible"
        assert result.data[0].phase == 0

    def test_assigning_phase_all_feasible_sorted_by_map_score(self):
        t1 = _make_task("t1", "image", 0.8, 0.1, 1.0)
        t2 = _make_task("t2", "audio", 0.3, 0.5, 0.8)
        t3 = _make_task("t3", "text", 0.5, 0.3, 0.7)
        tl = _make_task_list([t1, t2, t3])
        result = assigning_phase_with_dream(tl, remaining_time=1.0)
        assert len(result.data) == 3
        scores = [compute_map_score(t, 1.0) for t in result.data]
        assert scores == sorted(scores, reverse=True)

    def test_assigning_phase_all_dropped(self):
        tasks = [
            _make_task("t1", "image", 0.5, 2.0, 3.0),
            _make_task("t2", "audio", 0.5, 1.5, 2.0),
        ]
        tl = _make_task_list(tasks)
        result = assigning_phase_with_dream(tl, remaining_time=1.0)
        assert len(result.data) == 0

    def test_single_task_feasible(self):
        tasks = [_make_task("t1", "image", 0.5, 0.2, 0.8)]
        tl = _make_task_list(tasks)
        result = assigning_phase_with_dream(tl, remaining_time=1.0)
        assert len(result.data) == 1
        assert result.data[0].phase == 0


# ===========================================================================
# Tests for Adaptive (longest-sequence) workflow
# ===========================================================================

class TestAdaptiveWorkflow:

    def test_basic_phase_assignment(self):
        tasks = [
            _make_task("t1", "image", 0.3, 0.1, 0.5),
            _make_task("t2", "audio", 0.4, 0.2, 0.6),
        ]
        tl = _make_task_list(tasks)
        result = assigning_phase_with_longest_sequence(tl, time_constraint=1.0)
        phases = [t.phase for t in result.data]
        assert 0 in phases

    def test_sequential_when_tight(self):
        tasks = [
            _make_task("t1", "image", 0.6, 0.3, 0.8),
            _make_task("t2", "audio", 0.6, 0.3, 0.8),
        ]
        tl = _make_task_list(tasks)
        result = assigning_phase_with_longest_sequence(tl, time_constraint=1.0)
        assert result.data[0].phase == 0
        assert result.data[1].phase == 0 or result.data[1].phase == 1

    def test_single_task(self):
        tasks = [_make_task("t1", "image", 0.3, 0.1, 0.5)]
        tl = _make_task_list(tasks)
        result = assigning_phase_with_longest_sequence(tl, time_constraint=1.0)
        assert len(result.data) == 1
        assert result.data[0].phase == 0


# ===========================================================================
# Tests for select_by_overall_accuracy
# ===========================================================================

class TestSelectByOverallAccuracy:

    def _setup_task_with_services(self, top_k=3):
        svc_a = _make_service("svc_a", "model_a", ["inst_1", "inst_2"], overall_accuracy=0.95)
        svc_b = _make_service("svc_b", "model_b", ["inst_3"], overall_accuracy=0.90)
        svc_c = _make_service("svc_c", "model_c", ["inst_4", "inst_5"], overall_accuracy=0.85)
        svc_d = _make_service("svc_d", "model_d", ["inst_6"], overall_accuracy=0.80)

        inst_1 = _make_instance("inst_1", "svc_a", 0.3)
        inst_2 = _make_instance("inst_2", "svc_a", 0.5)
        inst_3 = _make_instance("inst_3", "svc_b", 0.4)
        inst_4 = _make_instance("inst_4", "svc_c", 0.2)
        inst_5 = _make_instance("inst_5", "svc_c", 0.6)
        inst_6 = _make_instance("inst_6", "svc_d", 0.35)

        task = InferenceTask(
            task_id="task_1",
            modality="image",
            allocated_time=0.5,
            min_execution_time=0.1,
            max_execution_time=1.0,
            status=TaskStatus.PENDING.value,
            ensemble_size=top_k,
            ensemble_selection_strategy="select_by_overall_accuracy",
            explainability=False,
            inference_services={
                "svc_a": svc_a, "svc_b": svc_b, "svc_c": svc_c, "svc_d": svc_d,
            },
            inference_instances={
                "inst_1": inst_1, "inst_2": inst_2, "inst_3": inst_3,
                "inst_4": inst_4, "inst_5": inst_5, "inst_6": inst_6,
            },
        )
        return task

    def test_selects_top_k_by_accuracy(self):
        task = self._setup_task_with_services(top_k=3)
        intermediate = InferenceResult()
        select_by_overall_accuracy(task, intermediate, top_k=3)
        assert len(task.selected_instances) == 3

    def test_selection_order_follows_accuracy(self):
        task = self._setup_task_with_services(top_k=2)
        intermediate = InferenceResult()
        select_by_overall_accuracy(task, intermediate, top_k=2)
        assert len(task.selected_instances) == 2
        selected_service_ids = [inst.inference_service_id for inst in task.selected_instances]
        assert selected_service_ids[0] == "svc_a"
        assert selected_service_ids[1] == "svc_b"

    def test_top_k_exceeds_available_services(self):
        task = self._setup_task_with_services(top_k=10)
        intermediate = InferenceResult()
        select_by_overall_accuracy(task, intermediate, top_k=10)
        assert len(task.selected_instances) == 4

    def test_top_k_one(self):
        task = self._setup_task_with_services(top_k=1)
        intermediate = InferenceResult()
        select_by_overall_accuracy(task, intermediate, top_k=1)
        assert len(task.selected_instances) == 1
        assert task.selected_instances[0].inference_service_id == "svc_a"

    def test_ignores_intermediate_result(self):
        task = self._setup_task_with_services(top_k=2)
        intermediate = InferenceResult(
            data={"cat": 0.9, "dog": 0.1},
            query_id="q1",
            task_id=["t0"],
            inf_id=["inf_0"],
        )
        select_by_overall_accuracy(task, intermediate, top_k=2)
        assert len(task.selected_instances) == 2
        selected_service_ids = [inst.inference_service_id for inst in task.selected_instances]
        assert selected_service_ids[0] == "svc_a"
        assert selected_service_ids[1] == "svc_b"


# ===========================================================================
# Cross-algorithm comparison tests
# ===========================================================================

class TestAlgorithmComparison:

    def _make_standard_tasks(self):
        return [
            _make_task("t_image", "image", 0.8, 0.2, 1.0),
            _make_task("t_audio", "audio", 0.3, 0.1, 0.5),
            _make_task("t_text", "text", 0.5, 0.15, 0.7),
        ]

    def test_all_algorithms_assign_phase_zero(self):
        remaining = 2.0
        for algo_fn in [assigning_phase_with_laxity, assigning_phase_with_dream]:
            tasks = self._make_standard_tasks()
            tl = _make_task_list(tasks)
            result = algo_fn(tl, remaining)
            for task in result.data:
                assert task.phase == 0, f"{algo_fn.__name__} failed to set phase 0"

    def test_adaptive_may_use_multiple_phases(self):
        tasks = [
            _make_task("t1", "image", 0.6, 0.3, 0.8),
            _make_task("t2", "audio", 0.6, 0.3, 0.8),
        ]
        tl = _make_task_list(tasks)
        result = assigning_phase_with_longest_sequence(tl, time_constraint=1.0)
        phases = set(t.phase for t in result.data)
        assert len(phases) >= 1

    def test_llf_and_dream_same_tasks_different_order(self):
        tasks_llf = [
            _make_task("t1", "image", 0.8, 0.2, 1.0),
            _make_task("t2", "audio", 0.3, 0.5, 0.8),
            _make_task("t3", "text", 0.5, 0.3, 0.7),
        ]
        tasks_dream = [
            _make_task("t1", "image", 0.8, 0.2, 1.0),
            _make_task("t2", "audio", 0.3, 0.5, 0.8),
            _make_task("t3", "text", 0.5, 0.3, 0.7),
        ]
        tl_llf = _make_task_list(tasks_llf)
        tl_dream = _make_task_list(tasks_dream)
        result_llf = assigning_phase_with_laxity(tl_llf, remaining_time=1.0)
        result_dream = assigning_phase_with_dream(tl_dream, remaining_time=1.0)
        order_llf = [t.task_id for t in result_llf.data]
        order_dream = [t.task_id for t in result_dream.data]
        assert order_llf != order_dream

    def test_dream_drops_while_llf_keeps(self):
        tasks_llf = [
            _make_task("feasible", "image", 0.3, 0.2, 0.5),
            _make_task("tight", "audio", 0.3, 1.5, 2.0),
        ]
        tasks_dream = [
            _make_task("feasible", "image", 0.3, 0.2, 0.5),
            _make_task("tight", "audio", 0.3, 1.5, 2.0),
        ]
        tl_llf = _make_task_list(tasks_llf)
        tl_dream = _make_task_list(tasks_dream)
        result_llf = assigning_phase_with_laxity(tl_llf, remaining_time=1.0)
        result_dream = assigning_phase_with_dream(tl_dream, remaining_time=1.0)
        assert len(result_llf.data) == 2
        assert len(result_dream.data) == 1
        assert result_dream.data[0].task_id == "feasible"


# ===========================================================================
# Edge cases
# ===========================================================================

class TestEdgeCases:

    def test_empty_task_list_llf(self):
        tl = TaskList()
        result = assigning_phase_with_laxity(tl, remaining_time=1.0)
        assert len(result.data) == 0

    def test_empty_task_list_dream(self):
        tl = TaskList()
        result = assigning_phase_with_dream(tl, remaining_time=1.0)
        assert len(result.data) == 0

    def test_empty_task_list_adaptive(self):
        tl = TaskList()
        result = assigning_phase_with_longest_sequence(tl, time_constraint=1.0)
        assert len(result.data) == 0

    def test_zero_remaining_time_dream_drops_all(self):
        tasks = [
            _make_task("t1", "image", 0.3, 0.2, 0.5),
            _make_task("t2", "audio", 0.3, 0.1, 0.5),
        ]
        tl = _make_task_list(tasks)
        result = assigning_phase_with_dream(tl, remaining_time=0.0)
        assert len(result.data) == 0

    def test_zero_remaining_time_llf(self):
        tasks = [_make_task("t1", "image", 0.3, 0.2, 0.5)]
        tl = _make_task_list(tasks)
        result = assigning_phase_with_laxity(tl, remaining_time=0.0)
        assert len(result.data) == 1
        assert result.data[0].phase == 0

    def test_very_large_task_list(self):
        tasks = [_make_task(f"t{i}", "image", 0.1 * (i + 1), 0.05, 0.5) for i in range(20)]
        tl_llf = _make_task_list(tasks)
        result = assigning_phase_with_laxity(tl_llf, remaining_time=5.0)
        assert len(result.data) == 20
        laxities = [compute_laxity(t, 5.0) for t in result.data]
        assert laxities == sorted(laxities)


# ===========================================================================
# Algorithm switching via factory
# ===========================================================================

class TestOrchestratorFactory:

    def test_registry_contains_all_algorithm_keys(self):
        assert "adaptive" in ORCHESTRATOR_REGISTRY
        assert "llf" in ORCHESTRATOR_REGISTRY
        assert "dream" in ORCHESTRATOR_REGISTRY

    def test_unknown_algorithm_raises(self):
        with pytest.raises(ValueError, match="Unknown orchestration algorithm"):
            create_orchestrator(algorithm="nonexistent", config_path="dummy.yaml")

    def test_case_insensitive_lookup(self):
        for name in ["Adaptive", "ADAPTIVE", "adaptive", "LLF", "llf", "Llf", "DREAM", "Dream"]:
            assert name.lower() in ORCHESTRATOR_REGISTRY

    @requires_duckdb
    def test_registry_resolves_to_correct_classes(self):
        assert _import_class(ORCHESTRATOR_REGISTRY["adaptive"]) is AdaptiveOrchestrator
        assert _import_class(ORCHESTRATOR_REGISTRY["llf"]) is LLFOrchestrator
        assert _import_class(ORCHESTRATOR_REGISTRY["dream"]) is DREAMOrchestrator


@requires_duckdb
class TestOrchestratorInheritance:

    def test_llf_is_subclass_of_adaptive(self):
        assert issubclass(LLFOrchestrator, AdaptiveOrchestrator)

    def test_dream_is_subclass_of_adaptive(self):
        assert issubclass(DREAMOrchestrator, AdaptiveOrchestrator)

    def test_llf_overrides_determine_execution_workflow(self):
        assert LLFOrchestrator.determine_execution_workflow is not AdaptiveOrchestrator.determine_execution_workflow

    def test_dream_overrides_determine_execution_workflow(self):
        assert DREAMOrchestrator.determine_execution_workflow is not AdaptiveOrchestrator.determine_execution_workflow

    def test_llf_overrides_task_execution_loop(self):
        assert LLFOrchestrator.task_execution_loop is not AdaptiveOrchestrator.task_execution_loop

    def test_dream_overrides_task_execution_loop(self):
        assert DREAMOrchestrator.task_execution_loop is not AdaptiveOrchestrator.task_execution_loop

    def test_llf_inherits_shared_methods(self):
        shared = [
            "orchestrate", "execute_inference", "prepare_data",
            "get_time_allocation", "update_task_allocation_time",
            "select_ensemble", "distribute_inference_workload",
            "report_inference_result", "check_pending_tasks",
            "get_access_privileges", "filter_instances",
        ]
        for method_name in shared:
            assert getattr(LLFOrchestrator, method_name) is getattr(AdaptiveOrchestrator, method_name), f"LLF should inherit {method_name}"

    def test_dream_inherits_shared_methods(self):
        shared = [
            "orchestrate", "execute_inference", "prepare_data",
            "get_time_allocation", "update_task_allocation_time",
            "select_ensemble", "distribute_inference_workload",
            "report_inference_result", "check_pending_tasks",
            "get_access_privileges", "filter_instances",
        ]
        for method_name in shared:
            assert getattr(DREAMOrchestrator, method_name) is getattr(AdaptiveOrchestrator, method_name), f"DREAM should inherit {method_name}"


class TestEnsembleStrategySwitch:

    def _setup_task_with_strategy(self, strategy_name, top_k=2):
        svc_a = _make_service("svc_a", "model_a", ["inst_1"], overall_accuracy=0.95)
        svc_b = _make_service("svc_b", "model_b", ["inst_2"], overall_accuracy=0.90)
        inst_1 = _make_instance("inst_1", "svc_a", 0.3)
        inst_2 = _make_instance("inst_2", "svc_b", 0.4)
        return InferenceTask(
            task_id="task_switch",
            modality="image",
            allocated_time=0.5,
            min_execution_time=0.1,
            max_execution_time=1.0,
            status=TaskStatus.PENDING.value,
            ensemble_size=top_k,
            ensemble_selection_strategy=strategy_name,
            explainability=False,
            inference_services={"svc_a": svc_a, "svc_b": svc_b},
            inference_instances={"inst_1": inst_1, "inst_2": inst_2},
        )

    def test_select_by_overall_accuracy_is_callable_by_name(self):
        from userModule.algorithm import multimodal_ensemble
        fn = getattr(multimodal_ensemble, "select_by_overall_accuracy", None)
        assert fn is not None
        assert callable(fn)

    def test_strategy_dispatch_matches_orchestrator_select_ensemble(self):
        from userModule.algorithm import multimodal_ensemble
        for strategy in ["select_by_overall_accuracy", "enhance_confidence"]:
            fn = getattr(multimodal_ensemble, strategy, None)
            assert fn is not None, f"Strategy '{strategy}' not found in multimodal_ensemble"

    def test_select_by_overall_accuracy_via_dynamic_dispatch(self):
        from userModule.algorithm import multimodal_ensemble
        task = self._setup_task_with_strategy("select_by_overall_accuracy", top_k=2)
        intermediate = InferenceResult()
        fn = getattr(multimodal_ensemble, task.ensemble_selection_strategy)
        fn(task, intermediate, task.ensemble_size)
        assert len(task.selected_instances) == 2
