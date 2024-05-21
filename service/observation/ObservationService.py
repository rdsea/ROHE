import traceback
import argparse
import sys, os
# User must export ROHE_PATH befor using
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)

from core.common.restService import RoheRestService
import lib.roheUtils as rohe_utils
from core.observation.registration import RoheRegistration
from core.observation.agentManager import RoheAgentManager
from core.storage.abstract import MDBClient, DBConf, DBCollection
from core.messaging.abstract import MessagingConnectionConfig
import logging, traceback
logging.basicConfig(format='%(asctime)s:%(levelname)s -- %(message)s', level=logging.INFO)


DEFAULT_CONFIG_PATH="/config/observationConfig.yaml"

if __name__ == '__main__': 
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Rohe Observation Service")
    parser.add_argument('--conf', help='configuration file', default=None)
    parser.add_argument('--port', help='default port', default=5010)

    # Parse the parameters
    args = parser.parse_args()
    config_file = args.conf
    #config_path = args.path
    port = int(args.port)

    # load configuration file
    if not config_file:
        config_file = ROHE_PATH+DEFAULT_CONFIG_PATH
        logging.debug(config_file)
    
    try:
        configuration = rohe_utils.load_config(config_file)
        logging.debug(configuration)
        dbConfig = DBConf.parse_obj(configuration["db_authentication"])
        dbCollection = DBCollection.parse_obj(configuration["db_collection"])
        dbClient = MDBClient(dbConfig)

        connectorConfig = MessagingConnectionConfig.parse_obj(configuration["connector"])
        collectorConfig = MessagingConnectionConfig.parse_obj(configuration["collector"])
        
        restConfig = {"dbClient": dbClient, 
                      "dbCollection": dbCollection, 
                      "connectorConfig":connectorConfig, 
                      "collectorConfig": collectorConfig,
                      "agent_image": configuration["agent_image"]}  
        observationService = RoheRestService(restConfig)
        observationService.add_resource(RoheRegistration, '/registration')
        observationService.add_resource(RoheAgentManager, '/agent')
        observationService.run(port=port)
    except Exception as e:
        logging.error("Error in starting Observation service: {}".format(e))
        