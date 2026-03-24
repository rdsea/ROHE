from __future__ import annotations

import logging
import statistics
from typing import Any

from rohe.models.metrics import CDMDefinition, MetricExpression

logger = logging.getLogger(__name__)


class CycleError(ValueError):
    """Raised when a CDM reference cycle is detected."""


class ExpressionEvaluator:
    """Evaluates CDM expression trees against raw metric data.

    Traverses MetricExpression trees recursively, computing results from
    raw metric records. Supports count, sum, avg, min, max, percentile,
    ratio, and cdm_ref node types.

    CDM references are resolved via a registry of CDMDefinitions, with
    cycle detection to prevent infinite recursion.
    """

    def __init__(self, cdm_registry: dict[str, CDMDefinition] | None = None) -> None:
        self._cdm_registry: dict[str, CDMDefinition] = cdm_registry or {}

    def register_cdm(self, cdm: CDMDefinition) -> None:
        """Register a CDM definition for cdm_ref resolution."""
        self._cdm_registry[cdm.name] = cdm

    def evaluate(
        self,
        expression: MetricExpression,
        metrics: list[dict[str, Any]],
        _visited: set[str] | None = None,
    ) -> float:
        """Evaluate an expression tree against a list of metric records.

        Args:
            expression: The expression tree to evaluate.
            metrics: Raw metric records (list of dicts).
            _visited: Internal set for cycle detection in cdm_ref chains.

        Returns:
            The computed float value.

        Raises:
            CycleError: If a cdm_ref cycle is detected.
            ValueError: If expression type is unknown or evaluation fails.
        """
        if _visited is None:
            _visited = set()

        if expression.type == "cdm_ref":
            return self._eval_cdm_ref(expression, metrics, _visited)

        filtered = self._apply_filters(metrics, expression.filters)

        if expression.type == "count":
            return float(len(filtered))

        if expression.type == "ratio":
            return self._eval_ratio(expression, metrics, _visited)

        values = self._extract_values(filtered)

        if expression.type == "sum":
            return sum(values) if values else 0.0

        if expression.type == "avg":
            return statistics.mean(values) if values else 0.0

        if expression.type == "min":
            return min(values) if values else 0.0

        if expression.type == "max":
            return max(values) if values else 0.0

        if expression.type == "percentile":
            return self._eval_percentile(values, expression.percentile_value)

        raise ValueError(f"Unknown expression type: {expression.type}")

    def _eval_cdm_ref(
        self,
        expression: MetricExpression,
        metrics: list[dict[str, Any]],
        visited: set[str],
    ) -> float:
        """Resolve a cdm_ref by looking up and evaluating the referenced CDM."""
        cdm_name = expression.cdm_ref
        if cdm_name is None:
            raise ValueError("cdm_ref expression must have cdm_ref field set")

        if cdm_name in visited:
            raise CycleError(
                f"CDM reference cycle detected: {cdm_name} already visited in {visited}"
            )

        cdm = self._cdm_registry.get(cdm_name)
        if cdm is None:
            raise ValueError(f"CDM '{cdm_name}' not found in registry")

        visited.add(cdm_name)
        result = self.evaluate(cdm.expression, metrics, visited)
        visited.discard(cdm_name)
        return result

    def _eval_ratio(
        self,
        expression: MetricExpression,
        metrics: list[dict[str, Any]],
        visited: set[str],
    ) -> float:
        """Evaluate a ratio expression: operands[0] / operands[1]."""
        if not expression.operands or len(expression.operands) != 2:
            raise ValueError("Ratio expression requires exactly 2 operands")

        numerator = self.evaluate(expression.operands[0], metrics, visited)
        denominator = self.evaluate(expression.operands[1], metrics, visited)

        if denominator == 0.0:
            logger.warning("Division by zero in ratio expression, returning 0.0")
            return 0.0

        return numerator / denominator

    @staticmethod
    def _eval_percentile(values: list[float], percentile_value: float | None) -> float:
        """Compute percentile from a list of values."""
        if not values:
            return 0.0
        if percentile_value is None:
            raise ValueError("Percentile expression requires percentile_value")

        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * percentile_value
        f = int(k)
        c = f + 1
        if c >= len(sorted_values):
            return sorted_values[-1]
        return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])

    @staticmethod
    def _apply_filters(
        metrics: list[dict[str, Any]],
        filters: dict[str, str] | None,
    ) -> list[dict[str, Any]]:
        """Filter metrics by key-value pairs."""
        if not filters:
            return metrics
        return [
            m for m in metrics if all(str(m.get(k)) == v for k, v in filters.items())
        ]

    @staticmethod
    def _extract_values(
        metrics: list[dict[str, Any]], field: str = "value"
    ) -> list[float]:
        """Extract numeric values from filtered metrics."""
        values: list[float] = []
        for m in metrics:
            v = m.get(field)
            if v is not None:
                try:
                    values.append(float(v))
                except (ValueError, TypeError):
                    continue
        return values
