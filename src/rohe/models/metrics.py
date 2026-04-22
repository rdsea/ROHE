from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class MetricExpression(BaseModel):
    """Expression tree node for composable CDM evaluation.

    Supports: count, sum, avg, min, max, percentile, ratio, cdm_ref.
    Composition via operands list enables arbitrary metric aggregation.
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["count", "sum", "avg", "min", "max", "percentile", "ratio", "cdm_ref"]
    filters: dict[str, str] | None = None
    operands: list[MetricExpression] | None = None
    cdm_ref: str | None = None
    percentile_value: float | None = None

    def is_leaf(self) -> bool:
        return self.operands is None or len(self.operands) == 0

    def references_cdm(self) -> set[str]:
        """Collect all CDM names referenced in this expression tree."""
        refs: set[str] = set()
        if self.type == "cdm_ref" and self.cdm_ref is not None:
            refs.add(self.cdm_ref)
        if self.operands:
            for operand in self.operands:
                refs.update(operand.references_cdm())
        return refs


class CDMDefinition(BaseModel):
    """Consumer-Defined Metric: a composable, tenant-defined quality metric."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Unique identifier, e.g. 'error_rate_human_car'")
    metric_type: Literal["per_request", "per_period"]
    expression: MetricExpression
    window: str | None = Field(
        None, description="Evaluation window, e.g. '5m', '1h'. Required for per_period."
    )
    description: str | None = None


class Metric(BaseModel):
    """A single measured metric value."""

    metric_name: str = Field(..., description="Name of the metric")
    value: float = Field(..., description="Value of the metric")
    unit: str | None = Field(None, description="Unit of the metric value")
    condition: str | None = Field(
        None, description="Condition, e.g. confidence threshold"
    )
    class_id: str | None = Field(
        None,
        description="Optional class identifier for class-specific metrics (e.g., per-class accuracy).",
    )

    @classmethod
    def from_dict(cls: type[Metric], data: dict[str, Any]) -> Metric:
        return cls.model_validate(data)


class ClassSpecificMetric(BaseModel):
    """Performance metrics for a specific class."""

    class_name: str = Field(..., description="Name of the class")
    performance: list[Metric] = Field(
        ..., description="Class-specific performance metrics"
    )

    @classmethod
    def from_dict(
        cls: type[ClassSpecificMetric], data: dict[str, Any]
    ) -> ClassSpecificMetric:
        if "performance" in data and isinstance(data["performance"], list):
            data["performance"] = [
                Metric(**item) if isinstance(item, dict) else item
                for item in data["performance"]
            ]
        return cls.model_validate(data)


class RuntimePerformance(BaseModel):
    """Runtime performance breakdown: overall + per-class."""

    overall_performance: list[Metric] | None = Field(
        None, description="Overall performance metrics"
    )
    class_specific_performance: list[ClassSpecificMetric] | None = Field(
        None, description="Per-class performance metrics"
    )

    @classmethod
    def from_dict(
        cls: type[RuntimePerformance], data: dict[str, Any]
    ) -> RuntimePerformance:
        if "overall_performance" in data and isinstance(
            data["overall_performance"], list
        ):
            data["overall_performance"] = [
                Metric(**item) if isinstance(item, dict) else item
                for item in data["overall_performance"]
            ]
        if "class_specific_performance" in data and isinstance(
            data["class_specific_performance"], list
        ):
            data["class_specific_performance"] = [
                ClassSpecificMetric.from_dict(item) if isinstance(item, dict) else item
                for item in data["class_specific_performance"]
            ]
        return cls.model_validate(data)
