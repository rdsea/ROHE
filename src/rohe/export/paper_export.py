"""Advanced data export for scientific paper writing.

Generates publication-ready artifacts from experiment data:
- LaTeX tables (IEEE/ACM/Springer format)
- Matplotlib figures (CDF, boxplot, scatter, heatmap)
- Summary statistics CSV
- Significance test results

Integrates with experiments/common/analysis/ utilities.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import pandas as pd
except ImportError:
    pd = None  # type: ignore[assignment]


class PaperExporter:
    """Export experiment results as publication-ready artifacts.

    Usage:
        exporter = PaperExporter()
        exporter.export_from_csv(
            csv_path="results/client_results.csv",
            output_dir="paper/figures/",
            pipeline_id="bts",
        )
    """

    def export_from_csv(
        self,
        csv_path: str | Path,
        output_dir: str | Path,
        pipeline_id: str = "",
        group_by: str = "model",
        formats: list[str] | None = None,
    ) -> dict[str, Any]:
        """Export paper artifacts from a client results CSV.

        Returns manifest of generated files.
        """
        if pd is None:
            raise ImportError("pandas required: pip install pandas")

        csv_path = Path(csv_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        if formats is None:
            formats = ["pdf", "png"]

        df = pd.read_csv(csv_path)
        manifest: dict[str, list[str]] = {"figures": [], "tables": [], "data": []}

        # Summary statistics
        stats = self._generate_summary_stats(df, output_dir, group_by)
        manifest["data"].extend(stats)

        # Figures
        figs = self._generate_figures(df, output_dir, group_by, pipeline_id, formats)
        manifest["figures"].extend(figs)

        # LaTeX tables
        tables = self._generate_latex_tables(df, output_dir, group_by, pipeline_id)
        manifest["tables"].extend(tables)

        # Significance tests
        sig = self._generate_significance_tests(df, output_dir, group_by)
        manifest["data"].extend(sig)

        logger.info(
            f"Paper export complete: {len(manifest['figures'])} figures, "
            f"{len(manifest['tables'])} tables, {len(manifest['data'])} data files"
        )
        return manifest

    def export_comparison(
        self,
        csv_paths: dict[str, str | Path],
        output_dir: str | Path,
        comparison_name: str = "comparison",
        formats: list[str] | None = None,
    ) -> dict[str, Any]:
        """Export comparison across multiple experiment runs.

        csv_paths: {label: csv_path} mapping for each experiment variant.
        """
        if pd is None:
            raise ImportError("pandas required")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        if formats is None:
            formats = ["pdf", "png"]

        # Merge all CSVs with labels
        frames = []
        for label, path in csv_paths.items():
            df = pd.read_csv(path)
            df["variant"] = label
            frames.append(df)
        merged = pd.concat(frames, ignore_index=True)

        manifest: dict[str, list[str]] = {"figures": [], "tables": [], "data": []}

        # Generate comparison artifacts
        figs = self._generate_figures(
            merged, output_dir, "variant", comparison_name, formats
        )
        manifest["figures"].extend(figs)

        tables = self._generate_latex_tables(
            merged, output_dir, "variant", comparison_name
        )
        manifest["tables"].extend(tables)

        sig = self._generate_significance_tests(merged, output_dir, "variant")
        manifest["data"].extend(sig)

        return manifest

    def _generate_summary_stats(
        self,
        df: Any,
        output_dir: Path,
        group_by: str,
    ) -> list[str]:
        """Generate summary statistics CSV."""
        files: list[str] = []
        try:
            from experiments.common.analysis.stats_utils import compute_summary_stats

            for metric in ["response_time_ms", "confidence"]:
                if metric not in df.columns or group_by not in df.columns:
                    continue
                stats = compute_summary_stats(df, metric, group_by)
                path = output_dir / f"summary_{metric}.csv"
                stats.to_csv(path)
                files.append(str(path))
        except ImportError:
            # Fallback: basic stats
            if group_by in df.columns:
                for metric in ["response_time_ms", "confidence"]:
                    if metric in df.columns:
                        stats = df.groupby(group_by)[metric].describe()
                        path = output_dir / f"summary_{metric}.csv"
                        stats.to_csv(path)
                        files.append(str(path))
        return files

    def _generate_figures(
        self,
        df: Any,
        output_dir: Path,
        group_by: str,
        title_prefix: str,
        formats: list[str],
    ) -> list[str]:
        """Generate matplotlib figures."""
        files: list[str] = []
        try:
            from experiments.common.analysis.plot_utils import (
                plot_accuracy_boxplot,
                plot_latency_cdf,
            )

            if "response_time_ms" in df.columns and group_by in df.columns:
                data = {
                    name: group["response_time_ms"].dropna().tolist()
                    for name, group in df.groupby(group_by)
                }
                fig = plot_latency_cdf(
                    data,
                    title=f"{title_prefix} - Response Time CDF",
                    output_path=output_dir / "latency_cdf",
                )
                files.append(str(output_dir / "latency_cdf.pdf"))

            if "confidence" in df.columns and group_by in df.columns:
                data = {
                    name: group["confidence"].dropna().tolist()
                    for name, group in df.groupby(group_by)
                }
                fig = plot_accuracy_boxplot(
                    data,
                    title=f"{title_prefix} - Confidence Distribution",
                    output_path=output_dir / "confidence_boxplot",
                )
                files.append(str(output_dir / "confidence_boxplot.pdf"))

        except ImportError:
            logger.debug("matplotlib not available, skipping figure generation")
        except Exception as e:
            logger.warning(f"Figure generation failed: {e}")
        return files

    def _generate_latex_tables(
        self,
        df: Any,
        output_dir: Path,
        group_by: str,
        title_prefix: str,
    ) -> list[str]:
        """Generate LaTeX tables."""
        files: list[str] = []
        try:
            from experiments.common.analysis.latex_utils import (
                generate_comparison_table,
            )

            metrics = [
                c
                for c in ["response_time_ms", "confidence", "model_count"]
                if c in df.columns
            ]
            if metrics and group_by in df.columns:
                latex = generate_comparison_table(
                    df,
                    metrics=metrics,
                    group_by=group_by,
                    caption=f"{title_prefix} comparison",
                    label=f"tab:{title_prefix.lower().replace(' ', '_')}",
                )
                path = output_dir / "comparison_table.tex"
                path.write_text(latex)
                files.append(str(path))

        except ImportError:
            logger.debug("latex_utils not available, skipping LaTeX generation")
        except Exception as e:
            logger.warning(f"LaTeX table generation failed: {e}")
        return files

    def _generate_significance_tests(
        self,
        df: Any,
        output_dir: Path,
        group_by: str,
    ) -> list[str]:
        """Generate statistical significance test results."""
        files: list[str] = []
        try:
            from experiments.common.analysis.stats_utils import compute_significance

            for metric in ["response_time_ms", "confidence"]:
                if metric not in df.columns or group_by not in df.columns:
                    continue
                groups = df[group_by].nunique()
                if groups < 2:
                    continue
                sig = compute_significance(df, metric=metric, group_by=group_by)
                if not sig.empty:
                    path = output_dir / f"significance_{metric}.csv"
                    sig.to_csv(path, index=False)
                    files.append(str(path))

        except ImportError:
            logger.debug("scipy not available, skipping significance tests")
        except Exception as e:
            logger.warning(f"Significance test failed: {e}")
        return files
