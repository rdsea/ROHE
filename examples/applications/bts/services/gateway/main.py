"""BTS gateway."""
from common.gateway_service import create_gateway_app

app = create_gateway_app(service_name="bts-gateway", input_mode="json")
