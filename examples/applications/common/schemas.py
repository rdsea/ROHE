"""Shared request/response schemas for all example applications."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class PredictRequest(BaseModel):
    """Standard prediction request. Data is opaque -- only the model inspects it."""

    query_id: str
    data: Any


class InferenceTaskRequest(BaseModel):
    """Request from orchestrator to an inference service via data references.

    The inference service fetches its input from DataHub using the data reference,
    runs inference, and returns the result. No actual data is in this request.
    """

    model_config = ConfigDict(protected_namespaces=())

    query_id: str
    inf_id: str  # unique task ID assigned by orchestrator
    modality: str
    data_key: str  # key to fetch from DataHub (e.g. "timeseries_normalized")
    data_hub_url: str  # DataHub base URL
    instance_id: str
    model_id: str  # noqa: N815 -- matches existing naming in pipeline models
    device_id: str = ""


class PreprocessTaskRequest(BaseModel):
    """Request from orchestrator to a preprocessor service via data references.

    The preprocessor fetches raw data from DataHub, processes it, and stores
    the result back to DataHub under output_data_key.
    """

    query_id: str
    modality: str
    data_key: str  # key to fetch raw data from DataHub
    output_data_key: str  # key to store preprocessed result in DataHub
    data_hub_url: str


class PreprocessTaskResponse(BaseModel):
    """Response from a preprocessor after storing result in DataHub."""

    model_config = ConfigDict(frozen=True)

    query_id: str
    output_data_key: str
    status: str  # "ok" or "error"


class OrchestrateRequest(BaseModel):
    """Control message from gateway to orchestrator."""

    query_id: str
    pipeline_id: str
    modalities: list[str] = []
    time_constraint_ms: float = 500.0
    data_hub_url: str = ""


class OrchestrateResponse(BaseModel):
    """Response from orchestrator to gateway with final result."""

    model_config = ConfigDict(frozen=True, protected_namespaces=())

    query_id: str
    ensemble_result: dict[str, float]
    individual_results: list[InferenceResponse] = []
    model_count: int = 0


class InferenceResponse(BaseModel):
    """Standard response from any inference service."""

    model_config = ConfigDict(frozen=True, protected_namespaces=())

    query_id: str
    predictions: dict[str, float]
    confidence: float
    model: str
    response_time_ms: float
    modality: str | None = None


class AggregateRequest(BaseModel):
    """Request to aggregate results from multiple models."""

    query_id: str
    results: list[InferenceResponse]
    strategy: str = "confidence_avg"


class AggregateResponse(BaseModel):
    """Response from aggregation service."""

    model_config = ConfigDict(frozen=True, protected_namespaces=())

    query_id: str
    ensemble_predictions: dict[str, float]
    avg_confidence: float
    model_count: int
    strategy: str


class GatewayResponse(BaseModel):
    """Response from gateway service."""

    model_config = ConfigDict(frozen=True, protected_namespaces=())

    query_id: str
    ensemble_result: dict[str, float]
    individual_results: list[InferenceResponse]
    model_count: int
