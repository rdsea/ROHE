
from threading import Thread

from app.object_classification.services.processing.processingServiceExecutor import ProcessingServiceExecutor
from app.object_classification.services.processing.processingServiceController import ProcessingServiceController

from lib.rohe.restService import RoheRestService

class ProcessingService():
    def __init__(self, config: dict, port: int,
                 endpoint: str = '/processing_service_controller') -> None:
        self.executor = ProcessingServiceExecutor(config)
        rest_config = {
            'processing_service_executor': self.executor
        }
        self.rest_service = RoheRestService(rest_config)
        self.rest_service.add_resource(ProcessingServiceController, endpoint)
        self.port = port

    def run(self):
        executor_thread = Thread(target=self.executor.run)
        executor_thread.start()
        self.rest_service.run(port= self.port)
