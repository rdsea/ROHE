from __future__ import annotations

from typing import Any

import pytest

from rohe.experiment.manager import ExperimentManager
from rohe.repositories.base import ExperimentRepository


class InMemoryExperimentRepo(ExperimentRepository):
    def __init__(self) -> None:
        self._experiments: dict[str, dict[str, Any]] = {}

    def create_experiment(self, experiment: dict[str, Any]) -> str:
        eid = experiment["experiment_id"]
        self._experiments[eid] = experiment
        return eid

    def get_experiment(self, experiment_id: str) -> dict[str, Any] | None:
        return self._experiments.get(experiment_id)

    def get_experiment_by_name(self, name: str) -> dict[str, Any] | None:
        for e in self._experiments.values():
            if e["name"] == name:
                return e
        return None

    def update_experiment(self, experiment_id: str, updates: dict[str, Any]) -> bool:
        if experiment_id not in self._experiments:
            return False
        self._experiments[experiment_id].update(updates)
        return True

    def list_experiments(self, status: str | None = None, pipeline_id: str | None = None) -> list[dict[str, Any]]:
        result = list(self._experiments.values())
        if status:
            result = [e for e in result if e.get("status") == status]
        if pipeline_id:
            result = [e for e in result if e.get("pipeline_id") == pipeline_id]
        return result

    def delete_experiment(self, experiment_id: str) -> bool:
        if experiment_id in self._experiments:
            del self._experiments[experiment_id]
            return True
        return False


@pytest.fixture
def manager() -> ExperimentManager:
    return ExperimentManager(InMemoryExperimentRepo())


class TestExperimentLifecycle:
    def test_create(self, manager: ExperimentManager) -> None:
        exp = manager.create("test-exp", "dream", "c-001", "p-001")
        assert exp["name"] == "test-exp"
        assert exp["algorithm"] == "dream"
        assert exp["status"] == "created"
        assert exp["experiment_id"]
        assert exp["created_at"]

    def test_create_with_config_and_tags(self, manager: ExperimentManager) -> None:
        exp = manager.create(
            "exp-2", "llf", "c-002", "p-002",
            config={"param1": 42},
            tags={"load": "steady", "nodes": "3"},
        )
        assert exp["config"]["param1"] == 42
        assert exp["tags"]["load"] == "steady"

    def test_start(self, manager: ExperimentManager) -> None:
        exp = manager.create("test", "dream", "c-001", "p-001")
        started = manager.start(exp["experiment_id"])
        assert started is not None
        assert started["status"] == "running"
        assert started["started_at"] is not None

    def test_start_nonexistent(self, manager: ExperimentManager) -> None:
        assert manager.start("nonexistent") is None

    def test_start_already_running(self, manager: ExperimentManager) -> None:
        exp = manager.create("test", "dream", "c-001", "p-001")
        manager.start(exp["experiment_id"])
        started_again = manager.start(exp["experiment_id"])
        assert started_again is not None
        assert started_again["status"] == "running"

    def test_stop(self, manager: ExperimentManager) -> None:
        exp = manager.create("test", "dream", "c-001", "p-001")
        manager.start(exp["experiment_id"])
        stopped = manager.stop(exp["experiment_id"])
        assert stopped is not None
        assert stopped["status"] == "stopped"
        assert stopped["stopped_at"] is not None

    def test_stop_nonexistent(self, manager: ExperimentManager) -> None:
        assert manager.stop("nonexistent") is None

    def test_full_lifecycle(self, manager: ExperimentManager) -> None:
        exp = manager.create("lifecycle", "priority", "c-001", "p-001")
        assert exp["status"] == "created"

        started = manager.start(exp["experiment_id"])
        assert started is not None
        assert started["status"] == "running"

        stopped = manager.stop(exp["experiment_id"])
        assert stopped is not None
        assert stopped["status"] == "stopped"

    def test_get_by_id(self, manager: ExperimentManager) -> None:
        exp = manager.create("test", "dream", "c-001", "p-001")
        found = manager.get(exp["experiment_id"])
        assert found is not None
        assert found["name"] == "test"

    def test_get_nonexistent(self, manager: ExperimentManager) -> None:
        assert manager.get("nonexistent") is None

    def test_get_by_name(self, manager: ExperimentManager) -> None:
        manager.create("unique-name", "llf", "c-001", "p-001")
        found = manager.get_by_name("unique-name")
        assert found is not None
        assert found["algorithm"] == "llf"

    def test_get_by_name_nonexistent(self, manager: ExperimentManager) -> None:
        assert manager.get_by_name("no-such-name") is None

    def test_list_all(self, manager: ExperimentManager) -> None:
        manager.create("exp-1", "dream", "c-001", "p-001")
        manager.create("exp-2", "llf", "c-001", "p-001")
        assert len(manager.list()) == 2

    def test_list_by_status(self, manager: ExperimentManager) -> None:
        e1 = manager.create("exp-1", "dream", "c-001", "p-001")
        manager.create("exp-2", "llf", "c-001", "p-001")
        manager.start(e1["experiment_id"])

        running = manager.list(status="running")
        assert len(running) == 1
        assert running[0]["name"] == "exp-1"

    def test_list_by_pipeline(self, manager: ExperimentManager) -> None:
        manager.create("exp-1", "dream", "c-001", "p-001")
        manager.create("exp-2", "llf", "c-001", "p-002")

        p1_exps = manager.list(pipeline_id="p-001")
        assert len(p1_exps) == 1

    def test_delete(self, manager: ExperimentManager) -> None:
        exp = manager.create("to-delete", "dream", "c-001", "p-001")
        assert manager.delete(exp["experiment_id"])
        assert manager.get(exp["experiment_id"]) is None

    def test_delete_nonexistent(self, manager: ExperimentManager) -> None:
        assert not manager.delete("nonexistent")

    def test_unique_experiment_ids(self, manager: ExperimentManager) -> None:
        e1 = manager.create("exp-1", "dream", "c-001", "p-001")
        e2 = manager.create("exp-2", "dream", "c-001", "p-001")
        assert e1["experiment_id"] != e2["experiment_id"]
