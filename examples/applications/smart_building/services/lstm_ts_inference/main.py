"""LSTM time-series inference service."""
from common.inference_service import create_inference_app

app = create_inference_app(service_name="lstm_ts", modality="timeseries")
