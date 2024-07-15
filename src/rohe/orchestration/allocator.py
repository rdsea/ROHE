import time
from typing import Dict

import numpy as np
import pymongo

from ..common.data_models import (
    MongoCollection,
    NodeData,
    OrchestrateAlgorithmConfig,
    ServiceData,
    ServiceQueueConfig,
)
from ..common.logger import logger
from ..storage.mongo import MDBClient
from .orchestration_algorithm.manager import AlgorithmManager
from .resource_management import Node, Service, ServiceInstance, ServiceQueue


class Allocator:
    def __init__(
        self,
        db_client: MDBClient,
        node_collection: MongoCollection,
        service_collection: MongoCollection,
        service_queue_config: ServiceQueueConfig,
        orchestrate_algorithm_config: OrchestrateAlgorithmConfig,
    ):
        self.db_client = db_client
        self.node_collection = node_collection
        self.service_collection = service_collection
        self.service_queue = ServiceQueue(service_queue_config)
        self.nodes: Dict[str, Node] = {}
        self.services: Dict[str, Service] = {}
        self.orchestrate_config = orchestrate_algorithm_config
        self.algorithm_manager = AlgorithmManager(self.orchestrate_config)

    # TODO: refactor into a query to database
    def sync_node_from_db(self, node_mac=None, replace=True):
        try:
            # Sync specific node
            if node_mac is not None:
                # query node from db
                node_res = list(
                    self.db_client.aggregate(
                        self.node_collection,
                        {"mac_address": node_mac},
                        [("timestamp", pymongo.DESCENDING)],
                    )
                )
                if len(node_res) > 0:
                    node_db = node_res[0]
                    # if replace -> completely replace local node by node from database
                    if replace:
                        self.nodes[node_mac] = node_db["data"]
                    # if not replace -> update local node using node from database: To do
                    else:
                        pass
            # Sync all node
            else:
                # query the last updated nodes
                query = [
                    {"$sort": {"timestamp": 1}},
                    {
                        "$group": {
                            "_id": "$mac_address",
                            "timestamp": {"$last": "$timestamp"},
                            "data": {"$last": "$data"},
                        }
                    },
                ]
                node_list = list(self.db_client.get(self.node_collection, query))
                self.nodes.clear()
                for node in node_list:
                    # if replace -> completely replace local nodes by nodes from database
                    if replace:
                        self.nodes[node["_id"]] = Node(NodeData(**node["data"]))
                    # if not replace -> update local nodes using nodes from database: To do
                    else:
                        pass
            logger.info("Agent Sync nodes from Database complete")
        except Exception as e:
            logger.exception(f"Error in `sync_node_from_db` OrchestrationAgent: {e}")

    def sync_service_from_db(self, service_id=None, replace=True):
        try:
            # Sync specific service
            if service_id is not None:
                # query service from db
                service_res = list(
                    self.db_client.aggregate(
                        self.service_collection,
                        {"service_id": service_id},
                        [("timestamp", pymongo.DESCENDING)],
                    )
                )
                if len(service_res) > 0:
                    service_db = service_res[0]
                    # if replace -> completely replace local service by service from database
                    if replace:
                        self.services[service_id] = Service(ServiceData(**service_db))
                    else:
                        pass
                    # if number of service instance running lower than its required replicas, put it to service queue
            else:
                pipeline = [
                    {"$sort": {"timestamp": 1}},
                    {
                        "$group": {
                            "_id": "$service_id",
                            "replicas": {"$last": "$replicas"},
                            "running": {"$last": "$running"},
                            "timestamp": {"$last": "$timestamp"},
                            "data": {"$last": "$data"},
                        }
                    },
                ]
                service_list = list(
                    self.db_client.get(self.service_collection, pipeline)
                )
                self.services.clear()
                for service in service_list:
                    # if replace -> completely replace local services by services from database
                    if replace:
                        self.services[service["_id"]] = Service(
                            ServiceData(**service["data"])
                        )
                    else:
                        pass
            logger.info("Agent Sync services from Database complete")
        except Exception as e:
            logger.exception(f"Error in `sync_service_from_db` OrchestrationAgent: {e}")
            # print(traceback.print_exc())

    def sync_node_to_db(self, node_mac=None):
        try:
            if node_mac is not None:
                node_db = next(
                    iter(
                        self.db_client.aggregate(
                            self.node_collection,
                            {"mac_address": node_mac},
                            [("timestamp", pymongo.DESCENDING)],
                        )
                    )
                )
                node_db["data"] = self.nodes[node_mac].config.model_dump()
                node_db.pop("_id")
                node_db["timestamp"] = time.time()
                self.db_client.insert_one(self.node_collection, node_db)
            else:
                for key in self.nodes:
                    self.sync_node_to_db(key)
        except Exception as e:
            logger.exception(f"Error in `sync_node_to_db` OrchestrationAgent: {e}")
            # print(traceback.format_exc())

    def sync_service_to_db(self, service_id=None):
        try:
            if service_id is not None:
                service_db = next(
                    iter(
                        self.db_client.aggregate(
                            self.service_collection,
                            {"service_id": service_id},
                            [("timestamp", pymongo.DESCENDING)],
                        )
                    )
                )
                service_db["data"] = self.services[service_id].config.model_dump()
                service_db["replicas"] = self.services[service_id].replicas
                service_db["running"] = self.services[service_id].running
                service_db.pop("_id")
                service_db["timestamp"] = time.time()
                self.db_client.insert_one(self.service_collection, service_db)
            else:
                for key in self.services:
                    logger.info(key)
                    self.sync_service_to_db(key)
        except Exception as e:
            logger.exception(f"Error in `sync_service_to_db` OrchestrationAgent: {e}")

    def sync_from_db(self):
        try:
            self.sync_node_from_db()
            self.sync_service_from_db()
        except Exception as e:
            logger.exception(f"Error in `sync_from_db` OrchestrationAgent: {e}")

    def update_service(self, service: Service, node: Node):
        if node.id in service.node_list:
            service.node_list[node.id] += 1
        else:
            service.node_list[node.id] = 1
        new_instance = ServiceInstance(service, node)
        service.instances[new_instance.id] = new_instance
        service.instance_ids = list(service.instances.keys())
        service.running = len(service.instance_ids)
        service.self_update_config()

        return new_instance

    def update_node(self, node: Node, service: Service):
        node.cpu.used = node.cpu.used + service.cpu
        node.memory.used["rss"] += service.memory["rss"]
        node.memory.used["vms"] += service.memory["vms"]
        for dev in service.accelerator:
            for device in node.accelerator:
                av_accelerator = (
                    node.accelerator[device].capacity - node.accelerator[device].used
                )
                if (
                    node.accelerator[device].accelerator_type == dev
                    and service.accelerator[dev] < av_accelerator
                ):
                    node.accelerator[device].used = (
                        node.accelerator[device].used + service.accelerator[dev]
                    )
        used_proc = np.sort(np.array(node.cores.used))
        req_proc = np.array(service.cores)
        req_proc.resize(used_proc.shape)
        new_instance = self.update_service(service, node)
        req_proc = -np.sort(-req_proc)
        used_proc = used_proc + req_proc
        node.cores.used = used_proc.tolist()
        if service.id in node.service_list:
            node.service_list[service.id] += 1
        else:
            node.service_list[service.id] = 1
        node.self_update()
        return new_instance

    def build_service_queue(self):
        for service in self.services.values():
            if service.running != service.replicas:
                self.service_queue.put(service)

    def deallocate_service(self):
        pass

    def allocate(self):
        self.sync_from_db()
        logger.info("Sync completed")
        self.build_service_queue()
        new_service_instances = []
        while not self.service_queue.empty():
            p_service = self.service_queue.get()
            if p_service is None:
                break
            desired_state_different = p_service.replicas - p_service.running
            if desired_state_different < 0:
                for _ in range(-desired_state_different):
                    node_id = self.algorithm_manager.find_deallocate(
                        p_service,
                        self.nodes,
                    )

                    if node_id is None:
                        raise RuntimeError(
                            "Why we can't find anything to deallocate?????"
                        )
            else:
                for _ in range(desired_state_different):
                    node_id = self.algorithm_manager.find_allocate(
                        p_service,
                        self.nodes,
                    )
                    if node_id is None:
                        break

                    new_service_instances.append(
                        self.update_node(self.nodes[node_id], p_service)
                    )
        self.sync_node_to_db()
        self.sync_service_to_db()
        return new_service_instances
