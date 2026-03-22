"""X3D Small inference service."""
from common.inference_service import create_inference_app

app = create_inference_app(service_name="x3d_s", modality="video")
