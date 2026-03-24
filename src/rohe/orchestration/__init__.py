"""Orchestration module.

Provides multiple orchestration algorithms selectable at runtime:
- v2 (InferenceOrchestrator): async-first production orchestrator
- adaptive (AdaptiveOrchestrator): original multimodal orchestrator with DuckDB
- dream (DREAMOrchestrator): DREAM algorithm variant
- llf (LLFOrchestrator): LLF algorithm variant

Algorithms can be selected via ExecutionPlan config or API request.
"""
from __future__ import annotations

# All available orchestration algorithms (lazy-loaded via importlib)
ORCHESTRATOR_REGISTRY: dict[str, str] = {
    "v2": "rohe.orchestration.inference.orchestrator_v2.InferenceOrchestrator",
    "adaptive": "rohe.orchestration.inference.adaptive_orchestrator.AdaptiveOrchestrator",
    "dream": "rohe.orchestration.inference.dream.DREAMOrchestrator",
    "llf": "rohe.orchestration.inference.llf.LLFOrchestrator",
}


def create_orchestrator(algorithm: str = "v2", **kwargs: object) -> object:
    """Create an orchestrator by algorithm name.

    Available algorithms: v2, adaptive, dream, llf
    Default is "v2" (InferenceOrchestrator).
    """
    class_path = ORCHESTRATOR_REGISTRY.get(algorithm.lower())
    if class_path is None:
        raise ValueError(
            f"Unknown algorithm '{algorithm}'. "
            f"Available: {list(ORCHESTRATOR_REGISTRY.keys())}"
        )
    module_path, class_name = class_path.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls(**kwargs)
