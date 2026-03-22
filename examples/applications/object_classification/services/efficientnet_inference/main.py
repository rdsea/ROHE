"""EfficientNet-B0 inference service."""
from common.inference_service import create_inference_app

app = create_inference_app(service_name="efficientnet_b0")
