"""Publication-quality plot utilities for ROHE experiments.

Provides consistent styling, figure generation, and export for
scientific papers (IEEE, ACM, Springer formats).
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

logger = logging.getLogger(__name__)

try:
    import matplotlib
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    plt = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]

# Publication-quality defaults
PAPER_RC = {
    "font.family": "serif",
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "legend.fontsize": 9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
    "lines.linewidth": 1.5,
    "lines.markersize": 5,
    "axes.grid": True,
    "grid.alpha": 0.3,
}

# Color palettes for different numbers of series
PALETTES = {
    "default": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"],
    "paired": ["#a6cee3", "#1f78b4", "#b2df8a", "#33a02c", "#fb9a99", "#e31a1c", "#fdbf6f", "#ff7f00"],
}


@contextmanager
def paper_style(rc_overrides: dict[str, Any] | None = None) -> Generator[None, None, None]:
    """Context manager for publication-quality matplotlib style."""
    if plt is None:
        raise ImportError("matplotlib required: pip install matplotlib")
    rc = {**PAPER_RC, **(rc_overrides or {})}
    with plt.rc_context(rc):
        yield


def save_figure(
    fig: Any,
    path: str | Path,
    formats: list[str] | None = None,
) -> list[Path]:
    """Save figure in multiple formats (default: PDF + PNG)."""
    if formats is None:
        formats = ["pdf", "png"]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    saved: list[Path] = []
    for fmt in formats:
        out = path.with_suffix(f".{fmt}")
        fig.savefig(out)
        saved.append(out)
        logger.info(f"Saved figure: {out}")
    plt.close(fig)
    return saved


def plot_latency_cdf(
    data: dict[str, list[float]],
    title: str = "Response Time CDF",
    xlabel: str = "Response Time (ms)",
    output_path: str | Path | None = None,
) -> Any:
    """Plot CDF of response times for multiple algorithms/models."""
    with paper_style():
        fig, ax = plt.subplots(figsize=(6, 4))
        colors = PALETTES["default"]
        for i, (label, values) in enumerate(data.items()):
            sorted_vals = sorted(values)
            cdf = [(j + 1) / len(sorted_vals) for j in range(len(sorted_vals))]
            ax.plot(sorted_vals, cdf, label=label, color=colors[i % len(colors)])
        ax.set_xlabel(xlabel)
        ax.set_ylabel("CDF")
        ax.set_title(title)
        ax.legend()
        if output_path:
            save_figure(fig, output_path)
        return fig


def plot_accuracy_boxplot(
    data: dict[str, list[float]],
    title: str = "Accuracy Distribution",
    ylabel: str = "Accuracy",
    output_path: str | Path | None = None,
) -> Any:
    """Box plot of accuracy across algorithms/models."""
    with paper_style():
        fig, ax = plt.subplots(figsize=(6, 4))
        labels = list(data.keys())
        values = [data[k] for k in labels]
        bp = ax.boxplot(values, labels=labels, patch_artist=True)
        colors = PALETTES["default"]
        for i, patch in enumerate(bp["boxes"]):
            patch.set_facecolor(colors[i % len(colors)])
            patch.set_alpha(0.7)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        if output_path:
            save_figure(fig, output_path)
        return fig


def plot_tradeoff_scatter(
    x_data: dict[str, float],
    y_data: dict[str, float],
    xlabel: str = "Response Time (ms)",
    ylabel: str = "Accuracy (%)",
    title: str = "Latency-Accuracy Tradeoff",
    output_path: str | Path | None = None,
) -> Any:
    """Scatter plot showing tradeoff between two metrics."""
    with paper_style():
        fig, ax = plt.subplots(figsize=(6, 4))
        colors = PALETTES["default"]
        for i, key in enumerate(x_data.keys()):
            ax.scatter(x_data[key], y_data[key], label=key,
                       color=colors[i % len(colors)], s=80, zorder=5)
            ax.annotate(key, (x_data[key], y_data[key]),
                        textcoords="offset points", xytext=(5, 5), fontsize=8)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        if output_path:
            save_figure(fig, output_path)
        return fig


def plot_model_heatmap(
    data: dict[str, dict[str, float]],
    title: str = "Model Selection Frequency",
    xlabel: str = "Model",
    ylabel: str = "Scenario",
    output_path: str | Path | None = None,
) -> Any:
    """Heatmap showing model selection frequency across scenarios."""
    with paper_style():
        scenarios = list(data.keys())
        models = sorted({m for s in data.values() for m in s.keys()})
        matrix = [[data[s].get(m, 0.0) for m in models] for s in scenarios]

        fig, ax = plt.subplots(figsize=(max(6, len(models) * 0.8), max(4, len(scenarios) * 0.6)))
        im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto")
        ax.set_xticks(range(len(models)))
        ax.set_xticklabels(models, rotation=45, ha="right")
        ax.set_yticks(range(len(scenarios)))
        ax.set_yticklabels(scenarios)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        fig.colorbar(im, ax=ax, shrink=0.8)
        if output_path:
            save_figure(fig, output_path)
        return fig
