import copy
import os
import sys

ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
import logging

from core.common.restService import RoheRestObject

logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)
import docker
from flask import jsonify, request

DEFAULT_DOCKER_MOUNT = {
    ROHE_PATH + "/core": {"bind": "/agent/core", "mode": "ro"},
    ROHE_PATH + "/userModule": {"bind": "/agent/userModule", "mode": "ro"},
    ROHE_PATH + "/lib": {"bind": "/agent/lib", "mode": "ro"},
    ROHE_PATH + "/config": {"bind": "/agent/configurations", "mode": "ro"},
    ROHE_PATH + "/temp/agent/": {"bind": "/agent/data/", "mode": "rw"},
}


class RoheAgentManager(RoheRestObject):
    def __init__(self, **kwargs) -> None:
        try:
            super().__init__()
            self.conf = kwargs

            # Init Database connection
            self.dbClient = self.conf["dbClient"]
            self.dbCollection = self.conf["dbCollection"]
            self.default_agent_image = self.conf["agent_image"]
            # local docker for testing
            self.docker_client = docker.from_env()
            # remote docker client
            # self.docker_client = docker.DockerClient(base_url= "tcp://<host>:2375")
            if "agent_dict" not in globals():
                global agent_dict
                agent_dict = {}
        except Exception as e:
            logging.error("Error in `__init__` RoheAgentManager: {}".format(e))
            return {}

    def start_docker(self, image, application_name):
        try:
            container = self.docker_client.containers.run(
                image,
                volumes=DEFAULT_DOCKER_MOUNT,
                remove=True,
                detach=True,
                environment={"APP_NAME": application_name, "ROHE_PATH": "/agent/"},
            )
            return container
        except Exception as e:
            logging.error("Error in `start_docker` RoheAgentManager: {}".format(e))
            return {}

    def update_app(self, metadata):
        try:
            # update application configuration
            return self.dbClient.insert_one(self.dbCollection, metadata)
        except Exception as e:
            logging.error("Error in `update_app` RoheAgentManager: {}".format(e))
            return {}

    def get_app(self, application_name):
        try:
            # Get application configuration from database
            # Prepare query pipeline
            pipeline = [
                {"$sort": {"timestamp": 1}},
                {
                    "$group": {
                        "_id": "$appID",
                        "application_name": {"$last": "$application_name"},
                        "user_id": {"$last": "$user_id"},
                        "run_id": {"$last": "$run_id"},
                        "timestamp": {"$last": "$timestamp"},
                        "db": {"$last": "$db"},
                        "client_count": {"$last": "$client_count"},
                        "agent_config": {"$last": "$agent_config"},
                    }
                },
            ]
            app_list = list(self.dbClient.get(self.dbCollection, pipeline))
            # Get application from application list
            for app in app_list:
                if app["application_name"] == application_name:
                    return app
            return None
        except Exception as e:
            logging.error("Error in `get_app` RoheAgentManager: {}".format(e))
            return None

    def show_agent(self):
        try:
            # Show list of agent and its status for debugging
            logging.info("Agent: {}".format(agent_dict))
        except Exception as e:
            logging.error("Error in `show_agent` RoheAgentManager: {}".format(e))
            return None

    def post(self):
        try:
            # Processing POST request
            response = {}
            if request.is_json:
                # parse json request
                args = request.get_json(force=True)
                self.show_agent()  # for debugging
                if "application_name" in args:
                    # Check application info from the request
                    application_name = args["application_name"]
                    # Get application configuration from database
                    app = self.get_app(application_name)
                    logging.info(app)
                    if app == None:
                        # Application has not been registered
                        response[application_name] = "Application {} not exist".format(
                            application_name
                        )
                    else:
                        # If application exist
                        if "agent_image" in args:
                            agent_image = args["agent_image"]
                        else:
                            agent_image = self.default_agent_image
                        if "command" in args:
                            # Check command
                            command = args["command"]
                            metadata = app
                            if command == "start":
                                # Check agent of the application status
                                if metadata["_id"] in agent_dict:
                                    # If agent is created locally
                                    agent = agent_dict[metadata["_id"]]
                                    if agent["status"] != 1:
                                        agent["docker"] = self.start_docker(
                                            str(agent_image), application_name
                                        )
                                        agent["status"] = 1
                                else:
                                    # If agent is not found - create new agent and start
                                    docker_agent = self.start_docker(
                                        str(agent_image), application_name
                                    )
                                    agent = {"docker": docker_agent, "status": 1}
                                    agent_dict[metadata["_id"]] = agent
                                if "stream_config" in args:
                                    metadata["appID"] = copy.deepcopy(metadata["_id"])
                                    metadata.pop("_id")
                                    metadata["agent_config"]["stream_config"] = args[
                                        "stream_config"
                                    ]
                                    self.update_app(metadata)
                                self.show_agent()  # for debugging
                                # create a response
                                response[application_name] = (
                                    "Application agent for application '{}' started ".format(
                                        application_name
                                    )
                                )
                            if command == "log":
                                if metadata["_id"] in agent_dict:
                                    agent = agent_dict[metadata["_id"]]
                                    docker_agent = agent["docker"]

                                    logging.info(docker_agent.logs(tail=20))

                            if command == "stop":
                                if metadata["_id"] in agent_dict:
                                    # if agent exist locally
                                    agent = agent_dict[metadata["_id"]]
                                    if agent["status"] == 1:
                                        # if ageent is running
                                        docker_agent = agent["docker"]
                                        docker_agent.stop()
                                        agent["status"] = 0

                                # create a response
                                response[application_name] = (
                                    "Application agent for {} stopped ".format(
                                        application_name
                                    )
                                )
                            if command == "delete":
                                if metadata["_id"] in agent_dict:
                                    # if agent exist locally
                                    agent = agent_dict.pop(metadata["_id"])
                                    # kill agent
                                    if agent["status"] == 1:
                                        # if ageent is running
                                        docker_agent = agent["docker"]
                                        docker_agent.stop()
                                        agent["status"] = 0
                                # Delete the application from databased
                                self.dbClient.delete_many(
                                    self.dbCollection,
                                    {"application_name": application_name},
                                )
                                # create a response
                                response[application_name] = (
                                    "Application agent for {} deleted ".format(
                                        application_name
                                    )
                                )
                            if command == "kill_all_agent":
                                for agent in list(agent_dict.keys()):
                                    agent_dict[agent]["status"] = 0
                                    agent_dict[agent]["docker"].stop()
            # Return the response
            return jsonify({"status": "success", "response": response})
        except Exception as e:
            logging.error("Error in `post` RoheAgentManager: {}".format(e))
            return jsonify({"status": "request fail"})
