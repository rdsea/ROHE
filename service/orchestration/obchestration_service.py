import os
import sys

ROHE_PATH = os.getenv("ROHE_PATH")
import argparse
import logging
import traceback

from flask import Flask
from flask_restful import Api

import rohe.lib.rohe_utils as rohe_utils
from rohe.orchestration.orchestration_agent import RoheAgentV1
from rohe.orchestration.rohe_node_and_service_manager import RoheNodeAndServiceManager
from rohe.storage.abstract import DBCollection, DBConf, MDBClient

logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)

DEFAULT_CONFIG_PATH = "/config/orchestrationConfig.yaml"

app = Flask(__name__)
api = Api(app)
rohe_agent = None

if __name__ == "__main__":
    # init_env_variables()
    parser = argparse.ArgumentParser(
        description="Argument for Rohe Orchestration Service"
    )
    parser.add_argument("--port", help="server port", default=5002)
    parser.add_argument("--conf", help="configuration file", default=None)
    args = parser.parse_args()
    try:
        config_file = args.conf
        port = args.port
        if not config_file:
            config_file = ROHE_PATH + DEFAULT_CONFIG_PATH
            logging.info(config_file)

        configuration = rohe_utils.load_config(config_file)
        logging.debug(configuration)

        dbConfig = DBConf.parse_obj(configuration["db_authentication"])
        dbClient = MDBClient(dbConfig)
        nodeCollection = DBCollection.parse_obj(configuration["db_node_collection"])
        serviceCollection = DBCollection.parse_obj(
            configuration["db_service_collection"]
        )

        restConfig = configuration.update(
            {
                "dbClient": dbClient,
                "node_collection": nodeCollection,
                "service_collection": serviceCollection,
            }
        )

        rohe_agent = RoheAgentV1(configuration, False)
        configuration["agent"] = rohe_agent
        api.add_resource(
            RoheNodeAndServiceManager,
            "/management",
            resource_class_kwargs=configuration,
        )
        app.run(debug=True, port=port)
    except:
        traceback.print_exc()
