import logging
import time

import numpy as np
import pymongo
from qoa4ml.config.configs import Dict

from rohe.storage.abstract import MDBClient

from ...common.data_models import MongoCollection, NodeData, ServiceData
from .node import Node
from .service import Service, ServiceInstance
from .service_queue import ServiceQueue


class Allocator:
    def __init__(
        self,
        db_client: MDBClient,
        node_collection: MongoCollection,
        service_collection: MongoCollection,
        service_queue: ServiceQueue,
        nodes: Dict[str, Node],
        services: Dict[str, Service],
    ) -> None:
        self.db_client = db_client
        self.node_collection = node_collection
        self.service_collection = service_collection
        self.service_queue = service_queue
        self.nodes = nodes
        self.services = services

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
                self.nodes = {}
                for node in node_list:
                    # if replace -> completely replace local nodes by nodes from database
                    if replace:
                        self.nodes[node["_id"]] = Node(NodeData(**node["data"]))
                    # if not replace -> update local nodes using nodes from database: To do
                    else:
                        pass
            logging.info("Agent Sync nodes from Database complete")
        except Exception as e:
            logging.error(
                "Error in `sync_node_from_db` OrchestrationAgent: {}".format(e)
            )

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
                self.services = {}
                for service in service_list:
                    # if replace -> completely replace local services by services from database
                    if replace:
                        self.services[service["_id"]] = Service(
                            ServiceData(**service["data"])
                        )
                    else:
                        pass
            logging.info("Agent Sync services from Database complete")
        except Exception as e:
            logging.error(
                "Error in `sync_service_from_db` OrchestrationAgent: {}".format(e)
            )
            # print(traceback.print_exc())

    def sync_node_to_db(self, node_mac=None):
        try:
            if node_mac is not None:
                node_db = list(
                    self.db_client.aggregate(
                        self.node_collection,
                        {"mac_address": node_mac},
                        [("timestamp", pymongo.DESCENDING)],
                    )
                )[0]
                node_db["data"] = self.nodes[node_mac].config.model_dump()
                node_db.pop("_id")
                node_db["timestamp"] = time.time()
                self.db_client.insert_one(self.node_collection, node_db)
            else:
                for key in self.nodes:
                    self.sync_node_to_db(key)
        except Exception as e:
            logging.error("Error in `sync_node_to_db` OrchestrationAgent: {}".format(e))
            # print(traceback.format_exc())

    def sync_service_to_db(self, service_id=None):
        try:
            if service_id is not None:
                service_db = list(
                    self.db_client.aggregate(
                        self.service_collection,
                        {"service_id": service_id},
                        [("timestamp", pymongo.DESCENDING)],
                    )
                )[0]
                service_db["data"] = self.services[service_id].config.model_dump()
                service_db["replicas"] = self.services[service_id].replicas
                service_db["running"] = self.services[service_id].running
                service_db.pop("_id")
                service_db["timestamp"] = time.time()
                self.db_client.insert_one(self.service_collection, service_db)
            else:
                for key in self.services:
                    logging.info(key)
                    self.sync_service_to_db(key)
        except Exception as e:
            logging.error(
                "Error in `sync_service_to_db` OrchestrationAgent: {}".format(e)
            )

    def sync_from_db(self):
        try:
            self.sync_node_from_db()
            self.sync_service_from_db()
        except Exception as e:
            logging.error("Error in `sync_from_db` OrchestrationAgent: {}".format(e))

    def update_service(self, node: Node, service: Service):
        if node.id in service.node_list:
            service.node_list[node.id] += 1
        else:
            service.node_list[node.id] = 1
        new_instance = ServiceInstance(service, node)
        service.instances[new_instance.id] = new_instance
        service.instance_ids = list(service.instances.keys())
        service.running = len(service.instance_ids)
        service.self_update_config()
        new_instance.generate_deployment()

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
        self.update_service(node, service)
        req_proc = -np.sort(-req_proc)
        used_proc = used_proc + req_proc
        node.cores.used = used_proc.tolist()
        if service.id in node.service_list:
            node.service_list[service.id] += 1
        else:
            node.service_list[service.id] = 1
        node.self_update()

    # def allocate(self,)