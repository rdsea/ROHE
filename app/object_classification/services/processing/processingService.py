import sys
from threading import Thread

from core.common.restService import RoheRestService

import app.object_classification.modules.utils as pipeline_utils
from app.object_classification.services.processing.processingServiceController import (
    ProcessingServiceController,
)
from app.object_classification.services.processing.processingServiceExecutor import (
    ProcessingServiceExecutor,
)


class ProcessingService:
    def __init__(
        self, config: dict, port: int, endpoint: str = "/processing_service_controller"
    ) -> None:
        #  time parser
        retry_delay: dict = config["processing"]["request"]["retry_delay"]
        for k, v in retry_delay.items():
            retry_delay[k] = pipeline_utils.parse_time(time_str=v)
        print(f"This is parsed time: {config['processing']['request']['retry_delay']}")

        self.executor = ProcessingServiceExecutor(config)
        rest_config = {"processing_service_executor": self.executor}
        self.rest_service = RoheRestService(rest_config)
        self.rest_service.add_resource(ProcessingServiceController, endpoint)
        self.port = port

    def run(self):
        executor_thread = Thread(target=self.executor.run)
        executor_thread.start()
        self.rest_service.run(port=self.port)
