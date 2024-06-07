import logging
import time
import traceback
from threading import Timer
from typing import Dict

import pymongo

from rohe.storage.abstract import MDBClient

from ..common.data_models import NodeData, ServiceData
from ..common.rohe_object import RoheObject
from ..orchestration.ensemble_optimization.scoring import (
    orchestrate as scoring_orchestrate,
)
from .resource_management.resource import Node, Service, ServiceQueue

logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)


class RoheAgentV1(RoheObject):
    def __init__(self, configuration, sync=True, log_lev=2):
        try:
            super().__init__(logging_level=log_lev)
            self.conf = configuration
            self.db_client: MDBClient = self.conf["db_client"]
            self.node_collection = self.conf["node_collection"]
            self.service_collection = self.conf["service_collection"]
            self.nodes: Dict[str, Node] = {}
            self.services: Dict[str, Service] = {}
            self.orchestrate_config = configuration["orchestrate_config"]
            self.service_queue = ServiceQueue(configuration["service_queue"])
            if sync:
                self.sync_from_db()
            self.orches_flag = True
            self.update_flag = False
            # self.show_services()
            # self.show_nodes()
        except Exception as e:
            logging.error("Error in `__init__` RoheAgentV1: {}".format(e))

    def start(self):
        try:
            # Periodically check service queue and allocate service
            self.orches_flag = True
            self.orchestrate()
        except Exception as e:
            logging.error("Error in `start` RoheAgentV1: {}".format(e))

    def allocate_service(self):
        pass

    def sync_from_db(self):
        try:
            self.sync_node_from_db()
            self.sync_service_from_db()
        except Exception as e:
            logging.error("Error in `sync_from_db` RoheAgentV1: {}".format(e))

    def orchestrate(self):
        try:
            if self.orches_flag:
                logging.info("Agent Start Orchestrating")
                self.sync_from_db()
                logging.info("Sync completed")
                scoring_orchestrate(
                    self.nodes,
                    self.services,
                    self.service_queue,
                    self.orchestrate_config,
                )
                self.show_services()
                self.sync_node_to_db()
                self.sync_service_to_db()
                logging.info("Sync nodes and services to Database completed")
                self.timer = Timer(self.conf["timer"], self.orchestrate)
                self.timer.start()
        except Exception as e:
            print(traceback.format_exc())
            logging.error("Error in `orchestrate` RoheAgentV1: {}".format(e))

    def stop(self):
        try:
            self.orches_flag = False
        except Exception as e:
            logging.error("Error in `stop` RoheAgentV1: {}".format(e))

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
            logging.error("Error in `sync_node_from_db` RoheAgentV1: {}".format(e))

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
            logging.error("Error in `sync_service_from_db` RoheAgentV1: {}".format(e))
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
            logging.error("Error in `sync_node_to_db` RoheAgentV1: {}".format(e))
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
            logging.error("Error in `sync_service_to_db` RoheAgentV1: {}".format(e))

    def show_nodes(self):
        try:
            logging.info("############ NODES LIST ############")
            for node_key in self.nodes:
                logging.info("{} : {}".format(self.nodes[node_key], node_key))
            logging.info("Nodes Size: {}".format(len(self.nodes)))
        except Exception as e:
            logging.error("Error in `show_nodes` RoheAgentV1: {}".format(e))

    def show_services(self):
        try:
            logging.info("############ SERVICES LIST ############")
            for service_key in self.services:
                logging.info(self.services[service_key])
            logging.info("Services Size: ".format())
        except Exception as e:
            logging.error("Error in `show_services` RoheAgentV1: {}".format(e))
