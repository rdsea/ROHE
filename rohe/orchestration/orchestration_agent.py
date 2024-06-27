import logging
import traceback
from threading import Timer

from ..common.data_models import (
    MongoCollection,
    OrchestrateAlgorithmConfig,
    ServiceQueueConfig,
)
from ..common.rohe_object import RoheObject
from ..storage.abstract import MDBClient
from .allocator import Allocator

logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)


class OrchestrationAgent(RoheObject):
    def __init__(
        self,
        db_client: MDBClient,
        node_collection: MongoCollection,
        service_collection: MongoCollection,
        orchestrate_algorithm_config: OrchestrateAlgorithmConfig,
        orchestration_interval: float,
        service_queue_config: ServiceQueueConfig,
        sync=True,
        log_lev=2,
    ):
        super().__init__(logging_level=log_lev)
        self.db_client: MDBClient = db_client
        self.node_collection = node_collection
        self.service_collection = service_collection
        self.orchestration_interval = orchestration_interval
        self.allocator = Allocator(
            self.db_client,
            self.node_collection,
            self.service_collection,
            service_queue_config,
            orchestrate_algorithm_config,
        )
        if sync:
            self.allocator.sync_from_db()
        self.orches_flag = True
        self.update_flag = False

    def start(self):
        try:
            # Periodically check service queue and allocate service
            self.orches_flag = True
            self.orchestrate()
            self.show_nodes()
            self.show_services()
        except Exception as e:
            logging.error("Error in `start` OrchestrationAgent: {}".format(e))

    def allocate_service(self):
        pass

    def orchestrate(self):
        try:
            if self.orches_flag:
                logging.info("Agent Start Orchestrating")
                self.allocator.allocate()
                # self.show_services()
                logging.info("Agent Finish Orchestrating")
                self.timer = Timer(self.orchestration_interval, self.orchestrate)
                self.timer.start()
        except Exception as e:
            print(traceback.format_exc())
            logging.error("Error in `orchestrate` OrchestrationAgent: {}".format(e))

    def stop(self):
        try:
            self.orches_flag = False
        except Exception as e:
            logging.error("Error in `stop` OrchestrationAgent: {}".format(e))

    def show_nodes(self):
        try:
            logging.info("############ NODES LIST ############")
            for node_key in self.allocator.nodes:
                logging.info("{} : {}".format(self.allocator.nodes[node_key], node_key))
            logging.info("Nodes Size: {}".format(len(self.allocator.nodes)))
        except Exception as e:
            logging.error("Error in `show_nodes` OrchestrationAgent: {}".format(e))

    def show_services(self):
        try:
            logging.info("############ SERVICES LIST ############")
            for service_key in self.allocator.services:
                logging.info(self.allocator.services[service_key])
            logging.info(f"Services Size: {len(self.allocator.services.keys())}")
        except Exception as e:
            logging.error("Error in `show_services` OrchestrationAgent: {}".format(e))
