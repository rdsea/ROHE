
import os, sys
import argparse
import qoa4ml.qoaUtils as qoa_utils


from dotenv import load_dotenv
load_dotenv()

main_path = os.getenv('ROHE_PATH')
print(f"This is main path: {main_path}")
sys.path.append(main_path)

# from lib.service_connectors.mongoDBConnector import MongoDBConnector, MongoDBInfo
# from app.modules.connectors.storage.mongoDBConnector import MongoDBInfo

from app.object_classification.modules.common import MongoDBInfo
from app.services.image_processing.aggregatingService import AggregatingService

import lib.roheUtils as roheUtils

from aggregating_functions import average_probability

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Argument for Inference Service")
    parser.add_argument('--conf', type= str, help='configuration file', 
            default= "aggregating_service.yaml")

    # Parse the parameters
    args = parser.parse_args()
    config_file = args.conf

    
    # yaml load configuration file
    config = roheUtils.load_config(file_path= config_file)
    if not config:
        print("Something also wrong with rohe utils load config function. Third attempt to load config using rohe config load yaml config function")
        config = roheUtils.load_yaml_config(file_path= config_file)

    mongodb_info = MongoDBInfo(**config['mongodb'])
    # db_connector = MongoDBConnector(db_info= mongodb_info)
    
    print(f"This is mongodb config: {mongodb_info.__dict__}")
    print(f"This is kafka config: {config['kafka']}")
    print(f"This is aggregating config: {config['aggregating']}")
    

    service = AggregatingService(kafka_address= config['kafka']['address'], 
                                 topic_name= config['kafka']['topic_name'], 
                                 aggregate_function= average_probability,
                                 mongodb_info= mongodb_info,
                                 agg_config= config['aggregating'])
    service.start_service()
