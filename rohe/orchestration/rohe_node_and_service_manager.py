import logging
import time
from typing import Any, Dict

import pymongo
from flask import jsonify, request
from flask_restful import Resource

from ..common.data_models import (
    AddNodeRequest,
    AddServiceRequest,
    NodeAddress,
    NodeData,
    RemoveNodeRequest,
    ServiceData,
)
from ..storage.abstract import MDBClient
from .resource_management.resource import Service

logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)


class RoheNodeAndServiceManager(Resource):
    def __init__(self, **kwargs) -> None:
        try:
            super().__init__()
            self.conf = kwargs
            self.agent = self.conf["agent"]
            self.db_client: MDBClient = self.conf["db_client"]
            self.node_collection = self.conf["node_collection"]
            self.service_collection = self.conf["service_collection"]
        except Exception as e:
            logging.error("Error in `__init__` RoheNodeAndServiceManager: {}".format(e))

    ################################ NODE FUNCTIONS ################################
    # check if node exist in database
    def is_node_exist(self, mac_address: str) -> bool:
        try:
            # find node by MAC address
            node = list(self.db_client.find(self.node_collection, {"mac": mac_address}))
            return bool(node)
        except Exception as e:
            logging.error(
                "Error in `is_node_exist` RoheNodeAndServiceManager: {}".format(e)
            )
            return False

    # check node status
    def get_node_status(self, mac_add):
        # get node status by MAC address
        try:
            node_db = list(
                self.db_client.aggregate(
                    self.node_collection,
                    {"mac_address": mac_add},
                    [("timestamp", pymongo.DESCENDING)],
                )
            )[0]
            return node_db["status"]
        except Exception as e:
            logging.error(
                "Error in `get_node_status` RoheNodeAndServiceManager: {}".format(e)
            )
            return None

    def delete_node(self, mac_add: str):
        try:
            # Delete node from MAC address
            self.db_client.delete_many(self.node_collection, {"mac_address": mac_add})
        except Exception as e:
            logging.error(
                "Error in `delete_node` RoheNodeAndServiceManager: {}".format(e)
            )

    def update_node_to_db(self, node):
        try:
            node_db = list(
                self.db_client.aggregate(
                    self.node_collection,
                    {"mac_address": node["MAC"]},
                    [("timestamp", pymongo.DESCENDING)],
                )
            )[0]
            node_db.pop("_id")
            node_db["status"] = node["status"]
            node_db["timestamp"] = time.time()
            node_db["data"] = node
            # To do: improve merge_dict function to update node
            # node_db["data"] = merge_dict(node_db["data"],node)
            self.db_client.insert_one(self.node_collection, node_db)
        except Exception as e:
            logging.error(
                "Error in `update_node_to_db` RoheNodeAndServiceManager: {}".format(e)
            )

    def add_node_to_db(self, node: NodeData):
        try:
            metadata: Dict[str, Any] = {}
            metadata["status"] = node.status
            metadata["timestamp"] = time.time()
            metadata["data"] = node.model_dump()
            metadata["mac_address"] = node.mac_address
            self.db_client.insert_one(self.node_collection, metadata)
        except Exception as e:
            logging.error(
                "Error in `add_node_to_db` RoheNodeAndServiceManager: {}".format(e)
            )

    def add_nodes(self, node_data: Dict[str, NodeData]) -> dict:
        try:
            # add multiple nodes (as dictionary) to database - node_data contains node configurations
            results = {}
            for node_key, node in node_data.items():
                if self.is_node_exist(node.mac_address):
                    self.update_node_to_db(node)
                    results[node_key] = "Updated"
                else:
                    self.add_node_to_db(node)
                    results[node_key] = "Added"
            return {"result": results}
        except Exception as e:
            logging.error(
                "Error in `add_nodes` RoheNodeAndServiceManager: {}".format(e)
            )
            return {"result": "fail"}

    def remove_node_db(self, node_address: NodeAddress):
        try:
            self.db_client.delete_many(
                self.node_collection, {"mac_address": node_address.mac_address}
            )
        except Exception as e:
            logging.error(
                "Error in `remove_node_db` RoheNodeAndServiceManager: {}".format(e)
            )

    def remove_nodes(self, node_data: Dict[str, NodeAddress]) -> dict:
        try:
            results = {}
            for node_key, node_address in node_data.items():
                self.remove_node_db(node_address)
                results[node_key] = "Removed"
            return {"result": results}
        except Exception as e:
            logging.error(
                "Error in `remove_nodes` RoheNodeAndServiceManager: {}".format(e)
            )
            return {"result": "fail"}

    def get_nodes(self):
        try:
            query = [
                {"$sort": {"timestamp": 1}},
                {
                    "$group": {
                        "_id": "$mac_address",
                        "status": {"$last": "$status"},
                        "timestamp": {"$last": "$timestamp"},
                        "data": {"$last": "$data"},
                    }
                },
            ]
            node_list = list(self.db_client.get(self.node_collection, query))
            return node_list
        except Exception as e:
            logging.error(
                "Error in `get_nodes` RoheNodeAndServiceManager: {}".format(e)
            )
            return []

    ################################ SERVICE FUNCTIONS ################################

    def is_service_exist(self, service_id: str) -> bool:
        try:
            service = list(
                self.db_client.find(self.service_collection, {"service_id": service_id})
            )
            return bool(service)
        except Exception as e:
            logging.error(
                "Error in `is_service_exist` RoheNodeAndServiceManager: {}".format(e)
            )
            return False

    def get_service_status(self, service_id: str) -> dict:
        try:
            service_db = list(
                self.db_client.aggregate(
                    self.service_collection,
                    {"service_id": service_id},
                    [("timestamp", pymongo.DESCENDING)],
                )
            )[0]
            return {
                "status": {
                    "running": service_db["running"],
                    "replicas": service_db["replicas"],
                }
            }
        except Exception as e:
            logging.error(
                "Error in `get_service_status` RoheNodeAndServiceManager: {}".format(e)
            )
            return {"status": "fail"}

    def remove_service_db(self, service: Service):
        try:
            self.db_client.delete_many(
                self.service_collection, {"service_id": service.id}
            )
        except Exception as e:
            logging.error(
                "Error in `remove_service_db` RoheNodeAndServiceManager: {}".format(e)
            )

    def remove_services(self, service_data) -> dict:
        try:
            results = {}
            for app_key in service_data:
                application_name = service_data[app_key]
                for s_key in application_name:
                    service = application_name[s_key]
                    self.remove_service_db(service)
                    results[s_key] = "Removed"
            return {"result": results}
        except Exception as e:
            logging.error(
                "Error in `remove_services` RoheNodeAndServiceManager: {}".format(e)
            )
            return {"result": "fail"}

    def add_service_to_db(self, service_data: ServiceData, application_name: str):
        try:
            metadata: Dict[str, Any] = {}
            metadata["status"] = service_data.status
            metadata["replicas"] = service_data.replicas
            metadata["running"] = service_data.running
            metadata["application_name"] = application_name
            metadata["timestamp"] = time.time()
            metadata["data"] = service_data.model_dump()
            metadata["service_id"] = service_data.service_id
            self.db_client.insert_one(self.service_collection, metadata)
        except Exception as e:
            logging.error(
                "Error in `add_service_to_db` RoheNodeAndServiceManager: {}".format(e)
            )

    def add_services(self, data: Dict[str, Dict[str, ServiceData]]):
        try:
            results = {}
            for application_name, services in data.items():
                for service_key, service_data in services.items():
                    if self.is_service_exist(service_data.service_id):
                        self.update_service_to_db(service_data)
                        results[service_key] = "Updated"
                    else:
                        self.add_service_to_db(service_data, application_name)
                        results[service_key] = "Added"
            return {"result": results}
        except Exception as e:
            logging.error(
                "Error in `add_services` RoheNodeAndServiceManager: {}".format(e)
            )
            return {"result": "fail"}

    def update_service_to_db(self, service: ServiceData):
        try:
            service_db = list(
                self.db_client.aggregate(
                    self.service_collection,
                    {"service_id": service.service_id},
                    [("timestamp", pymongo.DESCENDING)],
                )
            )[0]
            service_db.pop("_id")
            service_db["status"] = service.status.value
            service_db["replicas"] = service.replicas
            service_db["running"] = service.running
            service_db["timestamp"] = time.time()
            service_db["data"] = service.model_dump()

            # To do: improve merge_dict function to update service
            # service_db["data"] = merge_dict(service_db["data"],service)
            self.db_client.insert_one(self.service_collection, service_db)
        except Exception as e:
            logging.error(
                "Error in `update_service_to_db` RoheNodeAndServiceManager: {}".format(
                    e
                )
            )

    def get_services(self):
        try:
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
            service_list = list(self.db_client.get(self.service_collection, pipeline))
            return service_list
        except Exception as e:
            logging.error(
                "Error in `get_services` RoheNodeAndServiceManager: {}".format(e)
            )
            return []

    ################################ REST FUNCTIONS ################################

    def get(self):
        try:
            args = request.query_string.decode("utf-8").split("&")
            # get param from args here
            return jsonify({"status": args})
        except Exception as e:
            logging.error(
                "Error in `get_nodes` RoheNodeAndServiceManager: {}".format(e)
            )
            return jsonify({"status": "unsupported"})

    def post(self, command: str):
        try:
            if not request.is_json:
                response = {"result": "only support json type"}
            response = {}
            if command == "add-node":
                node_data = AddNodeRequest.model_validate_json(request.data)
                response = self.add_nodes(node_data.data)

            elif command == "remove-all-nodes":
                self.db_client.drop(self.node_collection)
                response = {"result": "All nodes removed"}

            elif command == "remove-node":
                remove_node_data = RemoveNodeRequest.model_validate_json(request.data)
                response = self.remove_nodes(remove_node_data.data)

            elif command == "add-service":
                service_data = AddServiceRequest.model_validate_json(request.data)
                response = self.add_services(service_data.data)

            elif command == "remove-all-services":
                self.db_client.drop(self.service_collection)
                response = {"result": "All services removed"}

            # TODO: improve this, the body is too big now
            elif command == "remove-service":
                pass
                # response = self.remove_services(args["data"])

            elif command == "get-all-services":
                response = {"result": self.get_services()}

            elif command == "get-all-nodes":
                response = {"result": self.get_nodes()}

            elif command == "start-agent":
                self.agent.start()
                response = {"result": "Agent started"}

            elif command == "stop-agent":
                self.agent.stop()
                response = {"result": "Agent Stop"}

            else:
                response = {"result": "Unknow command"}
            return jsonify({"status": "success", "response": response})
        except Exception as e:
            logging.error(
                "Error in `get_nodes` RoheNodeAndServiceManager: {}".format(e)
            )
            return jsonify({"status": "fail"})

    def put(self):
        try:
            if request.is_json:
                args = request.get_json(force=True)
            # get param from args here
            return jsonify({"status": args})
        except Exception as e:
            logging.error(
                "Error in `get_nodes` RoheNodeAndServiceManager: {}".format(e)
            )
            return jsonify({"status": "unsupported"})

    def delete(self):
        try:
            if request.is_json:
                args = request.get_json(force=True)
            # get param from args here
            return jsonify({"status": args})
        except Exception as e:
            logging.error(
                "Error in `get_nodes` RoheNodeAndServiceManager: {}".format(e)
            )
            return jsonify({"status": "unsupported"})
