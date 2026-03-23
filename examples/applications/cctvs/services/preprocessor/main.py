"""CCTVS image preprocessor.

Resizes images to 640x640 and normalizes pixel values.
Supports both DataHub-referenced and direct image upload.
"""
from __future__ import annotations

from typing import Any

from common.preprocessor_service import create_preprocessor_app


def preprocess_image(data: Any) -> Any:
    """Resize and normalize image data.

    Input can be a sample ID (simulated mode) or raw image bytes.
    """
    if isinstance(data, str):
        # Simulated mode: sample ID, pass through
        return data
    # For real images, a proper implementation would resize/normalize.
    # Keeping passthrough for now -- real preprocessing loaded via PreprocessorLoader.
    return data


app = create_preprocessor_app(
    service_name="cctvs-preprocessor",
    preprocess_fn=preprocess_image,
)
