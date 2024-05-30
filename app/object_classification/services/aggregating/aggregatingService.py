from threading import Thread

from core.common.restService import RoheRestService

from app.object_classification.services.aggregating.aggregatingServiceController import (
    AggregatingServiceController,
)
from app.object_classification.services.aggregating.aggregatingServiceExecutor import (
    AggregatingServiceExecutor,
)


class AggregatingService:
    def __init__(
        self, config: dict, port: int, endpoint: str = "/aggregating_service_controller"
    ) -> None:
        self.executor = AggregatingServiceExecutor(config)
        rest_config = {"aggregating_service_executor": self.executor}
        self.rest_service = RoheRestService(rest_config)
        self.rest_service.add_resource(AggregatingServiceController, endpoint)
        self.port = port

    def run(self):
        # controller_thread = Thread(target=self.rest_service.run)
        # controller_thread.start()

        # self.executor.run()

        executor_thread = Thread(target=self.executor.run)
        executor_thread.start()

        self.rest_service.run(port=self.port)
