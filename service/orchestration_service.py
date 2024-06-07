# import argparse
import logging

from flask import Flask
from flask_restful import Api

import rohe.lib.rohe_utils as rohe_utils
from rohe.orchestration.orchestration_agent import RoheAgentV1
from rohe.orchestration.rohe_node_and_service_manager import RoheNodeAndServiceManager
from rohe.storage.abstract import DBCollection, DBConf, MDBClient
from rohe.variable import ROHE_PATH

# import traceback


logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)

DEFAULT_CONFIG_PATH = "/config/orchestrationConfig.yaml"

app = Flask(__name__)
api = Api(app)
rohe_agent = None

# parser = argparse.ArgumentParser(description="Argument for Rohe Orchestration Service")
# parser.add_argument("--port", help="server port", default=5002)
# parser.add_argument("--conf", help="configuration file", default=None)
# args = parser.parse_args()
config_file = None
port = 5002
if not config_file:
    config_file = ROHE_PATH + DEFAULT_CONFIG_PATH
    logging.info(config_file)

configuration = rohe_utils.load_config(config_file)
logging.debug(configuration)

db_config = DBConf.parse_obj(configuration["db_authentication"])
db_client = MDBClient(db_config)
node_collection = DBCollection.parse_obj(configuration["db_node_collection"])
service_collection = DBCollection.parse_obj(configuration["db_service_collection"])

rest_config = configuration.update(
    {
        "db_client": db_client,
        "node_collection": node_collection,
        "service_collection": service_collection,
    }
)

rohe_agent = RoheAgentV1(configuration, False)
configuration["agent"] = rohe_agent
api.add_resource(
    RoheNodeAndServiceManager,
    "/management",
    "/management/<string:command>",
    resource_class_kwargs=configuration,
)
