import logging

from flask import Flask
from flask_restful import Api

import rohe.lib.rohe_utils as rohe_utils
from rohe.common.data_models import OrchestrationServiceConfig
from rohe.orchestration.rohe_node_and_service_manager import RoheNodeAndServiceManager
from rohe.variable import ROHE_PATH

logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)

DEFAULT_CONFIG_PATH = "/config/orchestrationConfig.yaml"
DEFAULT_PORT = 5002

app = Flask(__name__)
api = Api(app)
rohe_agent = None

config_file = None
port = DEFAULT_PORT
if not config_file:
    config_file = ROHE_PATH + DEFAULT_CONFIG_PATH
    logging.info(config_file)

configuration = rohe_utils.load_config(config_file)
assert configuration is not None

orchestration_service_config = OrchestrationServiceConfig.parse_obj(configuration)
api.add_resource(
    RoheNodeAndServiceManager,
    "/management",
    "/management/<string:command>",
    resource_class_kwargs={"configuration": orchestration_service_config},
)
