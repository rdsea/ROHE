import sys, os
import json

import argparse

from dotenv import load_dotenv
load_dotenv()

from threading import Lock

# set the ROHE to be in the system path
def get_parent_dir(file_path, levels_up=1):
    file_path = os.path.abspath(file_path)  # Get the absolute path of the running file
    parent_path = file_path
    for _ in range(levels_up):
        parent_path = os.path.dirname(parent_path)
    return parent_path

up_level = 6
root_path = get_parent_dir(__file__, up_level)
sys.path.append(root_path)

from examples.applications.NII.utilities.minioStorageConnector import MinioConnector
from examples.applications.NII.kube_deployment.dataIngestionService.services.ingestionService import IngestionService



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Ingestion Service")
    parser.add_argument('--conf', type= str, help='configuration file', 
            default= "examples/applications/NII/kube_deployment/dataIngestionService/configurations/ingestion_service.json")
    parser.add_argument('--relative_path', type= bool, help='specify whether it is a relative path', default=True)

    # Parse the parameters
    args = parser.parse_args()

    config_file = args.conf
    relative_path = args.relative_path

    if relative_path:
        config_file = os.path.join(root_path, config_file)

    storage_lock = Lock()
    # load configuration file
    with open(config_file, 'r') as json_file:
        config = json.load(json_file)    

    config['minio_config']['access_key'] = os.getenv("minio_client_access_key")
    config['minio_config']['secret_key'] = os.getenv("minio_client_secret_key")

    # Minio Connector for uploading image
    minio_connector = MinioConnector(storage_info= config['minio_config'])
    config['minio_connector'] = minio_connector

    config['storage_lock'] = storage_lock

    print(f"This is the minio connector: {minio_connector}")
    service = IngestionService(config= config)
    service.run()