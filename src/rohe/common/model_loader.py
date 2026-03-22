from __future__ import annotations

import logging
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from .model_interface import InferenceModel

logger = logging.getLogger(__name__)


class ModelType(StrEnum):
    PYTORCH = "pytorch"
    SKLEARN = "sklearn"
    SIMULATED = "simulated"


class ModelLoader:
    """Factory to load models from YAML config.

    Real model loaders (pytorch, sklearn) are implemented here.
    The simulated loader is a single deferred import from the
    simulation package (gitignored, volume-mounted at runtime).
    """

    @staticmethod
    def load(config_path: str | Path) -> InferenceModel:
        config = yaml.safe_load(Path(config_path).read_text())
        model_type = config["model"]["type"]

        if model_type == ModelType.PYTORCH:
            return ModelLoader._load_pytorch(config)

        if model_type == ModelType.SKLEARN:
            return ModelLoader._load_sklearn(config)

        if model_type == ModelType.SIMULATED:
            from simulation.simulated_model import SimulatedInferenceModel
            return SimulatedInferenceModel(config)

        raise ValueError(
            f"Unknown model type: '{model_type}'. "
            f"Supported: {', '.join(ModelType)}"
        )

    @staticmethod
    def _load_pytorch(config: dict[str, Any]) -> InferenceModel:
        raise NotImplementedError("PyTorch loader: implement per model architecture")

    @staticmethod
    def _load_sklearn(config: dict[str, Any]) -> InferenceModel:
        raise NotImplementedError("Sklearn loader: implement per model type")
