"""Ensemble selection strategies for multi-model inference.

Refactored from the legacy multimodal_ensemble.py which had 95% code duplication
across 3 strategy functions. Now uses a Strategy pattern with a common base.

Each strategy selects which inference service instances to include in the
ensemble for a given modality, based on different optimization criteria.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from rohe.models.enums import CommonMetric, Explainability, InstanceStatus
from rohe.models.pipeline import (
    InferenceResult,
    InferenceServiceInstance,
    InferenceServiceProfile,
    InferenceTask,
)

logger = logging.getLogger(__name__)


class EnsembleSelector(ABC):
    """Base class for ensemble selection strategies."""

    @abstractmethod
    def select(
        self,
        task: InferenceTask,
        intermediate_result: InferenceResult,
        services: dict[str, InferenceServiceProfile],
        instances: dict[str, InferenceServiceInstance],
    ) -> tuple[list[InferenceServiceInstance], list[InferenceServiceInstance]]:
        """Select ensemble instances for a task.

        Returns:
            (selected_instances, selected_explainability_instances)
        """
        ...

    def _get_target_classes(
        self,
        task: InferenceTask,
        intermediate_result: InferenceResult,
    ) -> list[str]:
        """Get target classes for this strategy. Subclasses override."""
        return []

    def _find_best_instance(
        self,
        service_id: str,
        task: InferenceTask,
        mode: str = "normal",
    ) -> InferenceServiceInstance | None:
        """Find the best instance for a service based on response time."""
        target_instances = (
            task.inference_instances_ex if mode == "explainability"
            else task.inference_instances
        )
        if not target_instances or service_id not in target_instances:
            return None

        best: InferenceServiceInstance | None = None
        best_time = float("inf")

        for inst_id, instance in target_instances[service_id].items():
            if not isinstance(instance, InferenceServiceInstance):
                continue
            for metric in instance.runtime_performance:
                if metric.metric_name == CommonMetric.RESPONSE_TIME:
                    rt = float(metric.value) if metric.value is not None else float("inf")
                    if rt < best_time:
                        best_time = rt
                        best = instance
                    break

        return best

    def _select_services_by_classes(
        self,
        task: InferenceTask,
        target_classes: list[str],
        services: dict[str, InferenceServiceProfile],
    ) -> list[str]:
        """Select services that are best for the given target classes.

        For each target class, finds the service with the highest
        class-specific accuracy.
        """
        selected: list[str] = []
        ensemble_size = task.ensemble_size or 1

        for target_class in target_classes:
            if len(selected) >= ensemble_size:
                break

            best_service_id: str | None = None
            best_accuracy = -1.0

            available_services = task.inference_services or {}
            for svc_id, svc in available_services.items():
                if svc_id in selected:
                    continue
                if not isinstance(svc, InferenceServiceProfile):
                    continue

                # Find class-specific accuracy
                for metric in svc.base_line:
                    if (
                        metric.metric_name == CommonMetric.ACCURACY
                        and metric.class_id == target_class
                        and metric.value is not None
                        and float(metric.value) > best_accuracy
                    ):
                        best_accuracy = float(metric.value)
                        best_service_id = svc_id
                        break

            if best_service_id and best_service_id not in selected:
                selected.append(best_service_id)

        return selected

    def _select_services_by_overall_accuracy(
        self,
        task: InferenceTask,
    ) -> list[str]:
        """Select services by overall accuracy (not class-specific)."""
        scored: list[tuple[str, float]] = []
        available_services = task.inference_services or {}

        for svc_id, svc in available_services.items():
            if not isinstance(svc, InferenceServiceProfile):
                continue
            for metric in svc.base_line:
                if metric.metric_name == CommonMetric.ACCURACY and metric.value is not None:
                    scored.append((svc_id, float(metric.value)))
                    break

        scored.sort(key=lambda x: x[1], reverse=True)
        ensemble_size = task.ensemble_size or 1
        return [svc_id for svc_id, _ in scored[:ensemble_size]]

    def _resolve_instances(
        self,
        task: InferenceTask,
        service_ids: list[str],
    ) -> tuple[list[InferenceServiceInstance], list[InferenceServiceInstance]]:
        """Resolve service IDs to actual instances."""
        normal: list[InferenceServiceInstance] = []
        explainability: list[InferenceServiceInstance] = []

        for svc_id in service_ids:
            inst = self._find_best_instance(svc_id, task, mode="normal")
            if inst:
                normal.append(inst)

            if task.explainability:
                ex_inst = self._find_best_instance(svc_id, task, mode="explainability")
                if ex_inst:
                    explainability.append(ex_inst)

        return normal, explainability


class EnhanceConfidenceSelector(EnsembleSelector):
    """Select services specialized in the top-K most confident predictions.

    Picks services with the highest class-specific accuracy for the classes
    that already have the highest predicted confidence.
    """

    def select(
        self,
        task: InferenceTask,
        intermediate_result: InferenceResult,
        services: dict[str, InferenceServiceProfile],
        instances: dict[str, InferenceServiceInstance],
    ) -> tuple[list[InferenceServiceInstance], list[InferenceServiceInstance]]:
        ensemble_size = task.ensemble_size or 1
        top_classes = intermediate_result.get_top_k_predictions(ensemble_size)

        if not top_classes:
            service_ids = self._select_services_by_overall_accuracy(task)
        else:
            service_ids = self._select_services_by_classes(task, top_classes, services)

        return self._resolve_instances(task, service_ids)


class SelectByOverallAccuracySelector(EnsembleSelector):
    """Select services with the highest overall accuracy.

    Simple strategy that ignores class-specific performance and picks
    the globally most accurate models.
    """

    def select(
        self,
        task: InferenceTask,
        intermediate_result: InferenceResult,
        services: dict[str, InferenceServiceProfile],
        instances: dict[str, InferenceServiceInstance],
    ) -> tuple[list[InferenceServiceInstance], list[InferenceServiceInstance]]:
        service_ids = self._select_services_by_overall_accuracy(task)
        return self._resolve_instances(task, service_ids)


class EnhanceGeneralizationSelector(EnsembleSelector):
    """Select services specialized in the worst-K predictions.

    Picks services that are best at the classes the ensemble is currently
    worst at, improving generalization across all classes.
    """

    def select(
        self,
        task: InferenceTask,
        intermediate_result: InferenceResult,
        services: dict[str, InferenceServiceProfile],
        instances: dict[str, InferenceServiceInstance],
    ) -> tuple[list[InferenceServiceInstance], list[InferenceServiceInstance]]:
        ensemble_size = task.ensemble_size or 1
        worst_classes = intermediate_result.get_worst_k_predictions(ensemble_size)

        if not worst_classes:
            service_ids = self._select_services_by_overall_accuracy(task)
        else:
            service_ids = self._select_services_by_classes(task, worst_classes, services)

        return self._resolve_instances(task, service_ids)


# -- Factory --

_STRATEGIES: dict[str, type[EnsembleSelector]] = {
    "enhance_confidence": EnhanceConfidenceSelector,
    "select_by_overall_accuracy": SelectByOverallAccuracySelector,
    "enhance_generalization": EnhanceGeneralizationSelector,
}


class EnsembleSelectorFactory:
    """Factory for creating ensemble selection strategies."""

    @staticmethod
    def create(strategy_name: str) -> EnsembleSelector:
        """Create a selector by strategy name."""
        cls = _STRATEGIES.get(strategy_name)
        if cls is None:
            logger.warning(
                f"Unknown strategy '{strategy_name}', falling back to enhance_confidence"
            )
            cls = EnhanceConfidenceSelector
        return cls()

    @staticmethod
    def available_strategies() -> list[str]:
        """Return list of available strategy names."""
        return list(_STRATEGIES.keys())

    @staticmethod
    def register(name: str, selector_class: type[EnsembleSelector]) -> None:
        """Register a custom ensemble selection strategy."""
        _STRATEGIES[name] = selector_class
