from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .metrics import Metric, RuntimePerformance

# Models with model_id/model_version fields need protected_namespaces=() to avoid
# Pydantic v2 warnings about the "model_" prefix conflicting with BaseModel internals.
_ML_MODEL_CONFIG = ConfigDict(protected_namespaces=())


class InferenceQuery(BaseModel):
    """A request for inference from a consumer."""

    metadata: dict[str, Any] = Field(..., description="Metadata about the consumer")
    data_source: list[str] = Field(..., description="Data sources for the inference query")
    time_window: int = Field(..., description="Time window for the inference query")
    explainability: bool = Field(..., description="Whether to include explainability")
    constraint: dict[str, Any] = Field(..., description="Constraints for the inference query")
    query_id: str | None = Field(None, description="Unique identifier for the query")

    def get_response_time(self) -> float | None:
        return self.constraint.get("response_time", None)


class MonitoringReport(BaseModel):
    """A monitoring report from an inference service instance."""

    model_config = _ML_MODEL_CONFIG

    metadata: dict[str, Any] | None = Field(None, description="Report metadata")
    query_id: str = Field(..., description="Unique identifier for the query")
    inf_id: str | None = Field(None, description="Inference ID")
    inf_time: float = Field(..., description="Inference time in seconds")
    data_source: list[str] | str | None = Field(..., description="Data sources used")
    time_window: float | None = Field(None, description="Time window for the inference")
    model_id: str = Field(..., description="Model ID used")
    device_id: str = Field(..., description="Device ID used")
    instance_id: str = Field(..., description="Instance ID")
    response_time: float = Field(..., description="Response time in seconds")
    inf_result: dict[str, float] = Field(..., description="Inference result data")
    model_version: str | None = Field(None, description="Model version")
    explainability: bool | None = Field(False, description="Whether explainability is included")
    time_violation: bool | None = Field(False, description="Whether time was violated")
    time_for_inference: float | None = Field(None, description="Remaining time for inference")


class InferenceServiceProfile(BaseModel):
    """Profile of an ML inference service (model + hardware combination)."""

    model_config = _ML_MODEL_CONFIG

    metadata: dict[str, Any] | None = Field(None, description="Service metadata")
    inference_service_id: str = Field(..., description="Unique service identifier")
    model_id: str = Field(..., description="Model ID")
    model_version: str | None = Field(None, description="Model version")
    device_type: str = Field(..., description="Device type (e.g. 'jetson-nano', 'gpu-a100')")
    base_line: list[Metric] = Field(..., description="Baseline performance metrics")
    inference_performance: RuntimePerformance | None = Field(None, description="Runtime performance")
    instance_list: list[str] = Field(..., description="List of instance_ids")
    specialized_class: list[str] | None = Field(None, description="Specialized classes")
    modality: str | None = Field(None, description="Modality: 'image', 'text', 'video', etc.")

    @classmethod
    def from_dict(cls: type[InferenceServiceProfile], data: dict[str, Any]) -> InferenceServiceProfile:
        if "base_line" in data and isinstance(data["base_line"], list):
            data["base_line"] = [Metric(**item) if isinstance(item, dict) else item for item in data["base_line"]]
        if "inference_performance" in data and isinstance(data["inference_performance"], dict):
            data["inference_performance"] = RuntimePerformance.from_dict(data["inference_performance"])
        return cls.model_validate(data)


class InferenceServiceInstance(BaseModel):
    """A running instance of an inference service on a specific device."""

    model_config = _ML_MODEL_CONFIG

    instance_id: str = Field(..., description="Unique instance identifier")
    model_id: str | None = Field(..., description="Model ID")
    model_version: str | None = Field(None, description="Model version")
    device_id: str = Field(..., description="Device ID where instance runs")
    ip_address: str = Field(..., description="IP address of the device")
    port: int = Field(..., description="Port number")
    runtime_performance: list[Metric] = Field(..., description="Runtime performance metrics")
    modality: str | None = Field(None, description="Modality")
    device_type: str | None = Field(None, description="Device type")
    inference_service_id: str | None = Field(None, description="Parent service ID")
    status: str | None = Field(None, description="Instance status: active, inactive, error, contention")
    inference_url: str | None = Field(None, description="URL for inference requests")

    @classmethod
    def from_dict(cls: type[InferenceServiceInstance], data: dict[str, Any]) -> InferenceServiceInstance:
        if "runtime_performance" in data and isinstance(data["runtime_performance"], list):
            data["runtime_performance"] = [
                Metric(**item) if isinstance(item, dict) else item for item in data["runtime_performance"]
            ]
        return cls.model_validate(data)


class InferenceResult(BaseModel):
    """Aggregated result from one or more inference service instances."""

    inference_time: float | None = Field(0.0, description="Inference time in seconds")
    data: dict[str, float] = Field(default_factory=dict, description="Class name -> confidence score")
    query_id: list[str] | str | None = Field(None, description="Query ID(s)")
    task_id: list[str] = Field(default_factory=list, description="Task IDs")
    inf_id: list[str] = Field(default_factory=list, description="Inference IDs")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Result metadata")

    def to_dict(self) -> dict[str, Any]:
        return {
            "inference_time": self.inference_time,
            "data": self.data,
            "query_id": self.query_id[0] if isinstance(self.query_id, list) and self.query_id else self.query_id,
            "task_id": str(self.task_id),
            "inf_id": str(self.inf_id),
            "metadata": self.metadata,
        }

    def get_top_k_predictions(self, top_k: int = 5) -> list[str]:
        sorted_items = sorted(self.data.items(), key=lambda item: item[1], reverse=True)[:top_k]
        return [key for key, _ in sorted_items]

    def get_worst_k_predictions(self, worst_k: int = 5) -> list[str]:
        sorted_items = sorted(self.data.items(), key=lambda item: item[1])[:worst_k]
        return [key for key, _ in sorted_items]

    def aggregate(self, other: InferenceResult, avg_flag: bool = False) -> InferenceResult:
        """Aggregate another InferenceResult into this one."""
        if not isinstance(other, InferenceResult):
            raise ValueError("other must be an instance of InferenceResult")
        if self.query_id is None:
            self.query_id = other.query_id
        self.inference_time = time.perf_counter()
        self.task_id = list(set(self.task_id + other.task_id))
        self.inf_id = list(set(self.inf_id + other.inf_id))

        all_classes = set(self.data.keys()) | set(other.data.keys())
        aggregate_data: dict[str, float] = {}
        for class_name in all_classes:
            combined = self.data.get(class_name, 0.0) + other.data.get(class_name, 0.0)
            aggregate_data[class_name] = combined / 2 if avg_flag else combined
        self.data = aggregate_data
        return self

    def get_avg_from_aggregated_sum(self) -> None:
        n_inf = len(self.inf_id)
        if n_inf == 0:
            return
        self.data = {class_name: value / n_inf for class_name, value in self.data.items()}

    def sort_inference_result(self) -> None:
        self.data = dict(sorted(self.data.items(), key=lambda item: item[1], reverse=True))


class InferenceTask(BaseModel):
    """A single inference task within a pipeline execution."""

    task_id: str = Field(..., description="Unique identifier (inf_id)")
    modality: str | None = Field(None, description="Modality: 'image', 'text', 'video'")
    allocated_time: float | None = Field(None, description="Allocated time in seconds")
    min_execution_time: float | None = Field(None, description="Min execution time in seconds")
    max_execution_time: float | None = Field(None, description="Max execution time in seconds")
    min_execution_time_ex: float | None = Field(None, description="Min exec time for explainability")
    max_execution_time_ex: float | None = Field(None, description="Max exec time for explainability")
    inference_services: dict[str, Any] | None = Field(default_factory=dict, description="Available inference services")
    inference_instances: dict[str, Any] | None = Field(default_factory=dict, description="Available inference instances")
    inference_services_ex: dict[str, Any] | None = Field(default_factory=dict, description="Explainability services")
    inference_instances_ex: dict[str, Any] | None = Field(default_factory=dict, description="Explainability instances")
    status: str | None = Field(None, description="Task status")
    phase: int | None = Field(0, description="Execution phase")
    inference_query: InferenceQuery | None = Field(None, description="Associated inference query")
    selected_instances: list[InferenceServiceInstance] = Field(default_factory=list, description="Selected instances")
    selected_instances_ex: list[InferenceServiceInstance] = Field(
        default_factory=list, description="Selected explainability instances"
    )
    ensemble_size: int | None = Field(1, description="Ensemble size")
    ensemble_selection_strategy: str | None = Field("enhance_confidence", description="Ensemble strategy")
    test_mode: bool | None = Field(True, description="Whether in test mode")
    monitoring_client: Any | None = Field(None, description="Monitoring client")
    explainability: bool | None = Field(False, description="Whether explainability is enabled")


class TaskList(BaseModel):
    """Collection of inference tasks."""

    data: list[InferenceTask] = Field(default_factory=list, description="List of tasks")

    def get_task_info(self, task_id: str) -> InferenceTask | None:
        for task in self.data:
            if task.task_id == task_id:
                return task
        return None

    def add_task(self, inf_task: InferenceTask) -> None:
        if self.get_task_info(inf_task.task_id) is not None:
            raise ValueError(f"Task with ID {inf_task.task_id} already exists")
        self.data.append(inf_task)

    def get_list_modality(self) -> list[str]:
        return [task.modality for task in self.data if task.modality is not None]


class InferenceFeedback(BaseModel):
    """Ground truth feedback for an inference query."""

    query_id: str = Field(..., description="Query ID")
    ground_truth: str = Field(..., description="Ground truth label")
