

from app.modules.image_processing.restful_service_module import RestfulServiceModule
from lib.rohe.restService import RoheRestService


class RestfulService():
    def __init__(self, service_controller_resource: dict, 
                 service_endpoint: str, port: int):
        self.service = RoheRestService(service_controller_resource)
        self.service.add_resource(RestfulServiceModule, service_endpoint)
        self.run(port= int(port))

    def run(self, port):
        self.service.run(port= port)


# if __name__ == '__main__': 
#     # import argparse
#     # import os, sys
#     # import qoa4ml.qoaUtils as qoa_utils


#     from app.modules.inference_service_controller import InferenceServiceController, EnsembleState
#     from app.modules.restful_service_controller import ControllerMangagement

#     from app.modules.image_processing.classificationObject import ClassificationObjectV1
#     from app.modules.service_connectors.storage_connectors.minioStorageConnector import MinioConnector
#     from app.modules.service_connectors.storage_connectors.mongoDBConnector import MongoDBConnector, MongoDBInfo
#     from app.modules.service_connectors.broker_connectors.quixStreamProducer import KafkaStreamProducer
#     import threading

#     import lib.roheUtils as roheUtils

#     parser = argparse.ArgumentParser(description="Argument for Inference Service")
#     parser.add_argument('--port', type= int, help='default port', default=30005)

#     parser.add_argument('--conf', type= str, help='configuration file', 
#             default= "./inference_service.yaml")
    
#     parser.add_argument('--service_endpoint', type= str, help='service endpoint', 
#             default= "/inference_service")
    
#     args = parser.parse_args()
#     config_file = args.conf


#     # yaml load configuration file
#     config = roheUtils.load_config(file_path= config_file)
#     if not config:
#         print("Something wrong with rohe utils load config function. Third attempt to load config using rohe config load yaml config function")
#         config = roheUtils.load_yaml_config(file_path= config_file)
        
#     print(f"\n\nThis is config file: {config}\n\n")


#     # load dependencies
#     minio_connector = MinioConnector(storage_info= config['minio_config'])
#     MLAgent = ClassificationObjectV1(model_info= config['model_info'],
#                                     input_shape= config['model_info']['input_shape'],
#                                     model_from_config= True) 
#     model_lock = threading.Lock() 

#     ensemble_controller = EnsembleState(config['ensemble'])
#     kafka_producer = KafkaStreamProducer(kafka_address= config['kafka']['address'],
#                                         topic_name= config['kafka']['topic_name'])
#     config['kafka_producer'] = kafka_producer
    
#     mongodb_info = MongoDBInfo(**config['mongodb'])
#     mongo_connector = MongoDBConnector(db_info= mongodb_info)
#     config['mongo_connector'] = mongo_connector

#     config['minio_connector'] = minio_connector
#     config['MLAgent'] = MLAgent
#     config['lock'] = model_lock
#     config['ensemble_controller'] = ensemble_controller
    
#     config['qoaClient'] = None
    

#     inference_service_controller = InferenceServiceController(config= config)
    
    
#     controller_manager = ControllerMangagement()
#     service_controller_resource = {
#         'service_controller': inference_service_controller,
#         # 'service_controller': None,
#         'controller_manager': controller_manager,
#     }


#     service = RestfulService(service_controller_resource= service_controller_resource,
#                              service_endpoint= args.service_endpoint,
#                              port= args.port)
    