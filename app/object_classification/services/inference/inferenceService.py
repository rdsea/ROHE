
from threading import Lock

from qoa4ml.QoaClient import QoaClient

from app.object_classification.lib.connectors.storage.minioStorageConnector import MinioConnector

from app.object_classification.services.inference.inferenceServiceExecutor import InferenceServiceExecutor
from app.object_classification.services.inference.inferenceServiceController import InferenceServiceController
from app.object_classification.lib.connectors.storage.mongoDBConnector import MongoDBConnector
from app.object_classification.modules.common import MongoDBInfo

from app.object_classification.lib.connectors.quixStream import QuixStreamProducer

from app.object_classification.modules.objectClassificationAgent import ObjectClassificationAgent
from app.object_classification.modules.common import InferenceEnsembleState

from core.common.restService import RoheRestService


class InferenceService():
    def __init__(self, config: dict, port: int,
                 executor_endpoint: str = '/inference_service',
                 controller_endpoint: str = '/inference_service_controller') -> None:
        
        # load dependencies
        minio_connector = MinioConnector(storage_info= config['external_services']['minio_storage'])

        MLAgent = ObjectClassificationAgent(load_model_params= config['model_info']['load_model_params'],
                                            model_id= config['model_info']['chosen_model_id'], 
                                            input_shape= config['model_info']['input_shape'])
        

        model_lock = Lock() 
        ensemble_lock = Lock()
        ensemble_controller = InferenceEnsembleState(config['ensemble'])


        config['minio_connector'] = minio_connector
        config['MLAgent'] = MLAgent
        config['model_lock'] = model_lock
        config['ensemble_lock'] = ensemble_lock
        config['ensemble_controller'] = ensemble_controller
    
        quix_producer = QuixStreamProducer(kafka_address= config['external_services']['kafka']['address'],
                                            topic_name= config['external_services']['kafka']['topic_name'])

        mongodb_info = MongoDBInfo(**config['external_services']['mongodb'])
        mongo_connector = MongoDBConnector(db_info= mongodb_info)
        config['mongo_connector'] = mongo_connector
        config['quix_producer'] = quix_producer


        if config.get('qoa_config'):
            print(f"\n\n\nAbout to load qoa client: {config['qoa_config']}")
            qoa_client = QoaClient(config['qoa_config'])
            config['qoaClient'] = qoa_client


        print(f"\n\nThis is config file: {config}\n\n")

        self.rest_service = RoheRestService(config)
        self.rest_service.add_resource(InferenceServiceExecutor, executor_endpoint)
        self.rest_service.add_resource(InferenceServiceController, controller_endpoint)
        self.port = port

    def run(self):
        self.rest_service.run(port= self.port)
