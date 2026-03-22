from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from rohe.common.data_models import AddNodeRequest, AddServiceRequest, RemoveNodeRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/management", tags=["orchestration"])


class CommandResponse(BaseModel):
    status: str
    response: dict[str, Any] = {}


def create_orchestration_router(node_and_service_manager: Any) -> APIRouter:
    """Create orchestration router with injected manager dependency."""

    @router.get("/")
    async def get_status() -> CommandResponse:
        return CommandResponse(status="ok")

    @router.post("/{command}")
    async def handle_command(command: str, request: Request) -> CommandResponse:
        try:
            body = await request.body()
            response: dict[str, Any] = {}

            if command == "add-node":
                node_data = AddNodeRequest.model_validate_json(body)
                response = node_and_service_manager.add_nodes(node_data.data)

            elif command == "remove-all-nodes":
                node_and_service_manager.db_client.drop(
                    node_and_service_manager.node_collection
                )
                response = {"result": "All nodes removed"}

            elif command == "remove-node":
                remove_data = RemoveNodeRequest.model_validate_json(body)
                response = node_and_service_manager.remove_nodes(remove_data.data)

            elif command == "add-service":
                service_data = AddServiceRequest.model_validate_json(body)
                response = node_and_service_manager.add_services(service_data.data)

            elif command == "remove-all-services":
                node_and_service_manager.db_client.drop(
                    node_and_service_manager.service_collection
                )
                response = {"result": "All services removed"}

            elif command == "get-all-services":
                response = {"result": node_and_service_manager.get_services()}

            elif command == "get-all-nodes":
                response = {"result": node_and_service_manager.get_nodes()}

            elif command == "start-agent":
                node_and_service_manager.orchestration_agent.start()
                response = {"result": "Agent started"}

            elif command == "stop-agent":
                node_and_service_manager.orchestration_agent.stop()
                response = {"result": "Agent stopped"}

            else:
                response = {"result": "Unknown command"}

            return CommandResponse(status="success", response=response)
        except Exception as e:
            logger.exception(f"Error handling command '{command}': {e}")
            raise HTTPException(status_code=500, detail="Command execution failed")

    return router
