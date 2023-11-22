
import threading
from qoa4ml.QoaClient import QoaClient

from app.object_classification.lib.connectors.storage.minioStorageConnector import MinioConnector

from app.object_classification.services.inference.inferenceServiceExecutor import InferenceServiceExecutor
from app.object_classification.services.inference.inferenceServiceController import InferenceServiceController

from app.object_classification.modules.objectClassificationAgent import ObjectClassificationAgent

from lib.rohe.restService import RoheRestService

from app.object_classification.modules.common import InferenceEnsembleState

class InferenceService():
    def __init__(self, config: dict, port: int,
                 executor_endpoint: str = '/inference_service',
                 controller_endpoint: str = '/inference_service_controller') -> None:
        
        # load dependencies
        minio_connector = MinioConnector(storage_info= config['minio_config'])
        MLAgent = ObjectClassificationAgent(model_info= config['model_info'],
                                        input_shape= config['model_info']['input_shape'],
                                        model_from_config= True) 
        model_lock = threading.Lock() 

        ensemble_controller = InferenceEnsembleState(config['ensemble'])


        config['minio_connector'] = minio_connector
        config['MLAgent'] = MLAgent
        config['lock'] = model_lock
        config['ensemble_controller'] = ensemble_controller
    
        if config.get('qoa_config'):
            print(f"About to load qoa client: {config['qoa_config']}")
            qoa_client = QoaClient(config['qoa_config'])
            config['qoaClient'] = qoa_client

        print(f"\n\nThis is config file: {config}\n\n")

        self.rest_service = RoheRestService(config)
        self.rest_service.add_resource(InferenceServiceExecutor, executor_endpoint)
        self.rest_service.add_resource(InferenceServiceController, controller_endpoint)
        self.port = port

    def run(self):
        self.rest_service.run(port= self.port)
