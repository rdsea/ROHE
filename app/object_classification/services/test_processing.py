import sys, os
import argparse


from dotenv import load_dotenv
load_dotenv()

main_path = os.getenv('ROHE_PATH')
print(f"This is main path: {main_path}")
sys.path.append(main_path)


from app.object_classification.lib.connectors.storage.minioStorageConnector import MinioConnector
from app.object_classification.services.processingServiceExecutor import ProcessingServiceExecutor

import lib.roheUtils as roheUtils


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Ingestion Service")
    parser.add_argument('--conf', type= str, help='specify configuration file path', 
                        default= 'processing_config.yaml')

    # Parse the parameters
    args = parser.parse_args()

    config_file = args.conf

 
    config = roheUtils.load_config(file_path= config_file)
    if not config:
        print("Something also wrong with rohe utils load config function. Third attempt to load config using rohe config load yaml config function")
        config = roheUtils.load_yaml_config(file_path= config_file)

    config['processing_config']['max_thread'] = int(config['processing_config']['max_thread'])
    config['processing_config']['min_waiting_period'] = int(config['processing_config']['min_waiting_period'])
    config['processing_config']['max_waiting_period'] = int(config['processing_config']['max_waiting_period'])

    print(f"This is the config: {config}")

    minio_connector = MinioConnector(storage_info= config.get('minio_storage_service'))

    config['minio_connector'] = minio_connector

    inference_server = "http://localhost:30005/inference_service"
    config['inference_server'] = {}
    config['inference_server']['urls'] = ("http://localhost:30005/inference_service","http://localhost:30000/inference_service")

    executor = ProcessingServiceExecutor(config=config)

    executor.run()