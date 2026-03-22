"""Aggregator service: combines ensemble results from multiple inference services."""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="BTS Aggregator Service")


class InferenceResult(BaseModel):
    query_id: str
    predictions: dict[str, float]
    confidence: float
    model: str


class AggregateRequest(BaseModel):
    query_id: str
    results: list[InferenceResult]


class AggregateResponse(BaseModel):
    query_id: str
    ensemble_predictions: dict[str, float]
    avg_confidence: float
    model_count: int


@app.post("/aggregate")
async def aggregate(request: AggregateRequest) -> AggregateResponse:
    """Aggregate results from multiple forecasting models via confidence-weighted averaging."""
    if not request.results:
        return AggregateResponse(
            query_id=request.query_id,
            ensemble_predictions={},
            avg_confidence=0.0,
            model_count=0,
        )

    all_keys: set[str] = set()
    for r in request.results:
        all_keys.update(r.predictions.keys())

    # Confidence-weighted averaging
    total_confidence = sum(r.confidence for r in request.results)
    ensemble: dict[str, float] = {}
    for key in all_keys:
        weighted_sum = sum(
            r.predictions.get(key, 0.0) * r.confidence
            for r in request.results
        )
        ensemble[key] = round(weighted_sum / total_confidence, 4) if total_confidence > 0 else 0.0

    sorted_ensemble = dict(sorted(ensemble.items()))
    avg_confidence = sum(r.confidence for r in request.results) / len(request.results)

    return AggregateResponse(
        query_id=request.query_id,
        ensemble_predictions=sorted_ensemble,
        avg_confidence=round(avg_confidence, 4),
        model_count=len(request.results),
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "aggregator"}
