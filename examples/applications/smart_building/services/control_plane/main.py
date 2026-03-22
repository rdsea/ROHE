"""Smart Building control plane."""
from common.gateway_service import create_gateway_app

app = create_gateway_app(service_name="smart-building-control-plane", input_mode="json")
