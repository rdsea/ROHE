from flask import Flask
from flask_restful import Api
from qoa4ml.config.configs import CollectorConfig, ConnectorConfig

from rohe.api.agent_manager_resource import AgentManagerResource
from rohe.api.registration_resource import RegistrationResource
from rohe.common import rohe_utils
from rohe.common.data_models import MongoAuthentication, MongoCollection
from rohe.common.logger import logger
from rohe.observation.agent_manager import AgentManager
from rohe.observation.registration_manager import RegistrationManager
from rohe.storage.mongo import MDBClient
from rohe.variable import ROHE_PATH

DEFAULT_CONFIG_PATH = "/config/observationConfig.yaml"


class ObservationService:
    def __init__(self) -> None:
        self.app = Flask(__name__)
        self.api = Api(self.app)
        # load configuration file
        config_file = ROHE_PATH + DEFAULT_CONFIG_PATH
        logger.debug(config_file)

        configuration = rohe_utils.load_config(config_file)
        assert configuration is not None
        logger.debug(configuration)
        db_config = MongoAuthentication(**configuration["db_authentication"])
        db_collection = MongoCollection(**configuration["db_collection"])
        db_client = MDBClient(db_config)

        connector_config = ConnectorConfig(**configuration["connector"])
        collector_config = CollectorConfig(**configuration["collector"])

        self.registration_manager = RegistrationManager(
            db_client, db_collection, connector_config, collector_config
        )
        self.agent_manager = AgentManager(
            db_client, db_collection, configuration["agent_image"]
        )
        self.api.add_resource(
            RegistrationResource,
            "/registration",
            resource_class_kwargs={"registration_manager": self.registration_manager},
        )
        self.api.add_resource(
            AgentManagerResource,
            "/agent/<string:command>",
            resource_class_kwargs={"agent_manager": self.agent_manager},
        )

    def run(self):
        return self.app


def create_app():
    my_app = ObservationService()
    return my_app.run()
