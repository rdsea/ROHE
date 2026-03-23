"""Analyze scaling behavior experiment results.

Plots throughput vs latency curves and identifies the saturation point
where latency begins to increase non-linearly.
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

# Pattern: {app}_rps{N}_rep{M}.csv
RESULT_FILENAME_RE = re.compile(r"^(.+?)_rps(\d+)_rep(\d+)\.csv$")


def load_results(input_dir: Path) -> "pd.DataFrame":
    """Load all result CSVs and tag with app, rps, and repetition."""
    if pd is None:
        raise ImportError("pandas is required: pip install pandas")

    frames: list[pd.DataFrame] = []
    for csv_path in sorted(input_dir.glob("*.csv")):
        match = RESULT_FILENAME_RE.match(csv_path.name)
        if not match:
            logger.warning(f"Skipping unrecognized file: {csv_path.name}")
            continue

        app_name = match.group(1)
        rps_level = int(match.group(2))
        rep = int(match.group(3))
        df = pd.read_csv(csv_path)
        df["app"] = app_name
        df["target_rps"] = rps_level
        df["repetition"] = rep
        frames.append(df)

    if not frames:
        raise FileNotFoundError(f"No result CSVs found in {input_dir}")

    combined = pd.concat(frames, ignore_index=True)
    logger.info(f"Loaded {len(combined)} rows from {len(frames)} CSV files")
    return combined


def find_saturation_point(
    rps_levels: list[int],
    p95_latencies: list[float],
) -> int | None:
    """Identify the RPS level where p95 latency growth rate exceeds 2x the initial rate.

    Returns the RPS level at saturation, or None if no saturation detected.
    """
    if np is None or len(rps_levels) < 3:
        return None

    rps_arr = np.array(rps_levels, dtype=float)
    lat_arr = np.array(p95_latencies, dtype=float)

    # Compute finite differences (latency growth per RPS unit)
    growth_rates = np.diff(lat_arr) / np.diff(rps_arr)
    if len(growth_rates) < 2:
        return None

    baseline_rate = growth_rates[0]
    if baseline_rate <= 0:
        return None

    for i, rate in enumerate(growth_rates[1:], start=1):
        if rate > 2.0 * baseline_rate:
            return rps_levels[i + 1]

    return None


def plot_throughput_latency(
    df: "pd.DataFrame",
    app_name: str,
    output_dir: Path,
) -> None:
    """Plot throughput vs latency with confidence intervals."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        logger.error("matplotlib required for plotting: pip install matplotlib")
        return

    rps_levels = sorted(df["target_rps"].unique())

    means: list[float] = []
    lowers: list[float] = []
    uppers: list[float] = []
    p95s: list[float] = []
    actual_throughputs: list[float] = []

    for rps in rps_levels:
        rps_df = df[df["target_rps"] == rps]
        latencies = rps_df["response_time_ms"].dropna().tolist()

        if not latencies:
            means.append(0.0)
            lowers.append(0.0)
            uppers.append(0.0)
            p95s.append(0.0)
            actual_throughputs.append(0.0)
            continue

        mean, lower, upper = compute_confidence_interval(latencies)
        means.append(mean)
        lowers.append(lower)
        uppers.append(upper)
        p95s.append(float(np.percentile(latencies, 95)))

        # Compute actual throughput (requests per second) from timestamps
        timestamps = rps_df["timestamp"].dropna()
        if len(timestamps) > 1:
            time_span = timestamps.max() - timestamps.min()
            actual_throughputs.append(len(timestamps) / max(time_span, 0.001))
        else:
            actual_throughputs.append(0.0)

    saturation_rps = find_saturation_point(rps_levels, p95s)

    with paper_style():
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))

        # Left: RPS vs Latency (mean + CI + p95)
        ax1.plot(rps_levels, means, "o-", label="Mean", color="#1f77b4")
        ax1.fill_between(rps_levels, lowers, uppers, alpha=0.2, color="#1f77b4")
        ax1.plot(rps_levels, p95s, "s--", label="p95", color="#d62728")

        if saturation_rps is not None:
            ax1.axvline(x=saturation_rps, linestyle=":", color="#888888", label=f"Saturation ({saturation_rps} RPS)")

        ax1.set_xlabel("Target RPS")
        ax1.set_ylabel("Response Time (ms)")
        ax1.set_title(f"Latency vs Load - {app_name}")
        ax1.legend()

        # Right: Target RPS vs Actual Throughput
        ax2.plot(rps_levels, actual_throughputs, "o-", color="#2ca02c")
        ax2.plot(rps_levels, rps_levels, "--", color="#888888", alpha=0.5, label="Ideal (1:1)")

        if saturation_rps is not None:
            ax2.axvline(x=saturation_rps, linestyle=":", color="#888888", label=f"Saturation ({saturation_rps} RPS)")

        ax2.set_xlabel("Target RPS")
        ax2.set_ylabel("Actual Throughput (req/s)")
        ax2.set_title(f"Throughput vs Load - {app_name}")
        ax2.legend()

        fig.tight_layout()
        save_figure(fig, output_dir / f"{app_name}_scaling_curve")

    if saturation_rps is not None:
        logger.info(f"Saturation point for {app_name}: {saturation_rps} RPS")
    else:
        logger.info(f"No saturation point detected for {app_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze scaling behavior results")
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

        # -- Throughput vs Latency plot --
        plot_throughput_latency(app_df, app_name, output_dir)

        # -- Summary statistics per RPS level --
        summary = compute_summary_stats(app_df, metric="response_time_ms", group_by="target_rps")
        summary_path = output_dir / f"{app_name}_scaling_summary.csv"
        summary.to_csv(summary_path)
        logger.info(f"Saved scaling summary to {summary_path}")

        # -- LaTeX table --
        latex_table = generate_comparison_table(
            df=app_df,
            metrics=["response_time_ms", "confidence"],
            group_by="target_rps",
            caption=f"Scaling behavior -- {app_name}",
            label=f"tab:{app_name}_scaling",
        )
        table_path = output_dir / f"{app_name}_scaling_table.tex"
        table_path.write_text(latex_table)
        logger.info(f"Saved LaTeX table to {table_path}")

    print(f"Analysis complete. Figures and tables saved to {output_dir}")


if __name__ == "__main__":
    main()
