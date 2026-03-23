"""Analyze latency-accuracy tradeoff experiment results.

Generates scatter plots of ensemble_size vs (latency, accuracy) and
identifies the Pareto frontier of optimal configurations.
"""
from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

try:
    import numpy as np
    import pandas as pd
except ImportError:
    np = None  # type: ignore[assignment]
    pd = None  # type: ignore[assignment]

from experiments.common.analysis.plot_utils import paper_style, save_figure
from experiments.common.analysis.stats_utils import (
    compute_confidence_interval,
    compute_summary_stats,
)
from experiments.common.analysis.latex_utils import generate_comparison_table

# Pattern: {app}_size{N}_rep{M}.csv
RESULT_FILENAME_RE = re.compile(r"^(.+?)_size(\d+)_rep(\d+)\.csv$")


def load_results(input_dir: Path) -> "pd.DataFrame":
    """Load all result CSVs and tag with app, ensemble_size, and repetition."""
    if pd is None:
        raise ImportError("pandas is required: pip install pandas")

    frames: list[pd.DataFrame] = []
    for csv_path in sorted(input_dir.glob("*.csv")):
        match = RESULT_FILENAME_RE.match(csv_path.name)
        if not match:
            logger.warning(f"Skipping unrecognized file: {csv_path.name}")
            continue

        app_name = match.group(1)
        ensemble_size = int(match.group(2))
        rep = int(match.group(3))
        df = pd.read_csv(csv_path)
        df["app"] = app_name
        df["ensemble_size"] = ensemble_size
        df["repetition"] = rep
        frames.append(df)

    if not frames:
        raise FileNotFoundError(f"No result CSVs found in {input_dir}")

    combined = pd.concat(frames, ignore_index=True)
    logger.info(f"Loaded {len(combined)} rows from {len(frames)} CSV files")
    return combined


def compute_pareto_frontier(
    points: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """Compute 2D Pareto frontier (minimize latency, maximize accuracy).

    Args:
        points: List of (latency, accuracy) tuples.

    Returns:
        Pareto-optimal points sorted by latency.
    """
    if not points:
        return []

    # Sort by latency ascending
    sorted_points = sorted(points, key=lambda p: p[0])
    frontier: list[tuple[float, float]] = []
    max_accuracy = float("-inf")

    for latency, accuracy in sorted_points:
        if accuracy > max_accuracy:
            frontier.append((latency, accuracy))
            max_accuracy = accuracy

    return frontier


def plot_tradeoff_with_pareto(
    df: "pd.DataFrame",
    app_name: str,
    output_dir: Path,
) -> None:
    """Scatter plot of ensemble_size vs (latency, accuracy) with Pareto frontier."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        logger.error("matplotlib required for plotting: pip install matplotlib")
        return

    ensemble_sizes = sorted(df["ensemble_size"].unique())
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]

    mean_latencies: list[float] = []
    mean_accuracies: list[float] = []

    with paper_style():
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))

        # Left: Individual points colored by ensemble_size
        for i, size in enumerate(ensemble_sizes):
            size_df = df[df["ensemble_size"] == size]
            color = colors[i % len(colors)]

            # Per-repetition means
            rep_groups = size_df.groupby("repetition")
            rep_latencies = rep_groups["response_time_ms"].mean().values
            rep_accuracies = rep_groups["confidence"].mean().values

            ax1.scatter(
                rep_latencies, rep_accuracies,
                label=f"Size {size}", color=color, s=60, alpha=0.7, zorder=5,
            )

            # Overall means for Pareto analysis
            mean_lat = float(size_df["response_time_ms"].mean())
            mean_acc = float(size_df["confidence"].mean())
            mean_latencies.append(mean_lat)
            mean_accuracies.append(mean_acc)

            # Error bars for mean point
            lat_mean, lat_lo, lat_hi = compute_confidence_interval(
                size_df["response_time_ms"].tolist()
            )
            acc_mean, acc_lo, acc_hi = compute_confidence_interval(
                size_df["confidence"].tolist()
            )
            ax1.errorbar(
                lat_mean, acc_mean,
                xerr=[[lat_mean - lat_lo], [lat_hi - lat_mean]],
                yerr=[[acc_mean - acc_lo], [acc_hi - acc_mean]],
                fmt="D", color=color, markersize=8, capsize=3, zorder=10,
            )

        # Pareto frontier on mean points
        pareto_points = list(zip(mean_latencies, mean_accuracies))
        frontier = compute_pareto_frontier(pareto_points)
        if len(frontier) > 1:
            f_lats, f_accs = zip(*frontier)
            ax1.plot(f_lats, f_accs, "k--", linewidth=1.5, alpha=0.6, label="Pareto frontier")

        ax1.set_xlabel("Mean Response Time (ms)")
        ax1.set_ylabel("Mean Confidence")
        ax1.set_title(f"Latency-Accuracy Tradeoff - {app_name}")
        ax1.legend()

        # Right: Box plots of latency and accuracy per ensemble_size
        latency_data = [
            df[df["ensemble_size"] == s]["response_time_ms"].tolist()
            for s in ensemble_sizes
        ]
        bp = ax2.boxplot(
            latency_data,
            labels=[str(s) for s in ensemble_sizes],
            patch_artist=True,
        )
        for i, patch in enumerate(bp["boxes"]):
            patch.set_facecolor(colors[i % len(colors)])
            patch.set_alpha(0.7)
        ax2.set_xlabel("Ensemble Size")
        ax2.set_ylabel("Response Time (ms)")
        ax2.set_title(f"Latency by Ensemble Size - {app_name}")

        fig.tight_layout()
        save_figure(fig, output_dir / f"{app_name}_tradeoff")

    logger.info(f"Saved tradeoff plot for {app_name}")

    # Log Pareto-optimal configurations
    for lat, acc in frontier:
        idx = mean_latencies.index(lat)
        size = ensemble_sizes[idx]
        logger.info(f"Pareto-optimal: size={size}, latency={lat:.1f}ms, accuracy={acc:.4f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze latency-accuracy tradeoff results")
    parser.add_argument("--input-dir", required=True, help="Directory containing result CSVs")
    parser.add_argument("--output-dir", default="./figures", help="Directory for output figures and tables")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_results(input_dir)

    # Filter to successful requests
    df_ok = df[df["status"] == "ok"].copy()
    if df_ok.empty:
        logger.error("No successful requests found in results")
        return

    apps = df_ok["app"].unique()

    for app_name in apps:
        app_df = df_ok[df_ok["app"] == app_name]
        logger.info(f"Analyzing app={app_name}: {len(app_df)} successful requests")

        # -- Tradeoff scatter with Pareto frontier --
        plot_tradeoff_with_pareto(app_df, app_name, output_dir)

        # -- Summary statistics per ensemble size --
        latency_summary = compute_summary_stats(
            app_df, metric="response_time_ms", group_by="ensemble_size",
        )
        latency_path = output_dir / f"{app_name}_latency_by_size.csv"
        latency_summary.to_csv(latency_path)
        logger.info(f"Saved latency summary to {latency_path}")

        accuracy_summary = compute_summary_stats(
            app_df, metric="confidence", group_by="ensemble_size",
        )
        accuracy_path = output_dir / f"{app_name}_accuracy_by_size.csv"
        accuracy_summary.to_csv(accuracy_path)
        logger.info(f"Saved accuracy summary to {accuracy_path}")

        # -- LaTeX table --
        latex_table = generate_comparison_table(
            df=app_df,
            metrics=["response_time_ms", "confidence", "model_count"],
            group_by="ensemble_size",
            caption=f"Latency-accuracy tradeoff -- {app_name}",
            label=f"tab:{app_name}_tradeoff",
        )
        table_path = output_dir / f"{app_name}_tradeoff_table.tex"
        table_path.write_text(latex_table)
        logger.info(f"Saved LaTeX table to {table_path}")

    print(f"Analysis complete. Figures and tables saved to {output_dir}")


if __name__ == "__main__":
    main()
