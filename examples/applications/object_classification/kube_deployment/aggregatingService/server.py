
import os, sys
import argparse
import qoa4ml.qoaUtils as qoa_utils


# set the ROHE to be in the system path
lib_level = os.environ.get('LIB_LEVEL')
if not lib_level:
    lib_level = 5
main_path = config_file = qoa_utils.get_parent_dir(__file__,lib_level)
sys.path.append(main_path)

# from lib.service_connectors.mongoDBConnector import MongoDBConnector, MongoDBInfo
from lib.service_connectors.mongoDBConnector import MongoDBInfo

from lib.services.object_classification.aggregatingService import AggregatingService
import lib.roheUtils as roheUtils

from aggregating_function import average_probability

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
