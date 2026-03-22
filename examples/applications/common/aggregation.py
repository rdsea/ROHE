"""Shared aggregation strategies for ensemble inference results."""
from __future__ import annotations

from collections import Counter

from .schemas import AggregateResponse, InferenceResponse


def aggregate_predictions(
    query_id: str,
    results: list[InferenceResponse],
    strategy: str = "confidence_avg",
) -> AggregateResponse:
    """Aggregate predictions from multiple models using the specified strategy."""
    if not results:
        return AggregateResponse(
            query_id=query_id,
            ensemble_predictions={},
            avg_confidence=0.0,
            model_count=0,
            strategy=strategy,
        )

    strategies = {
        "confidence_avg": _confidence_avg,
        "confidence_weighted": _confidence_weighted,
        "confidence_max": _confidence_max,
        "majority_vote": _majority_vote,
    }

    func = strategies.get(strategy, _confidence_avg)
    ensemble = func(results)
    avg_confidence = round(sum(r.confidence for r in results) / len(results), 4)

    sorted_ensemble = {
        k: round(v, 4)
        for k, v in sorted(ensemble.items(), key=lambda x: x[1], reverse=True)
    }

    return AggregateResponse(
        query_id=query_id,
        ensemble_predictions=sorted_ensemble,
        avg_confidence=avg_confidence,
        model_count=len(results),
        strategy=strategy,
    )


def _all_classes(results: list[InferenceResponse]) -> set[str]:
    classes: set[str] = set()
    for r in results:
        classes.update(r.predictions.keys())
    return classes


def _confidence_avg(results: list[InferenceResponse]) -> dict[str, float]:
    """Average confidence scores per class across all models."""
    classes = _all_classes(results)
    return {
        cls: sum(r.predictions.get(cls, 0.0) for r in results) / len(results)
        for cls in classes
    }


def _confidence_weighted(results: list[InferenceResponse]) -> dict[str, float]:
    """Weight each model's scores by its top-1 confidence."""
    classes = _all_classes(results)
    total_weight = sum(r.confidence for r in results)
    if total_weight == 0:
        return _confidence_avg(results)
    return {
        cls: sum(r.predictions.get(cls, 0.0) * r.confidence for r in results) / total_weight
        for cls in classes
    }


def _confidence_max(results: list[InferenceResponse]) -> dict[str, float]:
    """Take maximum confidence per class across all models."""
    classes = _all_classes(results)
    return {
        cls: max(r.predictions.get(cls, 0.0) for r in results)
        for cls in classes
    }


def _majority_vote(results: list[InferenceResponse]) -> dict[str, float]:
    """Each model votes for its top-1 class, returns vote distribution."""
    votes: list[str] = []
    for r in results:
        if r.predictions:
            top_class = max(r.predictions, key=r.predictions.get)  # type: ignore[arg-type]
            votes.append(top_class)

    if not votes:
        return {}

    counts = Counter(votes)
    total = len(votes)
    return {cls: count / total for cls, count in counts.items()}
