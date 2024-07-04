import logging

from devtools import debug
from flask import Flask
from flask_restful import Api
from qoa4ml.config.configs import CollectorConfig, ConnectorConfig

import rohe.lib.rohe_utils as rohe_utils
from rohe.observation.agent_manager import RoheAgentManager
from rohe.observation.registration import RoheRegistration
from rohe.storage.abstract import MDBClient
from rohe.variable import ROHE_PATH

logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)

DEFAULT_PORT = 5010
DEFAULT_CONFIG_PATH = "/config/observationConfig.yaml"

# init_env_variables()
# TODO: can be improved with autocomplete
# parser = argparse.ArgumentParser(description="Argument for Rohe Observation Service")
# parser.add_argument("--conf", help="configuration file", default=None)
# parser.add_argument("--port", help="default port", default=5010)
#
# # Parse the parameters
# #
# args = parser.parse_args()

config_file = None
# config_path = args.path
port = DEFAULT_PORT

app = Flask(__name__)
api = Api(app)
# load configuration file
if not config_file:
    config_file = ROHE_PATH + DEFAULT_CONFIG_PATH
    logging.debug(config_file)

configuration = rohe_utils.load_config(config_file)
logging.debug(configuration)
db_config = DBConf(**configuration["db_authentication"])
db_collection = DBCollection(**configuration["db_collection"])
db_client = MDBClient(db_config)

connector_config = ConnectorConfig(**configuration["connector"])
collector_config = CollectorConfig(**configuration["collector"])

rest_config = {
    "db_client": db_client,
    "db_collection": db_collection,
    "connector_config": connector_config,
    "collector_config": collector_config,
    "agent_image": configuration["agent_image"],
}
debug(rest_config)
api.add_resource(
    RoheRegistration,
    "/registration",
    resource_class_kwargs=rest_config,
)
api.add_resource(
    RoheAgentManager,
    "/agent/<string:command>",
    resource_class_kwargs=rest_config,
)
