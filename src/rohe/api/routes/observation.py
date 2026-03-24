from __future__ import annotations

import copy
import logging
import time
from copy import deepcopy
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from qoa4ml.config.configs import AMQPConnectorConfig

from rohe.common.data_models import AgentMangerRequest, RegistrationRequest

logger = logging.getLogger(__name__)


class StatusResponse(BaseModel):
    status: str
    response: dict[str, Any] = {}


def create_registration_router(registration_manager: Any) -> APIRouter:
    """Create registration router with injected manager dependency."""
    router = APIRouter(prefix="/registration", tags=["registration"])

    @router.post("/")
    async def register_app(request: Request) -> StatusResponse:
        try:
            body = await request.body()
            registration_data = RegistrationRequest.model_validate_json(body)
            response: dict[str, Any] = {}

            application_name = registration_data.application_name
            run_id = registration_data.run_id
            user_id = registration_data.user_id

            app = registration_manager.get_app(application_name)

            if app is None:
                metadata = registration_manager.register_app(
                    application_name, run_id, user_id
                )
                response[application_name] = (
                    f"Application {application_name} created for user {user_id} with run ID: {run_id}"
                )
            else:
                response[application_name] = "Application already exist"
                metadata = app
                metadata["client_count"] += 1
                metadata["timestamp"] = time.time()
                metadata["app_id"] = copy.deepcopy(metadata["_id"])
                metadata.pop("_id")
                registration_manager.update_app(metadata)

            connector = copy.deepcopy(registration_manager.connector_config)
            i_config = connector.config
            if isinstance(i_config, AMQPConnectorConfig):
                i_config.exchange_name = str(application_name) + "_exchange"
                i_config.out_routing_key = str(application_name)
                if registration_data.user_id is not None:
                    i_config.out_routing_key += "." + registration_data.user_id
                if registration_data.stage_id is not None:
                    i_config.out_routing_key += "." + registration_data.stage_id
                if registration_data.instance_id is not None:
                    i_config.out_routing_key += "." + registration_data.instance_id
                i_config.out_routing_key += ".client" + str(metadata["client_count"])

                response["app_id"] = metadata["app_id"]
                response["connector"] = connector.model_dump()

            return StatusResponse(status="success", response=response)
        except Exception as e:
            logger.exception(f"Error in registration: {e}")
            raise HTTPException(status_code=500, detail="Registration failed")

    @router.delete("/")
    async def delete_app(request: Request) -> StatusResponse:
        try:
            body = await request.body()
            registration_data = RegistrationRequest.model_validate_json(body)
            registration_manager.delete_app(
                registration_data.application_name,
                registration_data.run_id,
                registration_data.user_id,
            )
            return StatusResponse(
                status="success",
                response={"result": f"Deleted {registration_data.application_name}"},
            )
        except Exception as e:
            logger.exception(f"Error in delete: {e}")
            raise HTTPException(status_code=500, detail="Deletion failed")

    return router


def create_agent_manager_router(agent_manager: Any) -> APIRouter:
    """Create agent manager router with injected manager dependency."""
    router = APIRouter(prefix="/agent", tags=["agent-manager"])

    @router.post("/{command}")
    async def handle_agent_command(command: str, request: Request) -> StatusResponse:
        try:
            body = await request.body()
            response: dict[str, Any] = {}
            agent_manager.show_agent()

            request_data = AgentMangerRequest.model_validate_json(body)
            application_name = request_data.application_name
            app = agent_manager.get_app(application_name)

            if app is None:
                response[application_name] = f"Application {application_name} not exist"
                return StatusResponse(status="success", response=response)

            metadata = app
            agent_image = request_data.agent_image or agent_manager.default_agent_image

            if command == "start":
                if metadata["_id"] in agent_manager.agent_dict:
                    agent = agent_manager.agent_dict[metadata["_id"]]
                    if agent["status"] != 1:
                        agent["docker"] = agent_manager.start_docker(
                            str(agent_image), application_name
                        )
                        agent["status"] = 1
                else:
                    docker_agent = agent_manager.start_docker(
                        str(agent_image), application_name
                    )
                    agent = {"docker": docker_agent, "status": 1}
                    agent_manager.agent_dict[metadata["_id"]] = agent

                if request_data.stream_config is not None:
                    metadata["app_id"] = deepcopy(metadata["_id"])
                    metadata.pop("_id")
                    metadata["agent_config"]["stream_config"] = (
                        request_data.stream_config
                    )
                    agent_manager.update_app(metadata)

                response[application_name] = f"Agent for '{application_name}' started"

            elif command == "stop":
                if metadata["_id"] in agent_manager.agent_dict:
                    agent = agent_manager.agent_dict[metadata["_id"]]
                    if agent["status"] == 1:
                        agent["docker"].stop()
                        agent["status"] = 0
                response[application_name] = f"Agent for '{application_name}' stopped"

            elif command == "delete":
                if metadata["_id"] in agent_manager.agent_dict:
                    agent = agent_manager.agent_dict.pop(metadata["_id"])
                    if agent["status"] == 1:
                        agent["docker"].stop()
                        agent["status"] = 0
                agent_manager.db_client.delete_many(
                    agent_manager.db_collection,
                    {"application_name": application_name},
                )
                response[application_name] = f"Agent for '{application_name}' deleted"

            elif command == "kill-all":
                for agent_key in list(agent_manager.agent_dict.keys()):
                    agent_manager.agent_dict[agent_key]["status"] = 0
                    agent_manager.agent_dict[agent_key]["docker"].stop()
                response["result"] = "All agents killed"

            elif command == "log":
                if metadata["_id"] in agent_manager.agent_dict:
                    agent = agent_manager.agent_dict[metadata["_id"]]
                    logs = agent["docker"].logs(tail=20)
                    logger.info(logs)
                    response["logs"] = str(logs)

            else:
                raise HTTPException(
                    status_code=400, detail=f"Unknown command: {command}"
                )

            return StatusResponse(status="success", response=response)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error handling agent command '{command}': {e}")
            raise HTTPException(status_code=500, detail="Agent command failed")

    return router
