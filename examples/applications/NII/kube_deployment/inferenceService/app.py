
import os, sys
import json
import argparse
from dotenv import load_dotenv
load_dotenv()
import threading
from qoa4ml import qoaUtils
from qoa4ml.QoaClient import QoaClient



# set the ROHE to be in the system path
def get_parent_dir(file_path, levels_up=1):
    file_path = os.path.abspath(file_path)  # Get the absolute path of the running file
    parent_path = file_path
    for _ in range(levels_up):
        parent_path = os.path.dirname(parent_path)
    return parent_path

up_level = 6
root_path = get_parent_dir(__file__, up_level)
print(root_path)
sys.path.append(root_path)


from lib.restService import RoheRestService
from examples.applications.NII.kube_deployment.inferenceService.modules.classificationObject import ClassificationObject
from examples.applications.NII.kube_deployment.inferenceService.services.objectClassificationService import ClassificationRestService
from examples.applications.NII.utilities.minioStorageConnector import MinioConnector


def load_minio_storage(storage_info):
    minio_connector = MinioConnector(storage_info= storage_info)
    return minio_connector

if __name__ == '__main__': 

    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Inference Service")
    parser.add_argument('--port', type= int, help='default port', default=9000)

    parser.add_argument('--conf', type= str, help='configuration file', 
            default= "examples/applications/NII/kube_deployment/inferenceService/configurations/inference_service.json")

    parser.add_argument('--relative_path', type= bool, help='specify whether it is a relative path', default=True)

    # Parse the parameters
    args = parser.parse_args()

    port = int(args.port)
    config_file = args.conf
    relative_path = args.relative_path

    if relative_path:
        config_file = os.path.join(root_path, config_file)

    # load configuration file
    with open(config_file, 'r') as json_file:
        config = json.load(json_file)    

    config['minio_config']['access_key'] = os.getenv("minio_client_access_key")
    config['minio_config']['secret_key'] = os.getenv("minio_client_secret_key")


    print(f"\n\nThis is config file: {config}\n\n")
    # load minio connector and ML Agent here
    minio_connector = load_minio_storage(storage_info= config.get('minio_config', {})) 
    MLAgent = ClassificationObject(files= config['model']['files'],
                                    input_shape= config['model']['input_shape'],
                                    model_from_config= True) 

    model_lock = threading.Lock() 
    config['minio_connector'] = minio_connector
    config['MLAgent'] = MLAgent
    config['lock'] = model_lock

    print(f"\n\nThis is config file: {config}\n\n")

    classificationService = RoheRestService(config)
    classificationService.add_resource(ClassificationRestService, '/inference_service')
    classificationService.run(port=port)