from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from rohe.export.exporter import ExperimentExporter, ExportManifest
from rohe.repositories.base import ExperimentRepository, MetricRepository


class InMemoryMetricRepo(MetricRepository):
    def __init__(self, metrics: list[dict[str, Any]] | None = None):
        self._metrics = metrics or []

    def insert_metric(self, metric: dict[str, Any]) -> str:
        self._metrics.append(metric)
        return "ok"

    def insert_metrics_batch(self, metrics: list[dict[str, Any]]) -> int:
        self._metrics.extend(metrics)
        return len(metrics)

    def query_metrics(self, filters: dict[str, Any] | None = None, time_from: datetime | None = None, time_to: datetime | None = None, limit: int = 10000) -> list[dict[str, Any]]:
        result = self._metrics
        if filters:
            result = [m for m in result if all(m.get(k) == v for k, v in filters.items())]
        return result[:limit]

    def aggregate_metrics(self, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return []

    def delete_metrics(self, filters: dict[str, Any]) -> int:
        return 0


class InMemoryExperimentRepo(ExperimentRepository):
    def __init__(self, experiments: list[dict[str, Any]] | None = None):
        self._experiments = {e["experiment_id"]: e for e in (experiments or [])}

    def create_experiment(self, experiment: dict[str, Any]) -> str:
        self._experiments[experiment["experiment_id"]] = experiment
        return experiment["experiment_id"]

    def get_experiment(self, experiment_id: str) -> dict[str, Any] | None:
        return self._experiments.get(experiment_id)

    def get_experiment_by_name(self, name: str) -> dict[str, Any] | None:
        for e in self._experiments.values():
            if e["name"] == name:
                return e
        return None

    def update_experiment(self, experiment_id: str, updates: dict[str, Any]) -> bool:
        if experiment_id in self._experiments:
            self._experiments[experiment_id].update(updates)
            return True
        return False

    def list_experiments(self, status: str | None = None, pipeline_id: str | None = None) -> list[dict[str, Any]]:
        return list(self._experiments.values())

    def delete_experiment(self, experiment_id: str) -> bool:
        return self._experiments.pop(experiment_id, None) is not None


class TestExportManifest:
    def test_empty_manifest(self):
        m = ExportManifest()
        assert len(m.files) == 0
        assert "0 files" in m.summary()

    def test_add_files(self):
        m = ExportManifest()
        m.add_file(Path("a.csv"), 100, "test")
        m.add_file(Path("b.csv"), 50, "test2")
        assert len(m.files) == 2
        assert "150 total rows" in m.summary()


class TestExperimentExporter:
    def _make_experiment(self, exp_id: str = "exp-001", name: str = "test", algorithm: str = "dream") -> dict[str, Any]:
        return {
            "experiment_id": exp_id,
            "name": name,
            "algorithm": algorithm,
            "contract_id": "c-001",
            "pipeline_id": "p-001",
            "status": "stopped",
            "config": {},
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    def _make_metrics(self, exp_id: str, count: int = 10) -> list[dict[str, Any]]:
        return [
            {
                "experiment_id": exp_id,
                "query_id": f"q-{i}",
                "response_time_ms": 40.0 + i * 2,
                "confidence": 0.85 + i * 0.01,
                "model": "yolov8n",
            }
            for i in range(count)
        ]

    def test_export_experiment_csv(self, tmp_path: Path):
        exp = self._make_experiment()
        metrics = self._make_metrics("exp-001")
        exporter = ExperimentExporter(
            metric_repo=InMemoryMetricRepo(metrics),
            experiment_repo=InMemoryExperimentRepo([exp]),
        )

        manifest = exporter.export_experiment("exp-001", tmp_path, formats=["csv"])
        assert len(manifest.files) == 2  # metadata + metrics

        # Check metadata
        meta_path = tmp_path / "experiment_metadata.json"
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text())
        assert meta["experiment_id"] == "exp-001"

        # Check CSV
        csv_path = tmp_path / "per_request_metrics.csv"
        assert csv_path.exists()
        df = pd.read_csv(csv_path)
        assert len(df) == 10
        assert "query_id" in df.columns
        assert "response_time_ms" in df.columns

    def test_export_experiment_json(self, tmp_path: Path):
        exp = self._make_experiment()
        metrics = self._make_metrics("exp-001", count=5)
        exporter = ExperimentExporter(
            metric_repo=InMemoryMetricRepo(metrics),
            experiment_repo=InMemoryExperimentRepo([exp]),
        )
        manifest = exporter.export_experiment("exp-001", tmp_path, formats=["json"])
        json_path = tmp_path / "per_request_metrics.json"
        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert len(data) == 5

    def test_export_nonexistent_experiment(self, tmp_path: Path):
        exporter = ExperimentExporter(
            metric_repo=InMemoryMetricRepo(),
            experiment_repo=InMemoryExperimentRepo(),
        )
        manifest = exporter.export_experiment("nonexistent", tmp_path)
        assert len(manifest.files) == 0

    def test_export_experiment_no_metrics(self, tmp_path: Path):
        exp = self._make_experiment()
        exporter = ExperimentExporter(
            metric_repo=InMemoryMetricRepo(),
            experiment_repo=InMemoryExperimentRepo([exp]),
        )
        manifest = exporter.export_experiment("exp-001", tmp_path)
        # Only metadata, no metrics file
        assert len(manifest.files) == 1

    def test_export_creates_output_dir(self, tmp_path: Path):
        nested_dir = tmp_path / "nested" / "output"
        exp = self._make_experiment()
        exporter = ExperimentExporter(
            metric_repo=InMemoryMetricRepo(self._make_metrics("exp-001")),
            experiment_repo=InMemoryExperimentRepo([exp]),
        )
        exporter.export_experiment("exp-001", nested_dir)
        assert nested_dir.exists()

    def test_comparison_export(self, tmp_path: Path):
        exp1 = self._make_experiment("exp-dream", "dream-run", "dream")
        exp2 = self._make_experiment("exp-llf", "llf-run", "llf")
        metrics = self._make_metrics("exp-dream", 20) + self._make_metrics("exp-llf", 20)

        exporter = ExperimentExporter(
            metric_repo=InMemoryMetricRepo(metrics),
            experiment_repo=InMemoryExperimentRepo([exp1, exp2]),
        )
        manifest = exporter.export_comparison(["exp-dream", "exp-llf"], tmp_path)
        assert len(manifest.files) == 1

        csv_path = tmp_path / "algorithm_comparison.csv"
        assert csv_path.exists()
        df = pd.read_csv(csv_path)
        assert len(df) == 2
        assert set(df["algorithm"]) == {"dream", "llf"}
        assert "avg_response_time_ms" in df.columns
        assert "request_count" in df.columns

    def test_comparison_with_missing_experiment(self, tmp_path: Path):
        exp1 = self._make_experiment("exp-1")
        exporter = ExperimentExporter(
            metric_repo=InMemoryMetricRepo(self._make_metrics("exp-1")),
            experiment_repo=InMemoryExperimentRepo([exp1]),
        )
        manifest = exporter.export_comparison(["exp-1", "nonexistent"], tmp_path)
        csv_path = tmp_path / "algorithm_comparison.csv"
        df = pd.read_csv(csv_path)
        assert len(df) == 1  # only exp-1

    def test_comparison_empty(self, tmp_path: Path):
        exporter = ExperimentExporter(
            metric_repo=InMemoryMetricRepo(),
            experiment_repo=InMemoryExperimentRepo(),
        )
        manifest = exporter.export_comparison(["a", "b"], tmp_path)
        assert len(manifest.files) == 0

    def test_multiple_formats(self, tmp_path: Path):
        exp = self._make_experiment()
        metrics = self._make_metrics("exp-001")
        exporter = ExperimentExporter(
            metric_repo=InMemoryMetricRepo(metrics),
            experiment_repo=InMemoryExperimentRepo([exp]),
        )
        manifest = exporter.export_experiment("exp-001", tmp_path, formats=["csv", "json"])
        # metadata + csv + json
        assert len(manifest.files) == 3
        assert (tmp_path / "per_request_metrics.csv").exists()
        assert (tmp_path / "per_request_metrics.json").exists()
