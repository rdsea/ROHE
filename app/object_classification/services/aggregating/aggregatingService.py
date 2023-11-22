
from threading import Thread

from app.object_classification.services.aggregating.aggregatingServiceExecutor import AggregatingServiceExecutor
from app.object_classification.services.aggregating.aggregatingServiceController import AggregatingServiceController

from lib.rohe.restService import RoheRestService

class ProcessingService():
    def __init__(self, config: dict, port: int,
                 endpoint: str = '/aggregating_service_controller') -> None:
        self.executor = AggregatingServiceExecutor(config)
        rest_config = {
            'aggregating_service_executor': self.executor
        }
        self.rest_service = RoheRestService(rest_config)
        self.rest_service.add_resource(AggregatingServiceController, endpoint)
        self.port = port

    def run(self):
        executor_thread = Thread(target=self.executor.run)
        executor_thread.start()
        
        self.rest_service.run(port= self.port)
