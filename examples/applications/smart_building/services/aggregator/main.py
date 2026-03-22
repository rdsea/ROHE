"""Aggregator service: combines multi-modal results from inference services."""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Multi-Modal Aggregator Service")


class InferenceResult(BaseModel):
    query_id: str
    predictions: dict[str, float]
    confidence: float
    model: str
    modality: str = "unknown"


class AggregateRequest(BaseModel):
    query_id: str
    results: list[InferenceResult]
    weights: dict[str, float] | None = None


class AggregateResponse(BaseModel):
    query_id: str
    ensemble_predictions: dict[str, float]
    per_modality_predictions: dict[str, dict[str, float]]
    avg_confidence: float
    model_count: int
    modalities_used: list[str]


@app.post("/aggregate")
async def aggregate(request: AggregateRequest) -> AggregateResponse:
    """Aggregate results from multiple models across modalities.

    Supports optional per-modality weighting. Defaults to equal weights.
    """
    if not request.results:
        return AggregateResponse(
            query_id=request.query_id,
            ensemble_predictions={},
            per_modality_predictions={},
            avg_confidence=0.0,
            model_count=0,
            modalities_used=[],
        )

    modality_weight = request.weights or {}
    modalities_present = list({r.modality for r in request.results})

    # Compute per-modality ensemble
    per_modality: dict[str, dict[str, float]] = {}
    for modality in modalities_present:
        modality_results = [r for r in request.results if r.modality == modality]
        all_classes: set[str] = set()
        for r in modality_results:
            all_classes.update(r.predictions.keys())

        modality_ensemble: dict[str, float] = {}
        for cls in all_classes:
            values = [r.predictions.get(cls, 0.0) for r in modality_results]
            modality_ensemble[cls] = round(sum(values) / len(values), 4)

        per_modality[modality] = dict(
            sorted(modality_ensemble.items(), key=lambda x: x[1], reverse=True)
        )

    # Cross-modality fusion with optional weights
    all_classes_global: set[str] = set()
    for preds in per_modality.values():
        all_classes_global.update(preds.keys())

    total_weight = sum(modality_weight.get(m, 1.0) for m in modalities_present)
    ensemble: dict[str, float] = {}
    for cls in all_classes_global:
        weighted_sum = 0.0
        for modality in modalities_present:
            weight = modality_weight.get(modality, 1.0)
            weighted_sum += per_modality[modality].get(cls, 0.0) * weight
        ensemble[cls] = round(weighted_sum / total_weight, 4)

    sorted_ensemble = dict(sorted(ensemble.items(), key=lambda x: x[1], reverse=True))
    avg_confidence = sum(r.confidence for r in request.results) / len(request.results)

    return AggregateResponse(
        query_id=request.query_id,
        ensemble_predictions=sorted_ensemble,
        per_modality_predictions=per_modality,
        avg_confidence=round(avg_confidence, 4),
        model_count=len(request.results),
        modalities_used=modalities_present,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "aggregator"}
