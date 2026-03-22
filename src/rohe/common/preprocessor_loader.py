from __future__ import annotations

import logging
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from .model_interface import DataPreprocessor

logger = logging.getLogger(__name__)


class PreprocessorType(StrEnum):
    IMAGE = "image"
    TIMESERIES = "timeseries"
    SIMULATED = "simulated"


class PreprocessorLoader:
    """Factory to load data preprocessors from YAML config."""

    @staticmethod
    def load(config_path: str | Path) -> DataPreprocessor:
        config = yaml.safe_load(Path(config_path).read_text())
        preproc_type = config["preprocessor"]["type"]

        if preproc_type == PreprocessorType.IMAGE:
            return PreprocessorLoader._load_image(config)

        if preproc_type == PreprocessorType.TIMESERIES:
            return PreprocessorLoader._load_timeseries(config)

        if preproc_type == PreprocessorType.SIMULATED:
            from simulation.simulated_preprocessor import SimulatedPreprocessor
            return SimulatedPreprocessor(config)

        raise ValueError(
            f"Unknown preprocessor type: '{preproc_type}'. "
            f"Supported: {', '.join(PreprocessorType)}"
        )

    @staticmethod
    def _load_image(config: dict[str, Any]) -> DataPreprocessor:
        raise NotImplementedError("Image preprocessor: implement per pipeline")

    @staticmethod
    def _load_timeseries(config: dict[str, Any]) -> DataPreprocessor:
        raise NotImplementedError("Timeseries preprocessor: implement per pipeline")
