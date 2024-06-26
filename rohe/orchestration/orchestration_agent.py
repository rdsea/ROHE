import logging
import traceback
from threading import Timer
from typing import Dict

from rohe.common.data_models import (
    MongoCollection,
    OrchestrateAlgorithmConfig,
    ServiceQueueConfig,
)
from rohe.storage.abstract import MDBClient

from ..common.rohe_object import RoheObject
from .allocator import Allocator
from .resource_management import Node, Service, ServiceQueue

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
        self.nodes: Dict[str, Node] = {}
        self.services: Dict[str, Service] = {}
        self.orchestration_interval = orchestration_interval
        self.service_queue = ServiceQueue(service_queue_config)
        self.allocator = Allocator(
            self.db_client,
            self.node_collection,
            self.service_collection,
            self.service_queue,
            self.nodes,
            self.services,
            orchestrate_algorithm_config,
        )
        if sync:
            self.allocator.sync_from_db()
        self.orches_flag = True
        self.update_flag = False
        # self.show_services()
        # self.show_nodes()

    def start(self):
        try:
            # Periodically check service queue and allocate service
            self.orches_flag = True
            self.orchestrate()
        except Exception as e:
            logging.error("Error in `start` OrchestrationAgent: {}".format(e))

    def allocate_service(self):
        pass

    def orchestrate(self):
        try:
            if self.orches_flag:
                logging.info("Agent Start Orchestrating")
                self.allocator.allocate()
                self.show_services()
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
            for node_key in self.nodes:
                logging.info("{} : {}".format(self.nodes[node_key], node_key))
            logging.info("Nodes Size: {}".format(len(self.nodes)))
        except Exception as e:
            logging.error("Error in `show_nodes` OrchestrationAgent: {}".format(e))

    def show_services(self):
        try:
            logging.info("############ SERVICES LIST ############")
            for service_key in self.services:
                logging.info(self.services[service_key])
            logging.info(f"Services Size: {len(self.services.keys())}")
        except Exception as e:
            logging.error("Error in `show_services` OrchestrationAgent: {}".format(e))
