"""Shared request/response schemas for all example applications."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class PredictRequest(BaseModel):
    """Standard prediction request. Data is opaque -- only the model inspects it."""

    query_id: str
    data: Any


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
