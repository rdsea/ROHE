ORCHESTRATOR_REGISTRY = {
    "adaptive": "rohe.orchestration.inference.orchestrator.AdaptiveOrchestrator",
    "llf": "rohe.orchestration.inference.llf.LLFOrchestrator",
    "dream": "rohe.orchestration.inference.dream.DREAMOrchestrator",
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
