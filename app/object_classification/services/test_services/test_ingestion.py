import sys, os
import argparse


from dotenv import load_dotenv
load_dotenv()

main_path = os.getenv('ROHE_PATH')
print(f"This is main path: {main_path}")
sys.path.append(main_path)


from app.object_classification.lib.roheService import RoheRestService
from app.object_classification.lib.connectors.storage.minioStorageConnector import MinioConnector
from app.object_classification.services.ingestion.ingestionService import IngestionService

import lib.roheUtils as roheUtils



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Ingestion Service")
    parser.add_argument('--port', type= int, help='default port', default=3000)
    parser.add_argument('--conf', type= str, help='specify configuration file path', 
                        default= 'ingestion_config.yaml')

    # Parse the parameters
    args = parser.parse_args()
    port = int(args.port)

    config_file = args.conf

    # yaml load configuration file
    config = roheUtils.load_config(file_path= config_file)
    if not config:
        print("Something also wrong with rohe utils load config function. Third attempt to load config using rohe config load yaml config function")
        config = roheUtils.load_yaml_config(file_path= config_file)


    # Minio Connector for uploading image
    minio_connector = MinioConnector(storage_info= config['storage']['minio'])
    config['minio_connector'] = minio_connector

    # start server
    rest_service = RoheRestService(config)
    rest_service.add_resource(IngestionService, '/ingestion_service')
    rest_service.run(port=port)