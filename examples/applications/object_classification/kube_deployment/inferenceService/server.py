
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



from lib.services.restService import RoheRestService
from lib.modules.object_classification.classificationObject import NIIClassificationObject
from lib.services.object_classification.objectClassificationService import ClassificationRestService
from lib.service_connectors.minioStorageConnector import MinioConnector
import lib.roheUtils as roheUtils


if __name__ == '__main__': 
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Inference Service")
    parser.add_argument('--conf', type= str, help='specify configuration file path')

    parser.add_argument('--port', type= int, help='default port', default=30005)
    parser.add_argument('--enable_qoa', type= int, choices= [0, 1], 
                        help='debugging feature - false when debugging the pipeline itself',
                        default= 1)


    # Parse the parameters
    args = parser.parse_args()

    port = int(args.port)
    config_file = args.conf
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
    print(f"This is the config: {config}")

    print("*" * 20)
    print(f"This is qoa config: {config['qoa_config']}")
    print("*" * 20)
    print(f"this is the state of qoa: {enable_qoa}")

    # enable qoa in testing and production environment
    if enable_qoa:
        if config['qoa_config'] is not None:
            config['qoaClient'] = QoaClient(config_dict= config['qoa_config'])
    
    minio_connector = MinioConnector(storage_info= config['minio_config'])

    MLAgent = NIIClassificationObject(model_config= config['model']['files'],
                                    input_shape= config['model']['input_shape'],
                                    model_from_config= True) 

    model_lock = threading.Lock() 
    config['minio_connector'] = minio_connector
    config['MLAgent'] = MLAgent
    config['lock'] = model_lock
    

    classificationService = RoheRestService(config)
    classificationService.add_resource(ClassificationRestService, '/inference_service')
    classificationService.run(port=port)