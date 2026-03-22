from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from rohe.registry.discovery import ServiceDiscovery
from rohe.registry.registration import ApplicationRegistrar

logger = logging.getLogger(__name__)


class RegisterAppRequest(BaseModel):
    application_name: str
    run_id: str
    user_id: str


class RegisterServiceRequest(BaseModel):
    service_name: str
    host: str
    port: int
    metadata: dict[str, Any] | None = None


class StatusResponse(BaseModel):
    status: str
    data: dict[str, Any] = {}


def create_registry_router(
    registrar: ApplicationRegistrar,
    discovery: ServiceDiscovery,
) -> APIRouter:
    """Create registry router with injected dependencies."""
    router = APIRouter(prefix="/registry", tags=["registry"])

    # --- Application Registration ---

    @router.post("/applications")
    async def register_application(req: RegisterAppRequest) -> StatusResponse:
        existing = registrar.get_app(req.application_name)
        if existing is not None:
            updated = registrar.increment_client_count(req.application_name)
            return StatusResponse(status="existing", data=updated or {})

        metadata = registrar.register_app(req.application_name, req.run_id, req.user_id)
        return StatusResponse(status="created", data=metadata)

    @router.get("/applications")
    async def list_applications() -> StatusResponse:
        apps = registrar.list_apps()
        return StatusResponse(status="ok", data={"applications": apps})

    @router.get("/applications/{app_name}")
    async def get_application(app_name: str) -> StatusResponse:
        app = registrar.get_app(app_name)
        if app is None:
            raise HTTPException(status_code=404, detail=f"Application '{app_name}' not found")
        return StatusResponse(status="ok", data=app)

    @router.delete("/applications/{app_name}")
    async def delete_application(app_name: str) -> StatusResponse:
        deleted = registrar.delete_app(app_name)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Application '{app_name}' not found")
        return StatusResponse(status="deleted", data={"application_name": app_name})

    # --- Service Discovery ---

    @router.post("/services")
    async def register_service(req: RegisterServiceRequest) -> StatusResponse:
        instance_id = discovery.register(req.service_name, req.host, req.port, req.metadata)
        return StatusResponse(status="registered", data={"instance_id": instance_id})

    @router.get("/services/{service_name}")
    async def discover_service(service_name: str) -> StatusResponse:
        instances = discovery.discover(service_name)
        return StatusResponse(status="ok", data={"instances": instances})

    @router.delete("/services/{instance_id}")
    async def deregister_service(instance_id: str) -> StatusResponse:
        removed = discovery.deregister(instance_id)
        if not removed:
            raise HTTPException(status_code=404, detail=f"Instance '{instance_id}' not found")
        return StatusResponse(status="deregistered", data={"instance_id": instance_id})

    @router.get("/health")
    async def registry_health() -> StatusResponse:
        is_healthy = discovery.health_check()
        return StatusResponse(
            status="healthy" if is_healthy else "degraded",
            data={"discovery_backend": type(discovery).__name__},
        )

    return router
