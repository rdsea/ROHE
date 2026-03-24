from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from rohe.repositories.base import ExperimentRepository, MetricRepository

logger = logging.getLogger(__name__)


class ExportManifest:
    """Manifest of exported files with metadata."""

    def __init__(self) -> None:
        self.files: list[dict[str, Any]] = []

    def add_file(self, path: Path, row_count: int, description: str) -> None:
        self.files.append(
            {
                "path": str(path),
                "row_count": row_count,
                "description": description,
            }
        )

    def summary(self) -> str:
        total_rows = sum(f["row_count"] for f in self.files)
        return f"Exported {len(self.files)} files, {total_rows} total rows"


class ExperimentExporter:
    """Export experiment data to CSV/JSON/Parquet for scientific analysis."""

    def __init__(
        self,
        metric_repo: MetricRepository,
        experiment_repo: ExperimentRepository,
    ) -> None:
        self._metric_repo = metric_repo
        self._experiment_repo = experiment_repo

    def export_experiment(
        self,
        experiment_id: str,
        output_dir: Path,
        formats: list[Literal["csv", "json", "parquet"]] | None = None,
    ) -> ExportManifest:
        """Export all data for a single experiment."""
        if formats is None:
            formats = ["csv"]

        output_dir.mkdir(parents=True, exist_ok=True)
        manifest = ExportManifest()

        experiment = self._experiment_repo.get_experiment(experiment_id)
        if experiment is None:
            logger.warning(f"Experiment '{experiment_id}' not found")
            return manifest

        # Export experiment metadata
        meta_path = output_dir / "experiment_metadata.json"
        meta_path.write_text(json.dumps(experiment, indent=2, default=str))
        manifest.add_file(meta_path, 1, "Experiment metadata")

        # Export per-request metrics
        metrics = self._metric_repo.query_metrics(
            filters={"experiment_id": experiment_id},
            limit=100000,
        )
        if metrics:
            df = pd.DataFrame(metrics)
            for fmt in formats:
                path = output_dir / f"per_request_metrics.{fmt}"
                self._write_dataframe(df, path, fmt)
                manifest.add_file(path, len(df), f"Per-request metrics ({fmt})")

        logger.info(f"Export complete: {manifest.summary()}")
        return manifest

    def export_comparison(
        self,
        experiment_ids: list[str],
        output_dir: Path,
        group_by: str = "algorithm",
    ) -> ExportManifest:
        """Export side-by-side comparison across experiments."""
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest = ExportManifest()

        comparison_rows: list[dict[str, Any]] = []
        for exp_id in experiment_ids:
            experiment = self._experiment_repo.get_experiment(exp_id)
            if experiment is None:
                continue

            metrics = self._metric_repo.query_metrics(
                filters={"experiment_id": exp_id},
                limit=100000,
            )
            if not metrics:
                continue

            df = pd.DataFrame(metrics)
            row: dict[str, Any] = {
                "experiment_id": exp_id,
                "algorithm": experiment.get("algorithm", "unknown"),
                "name": experiment.get("name", ""),
            }

            if "response_time_ms" in df.columns:
                row["avg_response_time_ms"] = df["response_time_ms"].mean()
                row["p99_response_time_ms"] = df["response_time_ms"].quantile(0.99)

            if "confidence" in df.columns:
                row["avg_confidence"] = df["confidence"].mean()

            row["request_count"] = len(df)
            comparison_rows.append(row)

        if comparison_rows:
            comp_df = pd.DataFrame(comparison_rows)
            path = output_dir / "algorithm_comparison.csv"
            comp_df.to_csv(path, index=False)
            manifest.add_file(path, len(comp_df), "Algorithm comparison")

        logger.info(f"Comparison export complete: {manifest.summary()}")
        return manifest

    @staticmethod
    def _write_dataframe(df: pd.DataFrame, path: Path, fmt: str) -> None:
        """Write DataFrame in the specified format."""
        if fmt == "csv":
            df.to_csv(path, index=False)
        elif fmt == "json":
            df.to_json(path, orient="records", indent=2)
        elif fmt == "parquet":
            df.to_parquet(path, index=False)
