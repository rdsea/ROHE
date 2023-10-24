import sys, os
import json
import argparse
from threading import Lock

from dotenv import load_dotenv
load_dotenv()

import qoa4ml.qoaUtils as qoa_utils


# set the ROHE to be in the system path
lib_level = os.environ.get('LIB_LEVEL')
if not lib_level:
    lib_level = 5

main_path = config_file = qoa_utils.get_parent_dir(__file__,lib_level)
sys.path.append(main_path)
root_path = main_path

from app.modules.service_connectors.storage_connectors.minioStorageConnector import MinioConnector
from app.services.image_processing.ingestionService import IngestionService
import lib.roheUtils as roheUtils


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Ingestion Service")
    parser.add_argument('--conf', type= str, help='specify configuration file path', 
                        default= 'ingestion_service.yaml')

    # Parse the parameters
    args = parser.parse_args()

    config_file = args.conf

    # yaml load configuration file
    config = roheUtils.load_config(file_path= config_file)
    if not config:
        print("Something also wrong with rohe utils load config function. Third attempt to load config using rohe config load yaml config function")
        config = roheUtils.load_yaml_config(file_path= config_file)

    config['max_thread'] = int(config['max_thread'])
    config['mqtt_config']['broker_info']['keep_alive'] = int(config['mqtt_config']['broker_info']['keep_alive'])
    
    print(f"This is the config: {config}")
    storage_lock = Lock()

    # Minio Connector for uploading image
    minio_connector = MinioConnector(storage_info= config['minio_config'])
    config['minio_connector'] = minio_connector
    config['storage_lock'] = storage_lock

    service = IngestionService(config= config)
    service.run()