import sys, os
import argparse
import json

# from dotenv import load_dotenv
# load_dotenv()


import qoa4ml.qoaUtils as qoa_utils
from qoa4ml.QoaClient import QoaClient


from dotenv import load_dotenv
load_dotenv()

main_path = os.getenv('ROHE_PATH')
print(f"This is main path: {main_path}")
sys.path.append(main_path)

from app.services.image_processing.processingService import ProcessingService
from app.modules.connectors.storage.minioStorageConnector import MinioConnector
import lib.roheUtils as roheUtils


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Processing Service")
    parser.add_argument('--conf', type= str, help='configuration file',
                        default= "processing_service.yaml")
    # Parse the parameters
    args = parser.parse_args()
    config_file = args.conf

    # yaml load configuration file
    config = roheUtils.load_config(file_path= config_file)
    if not config:
        print("Something also wrong with rohe utils load config function. Third attempt to load config using rohe config load yaml config function")
        config = roheUtils.load_yaml_config(file_path= config_file)

    config['max_thread'] = int(config['max_thread'])
    config['processing_config']['min_request_period'] = int(config['processing_config']['min_request_period'])
    config['processing_config']['max_request_period'] = int(config['processing_config']['max_request_period'])

    print(f"This is the config: {config}")

    minio_connector = MinioConnector(storage_info= config.get('minio_config'))

    config['minio_connector'] = minio_connector
    service = ProcessingService(config)
    service.run()