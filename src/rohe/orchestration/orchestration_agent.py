from threading import Timer

from devtools import debug

from rohe.orchestration.deployment_management.k8s_client import K8sClient

from ..common.data_models import (
    MongoCollection,
    OrchestrateAlgorithmConfig,
    ServiceQueueConfig,
)
from ..common.logger import logger
from ..storage.abstract import MDBClient
from .allocator import Allocator


class OrchestrationAgent:
    def __init__(
        self,
        db_client: MDBClient,
        node_collection: MongoCollection,
        service_collection: MongoCollection,
        orchestrate_algorithm_config: OrchestrateAlgorithmConfig,
        orchestration_interval: float,
        service_queue_config: ServiceQueueConfig,
        sync=True,
    ):
        self.db_client: MDBClient = db_client
        self.node_collection = node_collection
        self.service_collection = service_collection
        self.orchestration_interval = orchestration_interval
        self.k8s_client = K8sClient()
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
            # self.show_nodes()
            # self.show_services()
        except Exception as e:
            logger.exception(f"Error in `start` OrchestrationAgent: {e}")

    def allocate_service(self):
        pass

    def orchestrate(self):
        try:
            if self.orches_flag:
                logger.info("Agent Start Orchestrating")
                new_service_instances = self.allocator.allocate()
                debug(new_service_instances)
                self.k8s_client.generate_deployment(new_service_instances[0])
                # self.show_services()
                logger.info("Agent Finish Orchestrating")
                self.timer = Timer(self.orchestration_interval, self.orchestrate)
                self.timer.start()
        except Exception as e:
            logger.exception(f"Error in `orchestrate` OrchestrationAgent: {e}")

    def stop(self):
        try:
            self.orches_flag = False
        except Exception as e:
            logger.exception(f"Error in `stop` OrchestrationAgent: {e}")

    def show_nodes(self):
        try:
            logger.info("############ NODES LIST ############")
            for node_key in self.allocator.nodes:
                logger.info(f"{self.allocator.nodes[node_key]} : {node_key}")
            logger.info(f"Nodes Size: {len(self.allocator.nodes)}")
        except Exception as e:
            logger.exception(f"Error in `show_nodes` OrchestrationAgent: {e}")

    def show_services(self):
        try:
            logger.info("############ SERVICES LIST ############")
            for service_key in self.allocator.services:
                logger.info(self.allocator.services[service_key])
            logger.info(f"Services Size: {len(self.allocator.services.keys())}")
        except Exception as e:
            logger.error(f"Error in `show_services` OrchestrationAgent: {e}")
