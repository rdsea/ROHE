"""Tier 2 quality evaluation: statistical anomaly detection.

Detects anomalous patterns in inference metrics using Isolation Forest
and Local Outlier Factor. Integrates with the ContractChecker by
producing anomaly scores that can be checked against CDM thresholds.

Usage:
  detector = AnomalyDetector(method="isolation_forest", contamination=0.05)
  scores = detector.fit_score(metric_values)
  anomaly_rate = detector.anomaly_rate(metric_values)
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Statistical anomaly detector for inference quality metrics.

    Wraps scikit-learn Isolation Forest and Local Outlier Factor
    behind a simple interface for the quality evaluation pipeline.
    """

    def __init__(
        self,
        method: str = "isolation_forest",
        contamination: float = 0.05,
        n_neighbors: int = 20,
        random_state: int = 42,
    ) -> None:
        self._method = method
        self._contamination = contamination
        self._n_neighbors = n_neighbors
        self._random_state = random_state
        self._model: Any = None

    def fit_score(self, values: list[float]) -> list[float]:
        """Fit detector and return anomaly scores for each value.

        Scores: negative = more anomalous, positive = more normal.
        """
        if len(values) < 5:
            return [0.0] * len(values)

        arr = np.array(values).reshape(-1, 1)

        if self._method == "isolation_forest":
            return self._isolation_forest_scores(arr)
        if self._method == "lof":
            return self._lof_scores(arr)
        raise ValueError(f"Unknown method: {self._method}")

    def detect(self, values: list[float]) -> list[bool]:
        """Detect anomalies. Returns True for anomalous values."""
        if len(values) < 5:
            return [False] * len(values)

        arr = np.array(values).reshape(-1, 1)

        if self._method == "isolation_forest":
            labels = self._isolation_forest_labels(arr)
        elif self._method == "lof":
            labels = self._lof_labels(arr)
        else:
            raise ValueError(f"Unknown method: {self._method}")

        return [label == -1 for label in labels]

    def anomaly_rate(self, values: list[float]) -> float:
        """Calculate the fraction of anomalous values."""
        if not values:
            return 0.0
        anomalies = self.detect(values)
        return sum(anomalies) / len(anomalies)

    def _isolation_forest_scores(self, arr: np.ndarray) -> list[float]:
        """Isolation Forest anomaly scores."""
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError:
            logger.warning("scikit-learn not available, returning zero scores")
            return [0.0] * len(arr)

        model = IsolationForest(
            contamination=self._contamination,
            random_state=self._random_state,
            n_estimators=100,
        )
        model.fit(arr)
        self._model = model
        return model.decision_function(arr).tolist()

    def _isolation_forest_labels(self, arr: np.ndarray) -> list[int]:
        """Isolation Forest anomaly labels (-1 = anomaly, 1 = normal)."""
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError:
            return [1] * len(arr)

        model = IsolationForest(
            contamination=self._contamination,
            random_state=self._random_state,
        )
        model.fit(arr)
        self._model = model
        return model.predict(arr).tolist()

    def _lof_scores(self, arr: np.ndarray) -> list[float]:
        """Local Outlier Factor anomaly scores."""
        try:
            from sklearn.neighbors import LocalOutlierFactor
        except ImportError:
            logger.warning("scikit-learn not available, returning zero scores")
            return [0.0] * len(arr)

        model = LocalOutlierFactor(
            n_neighbors=min(self._n_neighbors, len(arr) - 1),
            contamination=self._contamination,
        )
        model.fit_predict(arr)
        self._model = model
        return model.negative_outlier_factor_.tolist()

    def _lof_labels(self, arr: np.ndarray) -> list[int]:
        """Local Outlier Factor anomaly labels."""
        try:
            from sklearn.neighbors import LocalOutlierFactor
        except ImportError:
            return [1] * len(arr)

        model = LocalOutlierFactor(
            n_neighbors=min(self._n_neighbors, len(arr) - 1),
            contamination=self._contamination,
        )
        return model.fit_predict(arr).tolist()


class MetricAnomalyChecker:
    """Checks multiple metrics for anomalies and produces summary results.

    Used by QualityService to detect degradation patterns that
    rule-based thresholds might miss (e.g., gradual drift, sudden spikes).
    """

    def __init__(
        self,
        method: str = "isolation_forest",
        contamination: float = 0.05,
    ) -> None:
        self._detector = AnomalyDetector(method=method, contamination=contamination)

    def check_metrics(
        self,
        metrics_by_name: dict[str, list[float]],
    ) -> dict[str, dict[str, Any]]:
        """Check multiple metrics for anomalies.

        Returns: {metric_name: {anomaly_rate, anomaly_count, total, is_anomalous}}
        """
        results: dict[str, dict[str, Any]] = {}
        for name, values in metrics_by_name.items():
            if not values:
                continue
            rate = self._detector.anomaly_rate(values)
            anomalies = self._detector.detect(values)
            results[name] = {
                "anomaly_rate": round(rate, 4),
                "anomaly_count": sum(anomalies),
                "total": len(values),
                "is_anomalous": rate > self._detector._contamination * 2,
            }
        return results
