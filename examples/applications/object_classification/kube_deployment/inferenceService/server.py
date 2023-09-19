
import os, sys
import json
import argparse
import threading
import qoa4ml.qoaUtils as qoa_utils

from dotenv import load_dotenv
load_dotenv()



# set the ROHE to be in the system path
lib_level = os.environ.get('LIB_LEVEL')
if not lib_level:
    lib_level = 5

main_path = config_file = qoa_utils.get_parent_dir(__file__,lib_level)
print(f"This if main path: {main_path}")
sys.path.append(main_path)

import qoa4ml.qoaUtils as qoa_utils
from qoa4ml.QoaClient import QoaClient

qoa_conf_path = os.environ.get('QOA_CONF_PATH')
if not qoa_conf_path:
    qoa_conf_path = "./examples/applications/object_classification/kube_deployment/inferenceService/configurations/qoa_conf.json"

qoa_conf = qoa_utils.load_config(qoa_conf_path)
print(qoa_conf)
qoaClient = QoaClient(config_dict=qoa_conf)


from lib.services.restService import RoheRestService
from lib.modules.object_classification.classificationObject import NIIClassificationObject
from lib.services.object_classification.objectClassificationService import ClassificationRestService
from lib.service_connectors.minioStorageConnector import MinioConnector


def load_minio_storage(storage_info):
    minio_connector = MinioConnector(storage_info= storage_info)
    return minio_connector

if __name__ == '__main__': 

    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Inference Service")
    parser.add_argument('--port', type= int, help='default port', default=30005)

    parser.add_argument('--conf', type= str, help='configuration file', 
            default= "examples/applications/object_classification/kube_deployment/inferenceService/configurations/inference_service.json")

    parser.add_argument('--relative_path', type= bool, help='specify whether it is a relative path', default=True)

    # Parse the parameters
    args = parser.parse_args()

    port = int(args.port)
    config_file = args.conf
    relative_path = args.relative_path

    if relative_path:
        # main_path = qoa_utils.get_parent_dir(__file__,lib_level + 1)
        print(f"This is root path: {main_path}")
        config_file = os.path.join(main_path, config_file)


    # load configuration file
    with open(config_file, 'r') as json_file:
        config = json.load(json_file)    

    # config['minio_config']['access_key'] = os.getenv("minio_client_access_key")
    # config['minio_config']['secret_key'] = os.getenv("minio_client_secret_key")

    # config['model']['files']['architecture_file'] = os.getenv("architecture_file")
    # config['model']['files']['weights_file'] = os.getenv("weights_file")

    print(f"\n\nThis is config file: {config}\n\n")
    # load minio connector and ML Agent here
    minio_connector = load_minio_storage(storage_info= config.get('minio_config', {})) 

    MLAgent = NIIClassificationObject(model_config= config['model']['files'],
                                    input_shape= config['model']['input_shape'],
                                    model_from_config= True) 

    model_lock = threading.Lock() 
    config['minio_connector'] = minio_connector
    config['MLAgent'] = MLAgent
    config['lock'] = model_lock
    config['qoaClient'] = qoaClient

    print(f"\n\nThis is config file: {config}\n\n")

    classificationService = RoheRestService(config)
    classificationService.add_resource(ClassificationRestService, '/inference_service')
    classificationService.run(port=port)