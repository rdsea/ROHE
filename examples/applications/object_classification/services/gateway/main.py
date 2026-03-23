"""Object Classification gateway.

In the orchestrated pipeline, the gateway accepts JSON with opaque data
that gets stored in DataHub. The orchestrator handles routing to inference services.
"""
from common.gateway_service import create_gateway_app

app = create_gateway_app(service_name="object-classification-gateway", input_mode="json")
