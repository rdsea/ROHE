"""LaTeX table generation utilities for ROHE experiment results.

Generates publication-ready LaTeX tables for IEEE, ACM, and Springer formats.
"""
from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except ImportError:
    pd = None  # type: ignore[assignment]


def generate_comparison_table(
    df: Any,  # pd.DataFrame
    metrics: list[str],
    group_by: str,
    caption: str = "Algorithm comparison",
    label: str = "tab:comparison",
    float_format: str = "%.3f",
) -> str:
    """Generate a LaTeX comparison table from a DataFrame.

    Each row is a group (algorithm/model), columns are metrics.
    """
    if pd is None:
        raise ImportError("pandas required")

    groups = df[group_by].unique()
    rows: list[dict[str, Any]] = []
    for group in groups:
        group_df = df[df[group_by] == group]
        row: dict[str, Any] = {group_by: group}
        for metric in metrics:
            if metric in group_df.columns:
                row[metric] = group_df[metric].mean()
        rows.append(row)

    result_df = pd.DataFrame(rows).set_index(group_by)

    # Build LaTeX
    n_cols = len(metrics)
    col_spec = "l" + "r" * n_cols
    header = " & ".join([group_by.replace("_", r"\_")] + [m.replace("_", r"\_") for m in metrics])

    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        f"\\begin{{tabular}}{{{col_spec}}}",
        r"\toprule",
        header + r" \\",
        r"\midrule",
    ]

    for idx, row in result_df.iterrows():
        vals = [str(idx).replace("_", r"\_")]
        for metric in metrics:
            v = row.get(metric, "")
            if isinstance(v, float):
                vals.append(f"{v:{float_format[-2:]}}")
            else:
                vals.append(str(v))
        lines.append(" & ".join(vals) + r" \\")

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])

    return "\n".join(lines)


def generate_sla_compliance_table(
    results: dict[str, dict[str, float]],
    caption: str = "SLA compliance rates",
    label: str = "tab:sla",
) -> str:
    """Generate LaTeX table for SLA compliance results.

    results: {scenario_name: {latency_compliance, accuracy_compliance, overall_compliance}}
    """
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        r"\begin{tabular}{lrrr}",
        r"\toprule",
        r"Scenario & Latency (\%) & Accuracy (\%) & Overall (\%) \\",
        r"\midrule",
    ]

    for scenario, metrics in results.items():
        lat = metrics.get("latency_compliance", 0) * 100
        acc = metrics.get("accuracy_compliance", 0) * 100
        ovr = metrics.get("overall_compliance", 0) * 100
        name = scenario.replace("_", r"\_")
        lines.append(f"{name} & {lat:.1f} & {acc:.1f} & {ovr:.1f} \\\\")

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])

    return "\n".join(lines)


def format_metric_value(value: float, metric_name: str) -> str:
    """Format a metric value for display in tables."""
    if "time" in metric_name or "latency" in metric_name:
        return f"{value:.1f}"
    if "accuracy" in metric_name or "confidence" in metric_name or "compliance" in metric_name:
        return f"{value:.3f}"
    if "count" in metric_name:
        return f"{value:.0f}"
    return f"{value:.4f}"
