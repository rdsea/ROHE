"""Object Classification image preprocessor.

Resizes images to 224x224 and normalizes pixel values for classification models.
"""
from __future__ import annotations

from typing import Any

from common.preprocessor_service import create_preprocessor_app


def preprocess_image(data: Any) -> Any:
    """Resize image to 224x224 and normalize.

    Input can be a sample ID (simulated mode) or raw image bytes.
    """
    if isinstance(data, str):
        return data
    # Real implementation would resize to 224x224 and normalize to [0,1].
    # Passthrough for now -- real preprocessing loaded via PreprocessorLoader.
    return data


app = create_preprocessor_app(
    service_name="objclass-preprocessor",
    preprocess_fn=preprocess_image,
)
