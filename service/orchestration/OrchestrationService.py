import sys, os
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
import lib.roheUtils as rohe_utils
import argparse
from flask import Flask
from flask_restful import Api

from core.orchestration.manager import RoheNodeAndServiceManager
from core.orchestration.orchestrationAgent import RoheAgentV1
from core.storage.abstract import MDBClient, DBConf, DBCollection

import logging, traceback
logging.basicConfig(format='%(asctime)s:%(levelname)s -- %(message)s', level=logging.INFO)

DEFAULT_CONFIG_PATH="/config/orchestrationConfig.yaml"

app = Flask(__name__)
api = Api(app)
rohe_agent = None

if __name__ == '__main__': 
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Rohe Orchestration Service")
    parser.add_argument('--port', help='server port', default=5002)
    parser.add_argument('--conf', help='configuration file', default=None)
    args = parser.parse_args()
    try:
        config_file = args.conf
        port = args.port
        if not config_file:
            config_file = ROHE_PATH+DEFAULT_CONFIG_PATH
            logging.info(config_file)
        
        configuration = rohe_utils.load_config(config_file)
        logging.debug(configuration)

        dbConfig = DBConf.parse_obj(configuration["db_authentication"])
        dbClient = MDBClient(dbConfig)
        nodeCollection = DBCollection.parse_obj(configuration["db_node_collection"])
        serviceCollection = DBCollection.parse_obj(configuration["db_service_collection"])

        restConfig = configuration.update({"dbClient": dbClient, 
                      "node_collection": nodeCollection, 
                      "service_collection":serviceCollection})

        rohe_agent = RoheAgentV1(configuration,False)
        configuration["agent"] = rohe_agent
        api.add_resource(RoheNodeAndServiceManager, '/management',resource_class_kwargs=configuration)
        app.run(debug=True, port=port)
    except:
        traceback.print_exc()