"""ExecutionPlan models for orchestrator-managed inference pipelines.

The ExecutionPlan is the central data structure that defines how a pipeline
processes requests. It specifies per-modality ensembles (which models to call),
preprocessing steps, execution phases, and aggregation strategy.

The orchestrator owns and mutates ExecutionPlans at runtime to maintain
inference quality. Plans are persisted to Redis for crash recovery and
horizontal scaling.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# Leaf models are frozen (immutable) -- the orchestrator replaces them, not mutates them.

class EnsembleMember(BaseModel):
    """A single inference service instance within a modality's ensemble."""

    model_config = ConfigDict(frozen=True, protected_namespaces=())

    service_id: str = Field(..., description="Service name, e.g. 'x3d_s'")
    instance_id: str = Field(..., description="Unique instance, e.g. 'x3d_s-instance-01'")
    inference_url: str = Field(..., description="HTTP endpoint for inference")
    model_id: str = Field(..., description="Model identifier")
    device_type: str = Field(..., description="Hardware: 'gpu', 'cpu'")
    weight: float = Field(1.0, description="Weight for weighted aggregation")
    is_active: bool = Field(True, description="Whether this member is currently active")


class PreprocessorSpec(BaseModel):
    """Specification for a preprocessing service within a modality."""

    model_config = ConfigDict(frozen=True)

    service_url: str = Field(..., description="HTTP endpoint for preprocessing")
    preprocessor_id: str = Field(..., description="Preprocessor identifier")
    output_data_key: str = Field(
        ..., description="DataHub key for preprocessed output, e.g. 'video_preprocessed'"
    )


class PhaseCondition(BaseModel):
    """Condition that determines whether a conditional execution phase runs."""

    model_config = ConfigDict(frozen=True)

    trigger: str = Field(..., description="Condition type: 'confidence_below', 'agreement_below'")
    threshold: float = Field(..., description="Threshold value for the trigger")
    source_modalities: list[str] = Field(
        ..., description="Modalities from previous phases to evaluate"
    )


class ExecutionPhase(BaseModel):
    """A phase in the execution plan -- groups modalities that run concurrently."""

    model_config = ConfigDict(frozen=True)

    phase_id: int = Field(..., description="Phase order: 0, 1, 2...")
    modalities: list[str] = Field(..., description="Modalities to execute in this phase")
    is_conditional: bool = Field(False, description="Whether this phase depends on previous results")
    condition: PhaseCondition | None = Field(
        None, description="Condition for conditional phases"
    )


# Container models are MUTABLE -- the orchestrator updates them at runtime.

class ModalityEnsemble(BaseModel):
    """Ensemble configuration for a single modality within a pipeline.

    The orchestrator mutates this at runtime to maintain quality:
    - Add/remove ensemble members
    - Change selection strategy
    - Adjust time budget fractions
    """

    modality: str = Field(..., description="Modality name: 'video', 'acc_phone', 'timeseries', etc.")
    preprocessor: PreprocessorSpec | None = Field(
        None, description="Preprocessor for this modality (None to skip)"
    )
    ensemble_members: list[EnsembleMember] = Field(
        default_factory=list, description="Inference service instances in this ensemble"
    )
    selection_strategy: str = Field(
        "enhance_confidence", description="Ensemble selection strategy"
    )
    ensemble_size: int = Field(3, description="Max members to invoke per request")
    aggregation_strategy: str = Field(
        "confidence_weighted", description="Aggregation strategy for this modality"
    )
    time_budget_fraction: float = Field(
        0.5, description="Fraction of total time budget allocated to this modality"
    )

    def get_active_members(self) -> list[EnsembleMember]:
        """Return only active ensemble members."""
        return [m for m in self.ensemble_members if m.is_active]


class ExecutionPlan(BaseModel):
    """Complete execution plan for an inference pipeline.

    The orchestrator loads this from Redis on startup and mutates it at runtime.
    Each mutation increments `version` for cache invalidation and audit.
    """

    pipeline_id: str = Field(..., description="Pipeline identifier, e.g. 'bts', 'smart-building'")
    version: int = Field(0, description="Monotonically increasing version number")
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp",
    )
    orchestration_algorithm: str = Field(
        "v2",
        description="Orchestration algorithm: v2, adaptive, dream, llf",
    )
    modality_ensembles: dict[str, ModalityEnsemble] = Field(
        default_factory=dict, description="Per-modality ensemble configurations"
    )
    execution_phases: list[ExecutionPhase] = Field(
        default_factory=list, description="Ordered execution phases"
    )
    aggregator_url: str = Field(
        "http://aggregator:8000/aggregate", description="Aggregator service endpoint"
    )
    data_hub_url: str = Field(
        "http://data-hub:8000", description="DataHub service endpoint"
    )

    # -- Mutation methods (increment version on every change) --

    def _bump_version(self) -> None:
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)

    def add_member(self, modality: str, member: EnsembleMember) -> None:
        """Add an ensemble member to a modality."""
        if modality not in self.modality_ensembles:
            raise ValueError(f"Modality '{modality}' not found in plan")
        ensemble = self.modality_ensembles[modality]
        if any(m.instance_id == member.instance_id for m in ensemble.ensemble_members):
            raise ValueError(f"Instance '{member.instance_id}' already exists in '{modality}'")
        ensemble.ensemble_members.append(member)
        self._bump_version()

    def remove_member(self, modality: str, instance_id: str) -> None:
        """Remove an ensemble member by instance_id."""
        if modality not in self.modality_ensembles:
            raise ValueError(f"Modality '{modality}' not found in plan")
        ensemble = self.modality_ensembles[modality]
        original_count = len(ensemble.ensemble_members)
        ensemble.ensemble_members = [
            m for m in ensemble.ensemble_members if m.instance_id != instance_id
        ]
        if len(ensemble.ensemble_members) == original_count:
            raise ValueError(f"Instance '{instance_id}' not found in '{modality}'")
        self._bump_version()

    def replace_member(
        self, modality: str, old_instance_id: str, new_member: EnsembleMember
    ) -> None:
        """Atomically replace an ensemble member."""
        self.remove_member(modality, old_instance_id)
        self.add_member(modality, new_member)
        # remove_member and add_member each bump version; that's fine

    def set_member_active(self, modality: str, instance_id: str, *, is_active: bool) -> None:
        """Activate or deactivate an ensemble member."""
        if modality not in self.modality_ensembles:
            raise ValueError(f"Modality '{modality}' not found in plan")
        for i, member in enumerate(self.modality_ensembles[modality].ensemble_members):
            if member.instance_id == instance_id:
                # Frozen model -- replace with new instance
                self.modality_ensembles[modality].ensemble_members[i] = EnsembleMember(
                    **{**member.model_dump(), "is_active": is_active}
                )
                self._bump_version()
                return
        raise ValueError(f"Instance '{instance_id}' not found in '{modality}'")

    def get_phase_modalities(self, phase_id: int) -> list[str]:
        """Get modalities for a given execution phase."""
        for phase in self.execution_phases:
            if phase.phase_id == phase_id:
                return phase.modalities
        return []

    def to_redis_value(self) -> str:
        """Serialize to JSON string for Redis storage."""
        return self.model_dump_json()

    @classmethod
    def from_redis_value(cls, value: str) -> ExecutionPlan:
        """Deserialize from Redis JSON string."""
        return cls.model_validate_json(value)

    @classmethod
    def from_yaml_file(cls, path: str) -> ExecutionPlan:
        """Load from a YAML file (for initial bootstrap)."""
        import yaml  # noqa: PLC0415 -- deferred import, yaml is optional
        from pathlib import Path

        data: dict[str, Any] = yaml.safe_load(Path(path).read_text())
        return cls.model_validate(data)
