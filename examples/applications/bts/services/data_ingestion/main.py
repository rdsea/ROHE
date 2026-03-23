"""BTS data ingestion and normalization preprocessor.

Normalizes sensor readings (temperature, humidity, HVAC power, etc.)
to [0, 1] range using min-max normalization.
"""
from __future__ import annotations

from typing import Any

from common.preprocessor_service import create_preprocessor_app


def normalize_sensor_data(data: Any) -> Any:
    """Min-max normalize sensor values to [0, 1] range.

    Expected input: list of floats (sensor readings) or a sample ID string.
    """
    if isinstance(data, str):
        # Simulated mode: sample ID, pass through
        return data
    if not isinstance(data, list):
        return data

    # Sensor value ranges for BTS building data
    ranges = [
        (0.0, 50.0),    # temperature_c
        (0.0, 100.0),   # humidity_pct
        (0.0, 50.0),    # hvac_power_kw
        (0.0, 20.0),    # lighting_power_kw
        (0.0, 200.0),   # occupancy_count
        (0.0, 1200.0),  # solar_irradiance_wm2
    ]
    normalized = []
    for i, val in enumerate(data):
        if i < len(ranges):
            lo, hi = ranges[i]
            normalized.append(round(max(0.0, min(1.0, (val - lo) / (hi - lo))), 4))
        else:
            normalized.append(val)
    return normalized


app = create_preprocessor_app(
    service_name="bts-data-ingestion",
    preprocess_fn=normalize_sensor_data,
)
