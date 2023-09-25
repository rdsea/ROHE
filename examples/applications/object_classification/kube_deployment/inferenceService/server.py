
import os, sys
import argparse
import threading

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
from lib.modules.object_classification.classificationObject import ClassificationObjectV1
from lib.services.object_classification.objectClassificationService import ClassificationRestService
from lib.service_connectors.minioStorageConnector import MinioConnector
import lib.roheUtils as roheUtils


if __name__ == '__main__': 
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Inference Service")
    parser.add_argument('--port', type= int, help='default port', default=30005)

    parser.add_argument('--conf', type= str, help='configuration file', 
            default= "./configurations/inference_service.yaml")


    # Parse the parameters
    args = parser.parse_args()
    port = int(args.port)
    config_file = args.conf

    # yaml load configuration file
    config = roheUtils.load_config(file_path= config_file)
    if not config:
        print("Something wrong with rohe utils load config function. Third attempt to load config using rohe config load yaml config function")
        config = roheUtils.load_yaml_config(file_path= config_file)
    print(f"\n\nThis is config file: {config}\n\n")

    # load dependencies
    minio_connector = MinioConnector(storage_info= config['minio_config'])
    MLAgent = ClassificationObjectV1(model_config= config['model']['files'],
                                    input_shape= config['model']['input_shape'],
                                    model_from_config= True) 
    model_lock = threading.Lock() 
    qoa_client = QoaClient(config['qoa_config'])

    config['minio_connector'] = minio_connector
    config['MLAgent'] = MLAgent
    config['lock'] = model_lock
    config['qoaClient'] = qoa_client
    
    # start server
    classificationService = RoheRestService(config)
    classificationService.add_resource(ClassificationRestService, '/inference_service')
    classificationService.run(port=port)