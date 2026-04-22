"""Orchestration module.

Provides multiple orchestration algorithms selectable at runtime:
- v2 (InferenceOrchestrator): async-first production orchestrator (requires a ServiceRegistry)
- adaptive (AdaptiveOrchestrator): original multimodal orchestrator with DuckDB
- dream (DREAMOrchestrator): DREAM algorithm variant
- llf (LLFOrchestrator): LLF algorithm variant

Algorithms can be selected via ExecutionPlan config or API request.
"""

from __future__ import annotations

import importlib

# All available orchestration algorithms (lazy-loaded via importlib)
ORCHESTRATOR_REGISTRY: dict[str, str] = {
    "v2": "rohe.orchestration.inference.orchestrator_v2.InferenceOrchestrator",
    "adaptive": "rohe.orchestration.inference.adaptive_orchestrator.AdaptiveOrchestrator",
    "dream": "rohe.orchestration.inference.dream.DREAMOrchestrator",
    "llf": "rohe.orchestration.inference.llf.LLFOrchestrator",
}


def _import_class(class_path: str) -> type:
    """Import a class by dotted string path.

    Raises:
        ImportError: if the module cannot be imported.
        AttributeError: if the class is not found in the module.
    """
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def create_orchestrator(algorithm: str = "adaptive", **kwargs: object) -> object:
    """Create an orchestrator by algorithm name.

    Available algorithms: v2, adaptive, dream, llf. Each algorithm's constructor
    accepts different arguments (for example, v2 requires a ServiceRegistry).
    Pass the relevant keyword arguments via ``kwargs``.
    """
    class_path = ORCHESTRATOR_REGISTRY.get(algorithm.lower())
    if class_path is None:
        raise ValueError(
            f"Unknown orchestration algorithm '{algorithm}'. "
            f"Available: {list(ORCHESTRATOR_REGISTRY.keys())}"
        )
    cls = _import_class(class_path)
    return cls(**kwargs)
