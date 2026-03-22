from __future__ import annotations

import pytest

from rohe.models.pipeline import InferenceFeedback, InferenceQuery, InferenceResult, InferenceTask, TaskList


class TestInferenceQuery:
    def test_create(self):
        q = InferenceQuery(
            metadata={"consumer": "tenant-1"},
            data_source=["video", "sensor"],
            time_window=30,
            explainability=False,
            constraint={"response_time": 200},
            query_id="q-001",
        )
        assert q.query_id == "q-001"
        assert q.get_response_time() == 200
        assert len(q.data_source) == 2

    def test_no_response_time_constraint(self):
        q = InferenceQuery(
            metadata={},
            data_source=["img"],
            time_window=10,
            explainability=True,
            constraint={},
        )
        assert q.get_response_time() is None


class TestInferenceResult:
    def test_empty_result(self):
        r = InferenceResult()
        assert r.data == {}
        assert r.task_id == []
        assert r.inf_id == []

    def test_top_k(self):
        r = InferenceResult(data={"car": 0.9, "truck": 0.7, "bus": 0.3, "person": 0.1})
        top2 = r.get_top_k_predictions(top_k=2)
        assert top2 == ["car", "truck"]

    def test_worst_k(self):
        r = InferenceResult(data={"car": 0.9, "truck": 0.7, "bus": 0.3, "person": 0.1})
        worst2 = r.get_worst_k_predictions(worst_k=2)
        assert worst2 == ["person", "bus"]

    def test_aggregate_sum(self):
        r1 = InferenceResult(
            query_id="q-001", task_id=["t1"], inf_id=["i1"],
            data={"car": 0.8, "truck": 0.2},
        )
        r2 = InferenceResult(
            query_id="q-001", task_id=["t2"], inf_id=["i2"],
            data={"car": 0.6, "bus": 0.4},
        )
        r1.aggregate(r2)
        assert r1.data["car"] == pytest.approx(1.4)
        assert r1.data["truck"] == pytest.approx(0.2)
        assert r1.data["bus"] == pytest.approx(0.4)
        assert set(r1.task_id) == {"t1", "t2"}
        assert set(r1.inf_id) == {"i1", "i2"}

    def test_aggregate_avg(self):
        r1 = InferenceResult(
            query_id="q-001", task_id=["t1"], inf_id=["i1"],
            data={"car": 0.8},
        )
        r2 = InferenceResult(
            query_id="q-001", task_id=["t2"], inf_id=["i2"],
            data={"car": 0.6},
        )
        r1.aggregate(r2, avg_flag=True)
        assert r1.data["car"] == pytest.approx(0.7)

    def test_get_avg_from_sum(self):
        r = InferenceResult(
            query_id="q-001", inf_id=["i1", "i2"],
            data={"car": 1.8, "truck": 0.4},
        )
        r.get_avg_from_aggregated_sum()
        assert r.data["car"] == pytest.approx(0.9)
        assert r.data["truck"] == pytest.approx(0.2)

    def test_sort(self):
        r = InferenceResult(data={"bus": 0.3, "car": 0.9, "truck": 0.7})
        r.sort_inference_result()
        keys = list(r.data.keys())
        assert keys == ["car", "truck", "bus"]

    def test_to_dict(self):
        r = InferenceResult(query_id=["q-001"], data={"car": 0.9})
        d = r.to_dict()
        assert d["query_id"] == "q-001"
        assert d["data"]["car"] == 0.9


class TestTaskList:
    def test_add_and_get(self):
        tl = TaskList()
        task = InferenceTask(task_id="t-001", modality="video")
        tl.add_task(task)
        assert tl.get_task_info("t-001") is not None
        assert tl.get_task_info("t-999") is None

    def test_duplicate_rejected(self):
        tl = TaskList()
        task = InferenceTask(task_id="t-001")
        tl.add_task(task)
        with pytest.raises(ValueError, match="already exists"):
            tl.add_task(task)

    def test_modality_list(self):
        tl = TaskList()
        tl.add_task(InferenceTask(task_id="t1", modality="video"))
        tl.add_task(InferenceTask(task_id="t2", modality="sensor"))
        tl.add_task(InferenceTask(task_id="t3"))
        assert tl.get_list_modality() == ["video", "sensor"]


class TestInferenceFeedback:
    def test_create(self):
        f = InferenceFeedback(query_id="q-001", ground_truth="car")
        assert f.query_id == "q-001"
        assert f.ground_truth == "car"
