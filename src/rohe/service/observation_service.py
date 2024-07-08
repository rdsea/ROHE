# from devtools import debug
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
from rohe.storage.abstract import MDBClient
from rohe.variable import ROHE_PATH

DEFAULT_PORT = 5010
DEFAULT_CONFIG_PATH = "/config/observationConfig.yaml"

config_file = None
port = DEFAULT_PORT

app = Flask(__name__)
api = Api(app)
# load configuration file
if not config_file:
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

registration_manager = RegistrationManager(
    db_client, db_collection, connector_config, collector_config
)
agent_manager = AgentManager(db_client, db_collection, configuration["agent_image"])
api.add_resource(
    RegistrationResource,
    "/registration",
    resource_class_kwargs={"registration_manager": registration_manager},
)
api.add_resource(
    AgentManagerResource,
    "/agent/<string:command>",
    resource_class_kwargs={"agent_manager": agent_manager},
)
