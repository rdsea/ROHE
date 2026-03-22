ORCHESTRATOR_REGISTRY = {
    "adaptive": "rohe.orchestration.multimodal_orchestration.AdaptiveOrchestrator",
    "llf": "rohe.orchestration.llf_orchestration.LLFOrchestrator",
    "dream": "rohe.orchestration.dream_orchestration.DREAMOrchestrator",
}


def _import_class(dotted_path: str):
    module_path, class_name = dotted_path.rsplit(".", 1)
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def create_orchestrator(
    algorithm: str = "adaptive", config_path: str = "../config/orchestrator.yaml"
):
    class_path = ORCHESTRATOR_REGISTRY.get(algorithm.lower())
    if class_path is None:
        raise ValueError(
            f"Unknown orchestration algorithm '{algorithm}'. Available: {list(ORCHESTRATOR_REGISTRY.keys())}"
        )
    orchestrator_cls = _import_class(class_path)
    return orchestrator_cls(config_path=config_path)
