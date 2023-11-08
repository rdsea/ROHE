
import os, sys
import argparse
import threading

# from dotenv import load_dotenv
# load_dotenv()

import qoa4ml.qoaUtils as qoa_utils
from qoa4ml.QoaClient import QoaClient


from dotenv import load_dotenv
load_dotenv()

main_path = os.getenv('ROHE_PATH')
print(f"This is main path: {main_path}")
sys.path.append(main_path)

from lib.modules.restService.roheService import RoheRestService
from app.modules.image_processing.classificationObject import ClassificationObjectV1
from app.services.image_processing.objectClassificationService import ClassificationRestService, EnsembleState
from app.modules.connectors.storage.minioStorageConnector import MinioConnector
from app.modules.connectors.storage.mongoDBConnector import MongoDBConnector, MongoDBInfo
from app.modules.connectors.quixStream import KafkaStreamProducer

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
    MLAgent = ClassificationObjectV1(model_info= config['model_info'],
                                    input_shape= config['model_info']['input_shape'],
                                    model_from_config= True) 
    model_lock = threading.Lock() 


    # if config['ensemble']:
    #     kafka_producer = KafkaStreamProducer(kafka_address= config['kafka']['address'],
    #                                          topic_name= config['kafka']['topic_name'])
    #     config['kafka_producer'] = kafka_producer
        
    # else:
    #     mongodb_info = MongoDBInfo(**config['mongodb'])
    #     mongo_connector = MongoDBConnector(db_info= mongodb_info)
    #     config['mongo_connector'] = mongo_connector
    ensemble_controller = EnsembleState(config['ensemble'])
    kafka_producer = KafkaStreamProducer(kafka_address= config['kafka']['address'],
                                        topic_name= config['kafka']['topic_name'])
    config['kafka_producer'] = kafka_producer
    
    mongodb_info = MongoDBInfo(**config['mongodb'])
    mongo_connector = MongoDBConnector(db_info= mongodb_info)
    config['mongo_connector'] = mongo_connector

    config['minio_connector'] = minio_connector
    config['MLAgent'] = MLAgent
    config['lock'] = model_lock
    config['ensemble_controller'] = ensemble_controller
    

    if config.get('qoa_config'):
        print(f"About to load qoa client: {config['qoa_config']}")
        qoa_client = QoaClient(config['qoa_config'])
        config['qoaClient'] = qoa_client

    print(f"\n\nThis is config file: {config}\n\n")
    
    # start server
    classificationService = RoheRestService(config)
    classificationService.add_resource(ClassificationRestService, '/inference_service')
    classificationService.run(port=port)