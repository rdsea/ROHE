from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict


class InferenceOutput(BaseModel):
    """Standard output from any model (real or simulated)."""

    model_config = ConfigDict(frozen=True)

    predictions: dict[str, float]
    confidence: float
    metadata: dict[str, Any] = {}


class InferenceModel(ABC):
    """Interface that ALL models (real or simulated) must implement."""

    @abstractmethod
    def predict(self, input_data: Any) -> InferenceOutput: ...

    @abstractmethod
    def get_model_info(self) -> dict[str, str]: ...


class DataPreprocessor(ABC):
    """Interface that ALL preprocessors (real or simulated) must implement."""

    @abstractmethod
    def preprocess(self, input_data: Any) -> Any: ...

    @abstractmethod
    def get_preprocessor_info(self) -> dict[str, str]: ...
