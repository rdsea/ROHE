import argparse
import logging
import traceback

import rohe.lib.rohe_utils as rohe_utils
from rohe.common.rest_service import RoheRestService
from rohe.messaging.abstract import MessagingConnectionConfig
from rohe.observation.agent_manager import RoheAgentManager
from rohe.observation.registration import RoheRegistration
from rohe.storage.abstract import DBCollection, DBConf, MDBClient
from rohe.variable import ROHE_PATH

logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)


DEFAULT_CONFIG_PATH = "/config/observationConfig.yaml"

if __name__ == "__main__":
    # init_env_variables()
    parser = argparse.ArgumentParser(
        description="Argument for Rohe Observation Service"
    )
    parser.add_argument("--conf", help="configuration file", default=None)
    parser.add_argument("--port", help="default port", default=5010)

    # Parse the parameters
    args = parser.parse_args()
    config_file = args.conf
    # config_path = args.path
    port = int(args.port)

    # load configuration file
    if not config_file:
        config_file = ROHE_PATH + DEFAULT_CONFIG_PATH
        logging.debug(config_file)

    try:
        configuration = rohe_utils.load_config(config_file)
        logging.debug(configuration)
        dbConfig = DBConf.parse_obj(configuration["db_authentication"])
        dbCollection = DBCollection.parse_obj(configuration["db_collection"])
        dbClient = MDBClient(dbConfig)

        connectorConfig = MessagingConnectionConfig.parse_obj(
            configuration["connector"]
        )
        collectorConfig = MessagingConnectionConfig.parse_obj(
            configuration["collector"]
        )

        restConfig = {
            "dbClient": dbClient,
            "dbCollection": dbCollection,
            "connectorConfig": connectorConfig,
            "collectorConfig": collectorConfig,
            "agent_image": configuration["agent_image"],
        }
        observationService = RoheRestService(restConfig)
        observationService.add_resource(RoheRegistration, "/registration")
        observationService.add_resource(RoheAgentManager, "/agent")
        observationService.run(port=port)
    except Exception as e:
        logging.error("Error in starting Observation service: {}".format(e))
