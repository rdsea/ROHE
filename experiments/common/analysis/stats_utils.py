"""Statistical analysis utilities for ROHE experiments.

Provides significance testing, confidence intervals, and summary statistics
for comparing orchestration algorithms and model ensembles.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    import numpy as np
    import pandas as pd
except ImportError:
    np = None  # type: ignore[assignment]
    pd = None  # type: ignore[assignment]


def compute_summary_stats(
    df: Any,  # pd.DataFrame
    metric: str,
    group_by: str,
) -> Any:  # pd.DataFrame
    """Compute summary statistics (mean, std, median, p50, p95, p99) per group."""
    if pd is None:
        raise ImportError("pandas required: pip install pandas")
    return df.groupby(group_by)[metric].agg([
        ("count", "count"),
        ("mean", "mean"),
        ("std", "std"),
        ("median", "median"),
        ("p50", lambda x: x.quantile(0.50)),
        ("p95", lambda x: x.quantile(0.95)),
        ("p99", lambda x: x.quantile(0.99)),
        ("min", "min"),
        ("max", "max"),
    ]).round(4)


def compute_significance(
    df: Any,  # pd.DataFrame
    metric: str,
    group_by: str,
    method: str = "mannwhitneyu",
) -> Any:  # pd.DataFrame
    """Compute pairwise statistical significance between groups.

    Returns a DataFrame with columns: group_a, group_b, statistic, p_value, significant.
    """
    if pd is None or np is None:
        raise ImportError("pandas and numpy required")

    try:
        from scipy import stats as sp_stats
    except ImportError:
        raise ImportError("scipy required for significance tests: pip install scipy")

    groups = df[group_by].unique()
    results: list[dict[str, Any]] = []

    for i, g_a in enumerate(groups):
        for g_b in groups[i + 1:]:
            vals_a = df[df[group_by] == g_a][metric].dropna().values
            vals_b = df[df[group_by] == g_b][metric].dropna().values

            if len(vals_a) < 2 or len(vals_b) < 2:
                continue

            if method == "mannwhitneyu":
                stat, p_val = sp_stats.mannwhitneyu(vals_a, vals_b, alternative="two-sided")
            elif method == "ttest":
                stat, p_val = sp_stats.ttest_ind(vals_a, vals_b)
            elif method == "ks":
                stat, p_val = sp_stats.ks_2samp(vals_a, vals_b)
            else:
                raise ValueError(f"Unknown method: {method}")

            results.append({
                "group_a": g_a,
                "group_b": g_b,
                "method": method,
                "statistic": round(stat, 4),
                "p_value": round(p_val, 6),
                "significant_005": p_val < 0.05,
                "significant_001": p_val < 0.01,
            })

    return pd.DataFrame(results)


def compute_confidence_interval(
    values: list[float],
    confidence: float = 0.95,
) -> tuple[float, float, float]:
    """Compute confidence interval for a list of values.

    Returns (mean, lower_bound, upper_bound).
    """
    if np is None:
        raise ImportError("numpy required")
    arr = np.array(values)
    n = len(arr)
    mean = float(np.mean(arr))
    if n < 2:
        return mean, mean, mean

    try:
        from scipy import stats as sp_stats
        se = float(sp_stats.sem(arr))
        h = se * sp_stats.t.ppf((1 + confidence) / 2, n - 1)
    except ImportError:
        se = float(np.std(arr, ddof=1) / np.sqrt(n))
        # Approximate z-value for 95% CI
        z = 1.96 if confidence == 0.95 else 2.576
        h = se * z

    return mean, mean - h, mean + h


def compute_sla_compliance(
    df: Any,  # pd.DataFrame
    latency_col: str = "response_time_ms",
    accuracy_col: str = "confidence",
    latency_threshold_ms: float = 300.0,
    accuracy_threshold: float = 0.80,
) -> dict[str, float]:
    """Compute SLA compliance rates."""
    if pd is None:
        raise ImportError("pandas required")
    total = len(df)
    if total == 0:
        return {"latency_compliance": 0.0, "accuracy_compliance": 0.0, "overall_compliance": 0.0}

    latency_ok = (df[latency_col] <= latency_threshold_ms).sum()
    accuracy_ok = (df[accuracy_col] >= accuracy_threshold).sum()
    both_ok = ((df[latency_col] <= latency_threshold_ms) & (df[accuracy_col] >= accuracy_threshold)).sum()

    return {
        "latency_compliance": round(latency_ok / total, 4),
        "accuracy_compliance": round(accuracy_ok / total, 4),
        "overall_compliance": round(both_ok / total, 4),
        "total_requests": total,
    }
