from flask import Flask
from flask_restful import Api

from rohe.api.orchestration_resource import OrchestationResource
from rohe.common import rohe_utils
from rohe.common.data_models import OrchestrationServiceConfig
from rohe.common.logger import logger
from rohe.orchestration.node_and_service_manager import NodeAndServiceManager
from rohe.variable import ROHE_PATH

DEFAULT_CONFIG_PATH = "/config/orchestrationConfig.yaml"
DEFAULT_PORT = 5002


class OrchestrationService:
    def __init__(self) -> None:
        self.app = Flask(__name__)
        self.api = Api(self.app)

        config_file = None
        if not config_file:
            config_file = ROHE_PATH + DEFAULT_CONFIG_PATH
            logger.info(config_file)

        configuration = rohe_utils.load_config(config_file)
        assert configuration is not None

        orchestration_service_config = OrchestrationServiceConfig.parse_obj(
            configuration
        )
        self.node_and_service_manager = NodeAndServiceManager(
            orchestration_service_config
        )

        self.api.add_resource(
            OrchestationResource,
            "/management",
            "/management/<string:command>",
            resource_class_kwargs={
                "node_and_service_manager": self.node_and_service_manager
            },
        )

    def run(self):
        return self.app


def create_app():
    my_app = OrchestrationService()
    return my_app.run()
