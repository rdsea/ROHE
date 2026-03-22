"""Tests for model_interface, model_loader, aggregation strategies."""
from __future__ import annotations

from typing import Any

import pytest

from rohe.common.model_interface import DataPreprocessor, InferenceModel, InferenceOutput
from rohe.common.model_loader import ModelLoader, ModelType


class TestInferenceOutput:
    def test_frozen(self):
        output = InferenceOutput(predictions={"car": 0.9}, confidence=0.9)
        with pytest.raises(Exception):
            output.confidence = 0.5  # type: ignore[misc]

    def test_valid(self):
        output = InferenceOutput(
            predictions={"car": 0.9, "truck": 0.1},
            confidence=0.9,
            metadata={"model": "test"},
        )
        assert output.predictions["car"] == 0.9
        assert output.metadata["model"] == "test"

    def test_default_metadata(self):
        output = InferenceOutput(predictions={}, confidence=0.0)
        assert output.metadata == {}


class TestModelType:
    def test_values(self):
        assert ModelType.PYTORCH == "pytorch"
        assert ModelType.SKLEARN == "sklearn"
        assert ModelType.SIMULATED == "simulated"

    def test_is_str_enum(self):
        assert isinstance(ModelType.PYTORCH, str)


class TestModelLoader:
    def test_unknown_type_raises(self, tmp_path):
        config_file = tmp_path / "bad.yaml"
        config_file.write_text('model:\n  type: "unknown_type"\n')
        with pytest.raises(ValueError, match="Unknown model type"):
            ModelLoader.load(config_file)

    def test_pytorch_not_implemented(self, tmp_path):
        config_file = tmp_path / "pytorch.yaml"
        config_file.write_text('model:\n  type: "pytorch"\n  path: "/models/model.pt"\n')
        with pytest.raises(NotImplementedError):
            ModelLoader.load(config_file)

    def test_sklearn_not_implemented(self, tmp_path):
        config_file = tmp_path / "sklearn.yaml"
        config_file.write_text('model:\n  type: "sklearn"\n  path: "/models/model.pkl"\n')
        with pytest.raises(NotImplementedError):
            ModelLoader.load(config_file)

    def test_simulated_import_error(self, tmp_path):
        config_file = tmp_path / "sim.yaml"
        config_file.write_text('model:\n  type: "simulated"\n  name: "test"\n')
        with pytest.raises((ImportError, ModuleNotFoundError)):
            ModelLoader.load(config_file)

    def test_missing_config_raises(self):
        with pytest.raises(FileNotFoundError):
            ModelLoader.load("/nonexistent/config.yaml")


class TestInferenceModelInterface:
    def test_concrete_implementation(self):
        class DummyModel(InferenceModel):
            def predict(self, input_data: Any) -> InferenceOutput:
                return InferenceOutput(predictions={"a": 1.0}, confidence=1.0)

            def get_model_info(self) -> dict[str, str]:
                return {"name": "dummy", "type": "test"}

        model = DummyModel()
        result = model.predict("anything")
        assert result.confidence == 1.0
        assert model.get_model_info()["name"] == "dummy"

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            InferenceModel()  # type: ignore[abstract]


class TestDataPreprocessorInterface:
    def test_concrete_implementation(self):
        class DummyPreproc(DataPreprocessor):
            def preprocess(self, input_data: Any) -> Any:
                return input_data

            def get_preprocessor_info(self) -> dict[str, str]:
                return {"name": "dummy"}

        preproc = DummyPreproc()
        assert preproc.preprocess([1, 2, 3]) == [1, 2, 3]
