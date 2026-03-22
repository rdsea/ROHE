"""Aggregator service: combines ensemble results from multiple inference services."""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Aggregator Service")


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
    """Aggregate results from multiple models via confidence averaging."""
    if not request.results:
        return AggregateResponse(
            query_id=request.query_id,
            ensemble_predictions={},
            avg_confidence=0.0,
            model_count=0,
        )

    all_classes: set[str] = set()
    for r in request.results:
        all_classes.update(r.predictions.keys())

    ensemble: dict[str, float] = {}
    for cls in all_classes:
        values = [r.predictions.get(cls, 0.0) for r in request.results]
        ensemble[cls] = sum(values) / len(values)

    sorted_ensemble = dict(sorted(ensemble.items(), key=lambda x: x[1], reverse=True))
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
