from typing import Any, Dict

import docker

from ..common.data_models import MongoCollection
from ..common.logger import logger
from ..storage.mongo import MDBClient
from ..variable import ROHE_PATH

DEFAULT_DOCKER_MOUNT = {
    ROHE_PATH + "/core": {"bind": "/agent/core", "mode": "ro"},
    ROHE_PATH + "/userModule": {"bind": "/agent/userModule", "mode": "ro"},
    ROHE_PATH + "/lib": {"bind": "/agent/lib", "mode": "ro"},
    ROHE_PATH + "/config": {"bind": "/agent/configurations", "mode": "ro"},
    ROHE_PATH + "/temp/agent/": {"bind": "/agent/data/", "mode": "rw"},
}


class AgentManager:
    def __init__(
        self, db_client: MDBClient, db_collection: MongoCollection, agent_image: str
    ) -> None:
        try:
            # Init Database connection
            self.db_client = db_client
            self.db_collection = db_collection
            self.default_agent_image = agent_image
            # local docker for testing
            self.docker_client = docker.from_env()
            # remote docker client
            # self.docker_client = docker.DockerClient(base_url= "tcp://<host>:2375")
            # if "agent_dict" not in globals():
            #     global agent_dict
            #     agent_dict = {}
            self.agent_dict: Dict[str, Any] = {}
        except Exception as e:
            logger.exception(f"Error in `__init__` RoheAgentManager: {e}")

    def start_docker(self, image: str, application_name: str):
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
            logger.exception(f"Error in `start_docker` RoheAgentManager: {e}")
            return {}

    def update_app(self, metadata):
        try:
            # update application configuration
            return self.db_client.insert_one(self.db_collection, metadata)
        except Exception as e:
            logger.exception(f"Error in `update_app` RoheAgentManager: {e}")
            return {}

    def get_app(self, application_name):
        try:
            # Get application configuration from database
            # Prepare query pipeline
            query = [
                {"$sort": {"timestamp": 1}},
                {
                    "$group": {
                        "_id": "$app_id",
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
            app_list = self.db_client.get(self.db_collection, query)
            # Get application from application list
            for app in app_list:
                if app["application_name"] == application_name:
                    return app
            return None
        except Exception as e:
            logger.exception(f"Error in `get_app` RoheAgentManager: {e}")
            return None

    def show_agent(self):
        try:
            # Show list of agent and its status for debugging
            logger.info(f"Agent: {self.agent_dict}")
        except Exception as e:
            logger.exception(f"Error in `show_agent` RoheAgentManager: {e}")
            return
