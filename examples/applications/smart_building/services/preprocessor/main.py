"""Smart Building multi-modal preprocessor.

Handles preprocessing for all smart building modalities:
  - video: frame resize/normalization
  - acc_phone, acc_watch, gyro, orientation: min-max signal normalization
"""
from __future__ import annotations

from typing import Any

from common.preprocessor_service import create_preprocessor_app


def preprocess_multimodal(data: Any) -> Any:
    """Normalize sensor signals or video frames.

    Input can be:
      - str: sample ID (simulated mode), pass through
      - list[float]: sensor signal, apply min-max normalization to [-1, 1]
      - other: pass through
    """
    if isinstance(data, str):
        return data
    if isinstance(data, list) and all(isinstance(v, (int, float)) for v in data):
        if not data:
            return data
        min_val = min(data)
        max_val = max(data)
        span = max_val - min_val
        if span == 0:
            return [0.0] * len(data)
        return [round((v - min_val) / span * 2 - 1, 4) for v in data]
    return data


app = create_preprocessor_app(
    service_name="smartbuilding-preprocessor",
    preprocess_fn=preprocess_multimodal,
)
