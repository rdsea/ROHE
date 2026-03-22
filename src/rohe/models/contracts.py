from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class MetricThreshold(BaseModel):
    """Threshold definition for a metric in a service contract."""

    model_config = ConfigDict(frozen=True)

    operator: Literal["<", "<=", ">", ">=", "==", "!="]
    value: float
    window: str | None = Field(None, description="Evaluation window, e.g. '5m'")
    action_on_violation: Literal["alert", "degrade", "reroute", "reject"] = "alert"

    def is_violated(self, actual_value: float) -> bool:
        """Check if the actual value violates this threshold.

        A threshold is violated when the condition is NOT met.
        E.g., operator=">=" value=0.95 means "must be >= 0.95",
        so actual_value=0.90 violates (returns True).
        """
        is_satisfied = {
            "<": lambda a, t: a < t,
            "<=": lambda a, t: a <= t,
            ">": lambda a, t: a > t,
            ">=": lambda a, t: a >= t,
            "==": lambda a, t: a == t,
            "!=": lambda a, t: a != t,
        }
        return not is_satisfied[self.operator](actual_value, self.value)


class PerformanceSLO(BaseModel):
    """Performance targets in a service contract."""

    model_config = ConfigDict(frozen=True)

    response_time_p50_ms: float | None = None
    response_time_p99_ms: float | None = None
    throughput_rps: float | None = None
    availability_percent: float | None = None


class QualitySLO(BaseModel):
    """Quality targets in a service contract, including CDM thresholds."""

    model_config = ConfigDict(frozen=True)

    builtin_metrics: dict[str, MetricThreshold] | None = None
    cdm_thresholds: dict[str, MetricThreshold] | None = None


class ServiceContract(BaseModel):
    """Formal SLA/SLO agreement between tenant and platform."""

    model_config = ConfigDict(frozen=True)

    contract_id: str
    tenant_id: str
    pipeline_id: str
    effective_from: datetime
    effective_until: datetime | None = None
    performance_slo: PerformanceSLO
    quality_slo: QualitySLO

    def is_active(self, now: datetime | None = None) -> bool:
        """Check if the contract is currently active."""
        if now is None:
            now = datetime.now()
        if now < self.effective_from:
            return False
        return not (self.effective_until is not None and now > self.effective_until)


class ServiceLevelIndicator(BaseModel):
    """Individual SLI within a ServiceLevelAgreement (legacy model, kept for compatibility)."""

    metric_name: str = Field(..., description="Name of the service level indicator")
    target_value: float | list[float] | None = Field(None, description="Target value(s)")
    operator: str | None = Field(None, description="Operator: '>', '<', '=='")
    objective_type: str | None = Field(None, description="'minimize' or 'maximize'")
    condition: str | None = Field(None, description="Condition, e.g. confidence threshold")
    class_id: str | None = Field(None, description="Class id if applicable")


class ServiceLevelAgreement(BaseModel):
    """Legacy SLA model used by orchestration algorithms. Kept for backward compatibility."""

    sla_id: str = Field(..., description="Unique identifier for the SLA")
    tenant_id: str = Field(..., description="Tenant ID")
    access_privileges: list[str] = Field(..., description="Data sources the tenant can access")
    service_level_indicators: list[ServiceLevelIndicator] = Field(..., description="SLIs for the SLA")
    consumer_list: list[str] | None = Field(None, description="Consumers associated with the SLA")
    ensemble_size: int | None = Field(1, description="Ensemble size for inferences")
    ensemble_selection_strategy: str | None = Field("enhance_confidence", description="Ensemble selection strategy")

    @classmethod
    def from_dict(cls: type[ServiceLevelAgreement], data: dict[str, Any]) -> ServiceLevelAgreement:
        if "service_level_indicators" in data and isinstance(data["service_level_indicators"], list):
            data["service_level_indicators"] = [
                ServiceLevelIndicator(**item) if isinstance(item, dict) else item
                for item in data["service_level_indicators"]
            ]
        return cls.model_validate(data)
