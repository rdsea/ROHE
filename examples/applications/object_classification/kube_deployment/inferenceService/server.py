
import os, sys
import json
import argparse
import threading
import qoa4ml.qoaUtils as qoa_utils

from dotenv import load_dotenv
load_dotenv()


import qoa4ml.qoaUtils as qoa_utils
from qoa4ml.QoaClient import QoaClient


# set the ROHE to be in the system path
lib_level = os.environ.get('LIB_LEVEL')
if not lib_level:
    lib_level = 5

main_path = config_file = qoa_utils.get_parent_dir(__file__,lib_level)
sys.path.append(main_path)
import lib.roheUtils as rohe_utils





from lib.services.restService import RoheRestService
from lib.modules.object_classification.classificationObject import NIIClassificationObject
from lib.services.object_classification.objectClassificationService import ClassificationRestService
from lib.service_connectors.minioStorageConnector import MinioConnector
import lib.roheUtils as roheUtils


if __name__ == '__main__': 
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Inference Service")
    parser.add_argument('--port', type= int, help='default port', default=30005)
    parser.add_argument('--enable_qoa', type= int, choices= [0, 1], 
                        help='debugging feature - false when debugging the pipeline itself',
                        default= 1)

    parser.add_argument('--conf', type= str, help='configuration file', 
            default= "/configurations/inference_service.yaml")

    parser.add_argument('--relative_path', type= bool, help='specify whether it is a relative path', default=True)

    current_path = qoa_utils.get_file_dir(__file__)
    # Parse the parameters
    args = parser.parse_args()

    port = int(args.port)
    config_file = current_path+args.conf
    enable_qoa = args.enable_qoa

    # # yaml load configuration file
    # config = qoa_utils.load_config(file_path= config_file, format= 1)
    # if config is None:
    #     print("Something wrong with qoa_utils load config function. Second attempt to use rohe utils")
    #     config = roheUtils.load_config(file_path= config_file, format= 1)
    #     if not config:
    #         print("Something also wrong with rohe utils load config function. Third attempt to load config using rohe config load yaml config function")
    #         config = roheUtils.load_yaml_config(file_path= config_file)
    #         print(f"This is the config: {config}")
    print(f"this is the path to config file: {config_file}")
    
    config = roheUtils.load_yaml_config(file_path= config_file)
    # print(f"This is the config: {config}")

    # print("*" * 20)
    # print(f"This is qoa config: {config['qoa_config']}")
    # print("*" * 20)
    # print(f"this is the state of qoa: {enable_qoa}")

    # # load configuration file
    config = rohe_utils.load_config(config_file)    

    # config['minio_config']['access_key'] = os.getenv("minio_client_access_key")
    # config['minio_config']['secret_key'] = os.getenv("minio_client_secret_key")

    # config['model']['files']['architecture_file'] = os.getenv("architecture_file")
    # config['model']['files']['weights_file'] = os.getenv("weights_file")

    print(f"\n\nThis is config file: {config}\n\n")
    # load minio connector and ML Agent here
    minio_connector = MinioConnector(storage_info= config['minio_config'])

    MLAgent = NIIClassificationObject(model_config= config['model']['files'],
                                    input_shape= config['model']['input_shape'],
                                    model_from_config= True) 

    model_lock = threading.Lock() 
    config['minio_connector'] = minio_connector
    config['MLAgent'] = MLAgent
    config['lock'] = model_lock
    config['qoaClient'] = QoaClient(config['qoa_config'])
    print("test")
    

    classificationService = RoheRestService(config)
    classificationService.add_resource(ClassificationRestService, '/inference_service')
    classificationService.run(port=port)