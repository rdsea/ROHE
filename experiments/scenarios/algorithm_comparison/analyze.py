"""Analyze algorithm comparison experiment results.

Loads result CSVs, generates latency CDF and accuracy boxplot per algorithm,
computes statistical significance tests, and produces a LaTeX comparison table.
"""
from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

try:
    import pandas as pd
except ImportError:
    pd = None  # type: ignore[assignment]

from experiments.common.analysis.plot_utils import (
    plot_accuracy_boxplot,
    plot_latency_cdf,
)
from experiments.common.analysis.stats_utils import (
    compute_significance,
    compute_summary_stats,
)
from experiments.common.analysis.latex_utils import generate_comparison_table

# Pattern: {app}_{algorithm}_rep{N}.csv
RESULT_FILENAME_RE = re.compile(r"^(.+?)_(.+?)_rep(\d+)\.csv$")


def load_results(input_dir: Path) -> "pd.DataFrame":
    """Load all result CSVs and tag with app, algorithm, and repetition."""
    if pd is None:
        raise ImportError("pandas is required: pip install pandas")

    frames: list[pd.DataFrame] = []
    for csv_path in sorted(input_dir.glob("*.csv")):
        match = RESULT_FILENAME_RE.match(csv_path.name)
        if not match:
            logger.warning(f"Skipping unrecognized file: {csv_path.name}")
            continue

        app_name, algorithm, rep = match.group(1), match.group(2), int(match.group(3))
        df = pd.read_csv(csv_path)
        df["app"] = app_name
        df["algorithm"] = algorithm
        df["repetition"] = rep
        frames.append(df)

    if not frames:
        raise FileNotFoundError(f"No result CSVs found in {input_dir}")

    combined = pd.concat(frames, ignore_index=True)
    logger.info(f"Loaded {len(combined)} rows from {len(frames)} CSV files")
    return combined


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze algorithm comparison results")
    parser.add_argument("--input-dir", required=True, help="Directory containing result CSVs")
    parser.add_argument("--output-dir", default="./figures", help="Directory for output figures and tables")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_results(input_dir)

    # Filter to successful requests only
    df_ok = df[df["status"] == "ok"].copy()
    if df_ok.empty:
        logger.error("No successful requests found in results")
        return

    apps = df_ok["app"].unique()

    for app_name in apps:
        app_df = df_ok[df_ok["app"] == app_name]
        logger.info(f"Analyzing app={app_name}: {len(app_df)} successful requests")

        # -- Latency CDF per algorithm --
        latency_data: dict[str, list[float]] = {}
        for algo in app_df["algorithm"].unique():
            latency_data[algo] = app_df[app_df["algorithm"] == algo]["response_time_ms"].tolist()

        plot_latency_cdf(
            latency_data,
            title=f"Response Time CDF - {app_name}",
            output_path=output_dir / f"{app_name}_latency_cdf",
        )
        logger.info(f"Saved latency CDF for {app_name}")

        # -- Accuracy boxplot per algorithm --
        accuracy_data: dict[str, list[float]] = {}
        for algo in app_df["algorithm"].unique():
            accuracy_data[algo] = app_df[app_df["algorithm"] == algo]["confidence"].tolist()

        plot_accuracy_boxplot(
            accuracy_data,
            title=f"Confidence Distribution - {app_name}",
            ylabel="Confidence",
            output_path=output_dir / f"{app_name}_accuracy_boxplot",
        )
        logger.info(f"Saved accuracy boxplot for {app_name}")

        # -- Summary statistics --
        summary = compute_summary_stats(app_df, metric="response_time_ms", group_by="algorithm")
        summary_path = output_dir / f"{app_name}_latency_summary.csv"
        summary.to_csv(summary_path)
        logger.info(f"Saved latency summary to {summary_path}")

        accuracy_summary = compute_summary_stats(app_df, metric="confidence", group_by="algorithm")
        accuracy_summary_path = output_dir / f"{app_name}_accuracy_summary.csv"
        accuracy_summary.to_csv(accuracy_summary_path)
        logger.info(f"Saved accuracy summary to {accuracy_summary_path}")

        # -- Statistical significance --
        sig_latency = compute_significance(app_df, metric="response_time_ms", group_by="algorithm")
        sig_latency_path = output_dir / f"{app_name}_significance_latency.csv"
        sig_latency.to_csv(sig_latency_path, index=False)
        logger.info(f"Saved latency significance tests to {sig_latency_path}")

        sig_accuracy = compute_significance(app_df, metric="confidence", group_by="algorithm")
        sig_accuracy_path = output_dir / f"{app_name}_significance_accuracy.csv"
        sig_accuracy.to_csv(sig_accuracy_path, index=False)
        logger.info(f"Saved accuracy significance tests to {sig_accuracy_path}")

        # -- LaTeX comparison table --
        latex_table = generate_comparison_table(
            df=app_df,
            metrics=["response_time_ms", "confidence", "model_count"],
            group_by="algorithm",
            caption=f"Algorithm comparison -- {app_name}",
            label=f"tab:{app_name}_algo_comparison",
        )
        table_path = output_dir / f"{app_name}_comparison_table.tex"
        table_path.write_text(latex_table)
        logger.info(f"Saved LaTeX table to {table_path}")

    print(f"Analysis complete. Figures and tables saved to {output_dir}")


if __name__ == "__main__":
    main()
