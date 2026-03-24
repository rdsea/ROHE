from copy import deepcopy

from flask import jsonify, request
from flask_restful import Resource

from ..common.data_models import AgentMangerRequest
from ..common.logger import logger
from ..observation.agent_manager import AgentManager


class AgentManagerResource(Resource):
    def __init__(self, **kwargs) -> None:
        self.config = kwargs
        self.agent_manager: AgentManager = self.config["agent_manager"]

    def post(self, command: str):
        try:
            # Processing POST request
            response = {}
            if not request.is_json:
                return jsonify({"status": "request failed, only support json"})
            self.agent_manager.show_agent()  # for debugging
            request_data = AgentMangerRequest.model_validate_json(request.data)
            # Check application info from the request
            application_name = request_data.application_name
            # Get application configuration from database
            app = self.agent_manager.get_app(application_name)
            logger.info(app)
            if app is None:
                # Application has not been registered
                response[application_name] = f"Application {application_name} not exist"
            else:
                # If application exist
                if request_data.agent_image is not None:
                    agent_image = request_data.agent_image
                else:
                    agent_image = self.agent_manager.default_agent_image
                metadata = app
                if command == "start":
                    # Check agent of the application status
                    if metadata["_id"] in self.agent_manager.agent_dict:
                        # If agent is created locally
                        agent = self.agent_manager.agent_dict[metadata["_id"]]
                        if agent["status"] != 1:
                            agent["docker"] = self.agent_manager.start_docker(
                                str(agent_image), application_name
                            )
                            agent["status"] = 1
                    else:
                        # If agent is not found - create new agent and start
                        docker_agent = self.agent_manager.start_docker(
                            str(agent_image), application_name
                        )
                        agent = {"docker": docker_agent, "status": 1}
                        self.agent_manager.agent_dict[metadata["_id"]] = agent
                    if request_data.stream_config is not None:
                        metadata["app_id"] = deepcopy(metadata["_id"])
                        metadata.pop("_id")
                        metadata["agent_config"]["stream_config"] = (
                            request_data.stream_config
                        )
                        self.agent_manager.update_app(metadata)
                    self.agent_manager.show_agent()  # for debugging
                    # create a response
                    response[application_name] = (
                        f"Application agent for application '{application_name}' started "
                    )
                elif command == "log":
                    if metadata["_id"] in self.agent_manager.agent_dict:
                        agent = self.agent_manager.agent_dict[metadata["_id"]]
                        docker_agent = agent["docker"]

                        logger.info(docker_agent.logs(tail=20))

                elif command == "stop":
                    if metadata["_id"] in self.agent_manager.agent_dict:
                        # if agent exist locally
                        agent = self.agent_manager.agent_dict[metadata["_id"]]
                        if agent["status"] == 1:
                            # if ageent is running
                            docker_agent = agent["docker"]
                            docker_agent.stop()
                            agent["status"] = 0

                    # create a response
                    response[application_name] = (
                        f"Application agent for {application_name} stopped "
                    )
                elif command == "delete":
                    if metadata["_id"] in self.agent_manager.agent_dict:
                        # if agent exist locally
                        agent = self.agent_manager.agent_dict.pop(metadata["_id"])
                        # kill agent
                        if agent["status"] == 1:
                            # if ageent is running
                            docker_agent = agent["docker"]
                            docker_agent.stop()
                            agent["status"] = 0
                    # Delete the application from databased
                    self.agent_manager.db_client.delete_many(
                        self.agent_manager.db_collection,
                        {"application_name": application_name},
                    )
                    # create a response
                    response[application_name] = (
                        f"Application agent for {application_name} deleted "
                    )
                elif command == "kill-all":
                    for agent in list(self.agent_manager.agent_dict.keys()):
                        self.agent_manager.agent_dict[agent]["status"] = 0
                        self.agent_manager.agent_dict[agent]["docker"].stop()
                else:
                    response = {"status": "failed", "response": "Command not found"}
            # Return the response
            return jsonify({"status": "success", "response": response})
        except Exception as e:
            logger.exception(f"Error in `post` RoheAgentManager: {e}")
            return jsonify({"status": "request fail"})
