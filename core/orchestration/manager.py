import sys, os
import pymongo, time
from flask import jsonify, request
from flask_restful import Resource
# User must export ROHE_PATH befor using
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
import logging
logging.basicConfig(format='%(asctime)s:%(levelname)s -- %(message)s', level=logging.INFO)

from core.orchestration.ensembleOptimization.scoring import orchestrate as scoringOrchestrate



class RoheNodeAndServiceManager(Resource):
    def __init__(self, **kwargs) -> None:
        try:
            super().__init__()
            self.conf = kwargs
            self.agent = self.conf["agent"]
            self.dbClient = self.conf["dbClient"]
            self.node_collection = self.conf["node_collection"]
            self.service_collection = self.conf["service_collection"]
        except Exception as e:
            logging.error("Error in `__init__` RoheNodeAndServiceManager: {}".format(e))


    ################################ NODE FUNCTIONS ################################
    # check if node exist in database
    def is_node_exist(self,mac_add) -> bool:
        try: 
            # find node by MAC address
            node = list(self.dbClient.find(self.node_collection,{"mac":mac_add}))
            return bool(node)
        except Exception as e:
            logging.error("Error in `is_node_exist` RoheNodeAndServiceManager: {}".format(e))
            return False
    
    # check node status
    def get_node_status(self,mac_add):
        # get node status by MAC address
        try: 
            node_db = list(self.dbClient.aggregate(self.node_collection,{"mac":mac_add}, [('timestamp', pymongo.DESCENDING)]))[0]
            return node_db["status"]
        except Exception as e:
            logging.error("Error in `get_node_status` RoheNodeAndServiceManager: {}".format(e))
            return None

    def delete_node(self, mac_add):
        try:
            # Delete node from MAC address
            self.dbClient.delete_many(self.node_collection, {"mac":mac_add})
        except Exception as e:
            logging.error("Error in `delete_node` RoheNodeAndServiceManager: {}".format(e))

    def update_node_to_db(self, node):
        try:
            node_db = list(self.dbClient.aggregate(self.node_collection,{"mac":node["MAC"]},[('timestamp', pymongo.DESCENDING)]))[0]
            node_db.pop("_id")
            node_db["status"] = node["status"]
            node_db["timestamp"] = time.time()
            node_db["data"] = node
            # To do: improve merge_dict function to update node
            # node_db["data"] = merge_dict(node_db["data"],node)
            self.dbClient.insert_one(self.node_collection,node_db)
        except Exception as e:
            logging.error("Error in `update_node_to_db` RoheNodeAndServiceManager: {}".format(e))
        

    def add_node_to_db(self, node):
        try:
            metadata = {}
            metadata["status"] = node["status"]
            metadata["timestamp"] = time.time()
            metadata["data"] = node
            metadata["mac"] = node["MAC"]
            self.dbClient.insert_one(self.node_collection,metadata)
        except Exception as e:
            logging.error("Error in `add_node_to_db` RoheNodeAndServiceManager: {}".format(e))

    def add_nodes(self, node_data) -> dict:
        try:
            # add multiple nodes (as dictionary) to database - node_data contains node configurations
            results = {}
            for node_key in node_data:
                node = node_data[node_key]

                if self.is_node_exist(node["MAC"]):
                    self.update_node_to_db(node)
                    results[node_key] = "Updated"
                else:
                    self.add_node_to_db(node)
                    results[node_key] = "Added"
            return {"result":results}
        except Exception as e:
            logging.error("Error in `add_nodes` RoheNodeAndServiceManager: {}".format(e))
            return {"result":"fail"}
    
    def remove_node_db(self, node):
        try:
            self.dbClient.delete_many(self.node_collection,{"mac":node["MAC"]})
        except Exception as e:
            logging.error("Error in `remove_node_db` RoheNodeAndServiceManager: {}".format(e))

    def remove_nodes(self, node_data) -> dict:
        try:
            results = {}
            for node_key in node_data:
                node = node_data[node_key]
                self.remove_node_db(node)
                results[node_key] = "Removed"
            return {"result":results}
        except Exception as e:
            logging.error("Error in `remove_nodes` RoheNodeAndServiceManager: {}".format(e))
            return {"result":"fail"}
    
    def get_nodes(self):
        try:
            pipeline = [{"$sort":{"timestamp":1}},{"$group": {"_id": "$mac", "status": {"$last": "$status"},"timestamp": {"$last": "$timestamp"}, "data":{"$last": "$data"}}}]
            node_list = list(self.dbClient.get(self.node_collection,pipeline))
            return node_list
        except Exception as e:
            logging.error("Error in `get_nodes` RoheNodeAndServiceManager: {}".format(e))
            return []

    ################################ SERVICE FUNCTIONS ################################

    def is_service_exist(self,service_id) -> bool:
        try:
            service = list(self.dbClient.find(self.service_collection,{"service_id":service_id}))
            return bool(service)
        except Exception as e:
            logging.error("Error in `is_service_exist` RoheNodeAndServiceManager: {}".format(e))
            return False

    def get_service_status(self,service_id) -> dict:
        try:
            service_db = list(self.dbClient.aggregate(self.service_collection,{"service_id":service_id},[('timestamp', pymongo.DESCENDING)]))[0]
            return {"status": {"running": service_db["running"], "replicas": service_db["replicas"]}}
        except Exception as e:
            logging.error("Error in `get_service_status` RoheNodeAndServiceManager: {}".format(e))
            return {"status": "fail"}
    
    def remove_service_db(self, service):
        try:
            self.dbClient.delete_many(self.service_collection,{"service_id":service["service_id"]})
        except Exception as e:
            logging.error("Error in `remove_service_db` RoheNodeAndServiceManager: {}".format(e))

    def remove_services(self, service_data) -> dict:
        try:
            results = {}
            for app_key in service_data:
                application_name = service_data[app_key]
                for s_key in application_name:
                    service = application_name[s_key]
                    self.remove_service_db(service)
                    results[s_key] = "Removed"
            return {"result":results}
        except Exception as e:
            logging.error("Error in `remove_services` RoheNodeAndServiceManager: {}".format(e))
            return {"result":"fail"}
    
    def add_service_to_db(self, service, application_name):
        try:
            metadata = {}
            metadata["status"] = service["status"]
            metadata["replicas"] = service["replicas"]
            metadata["running"] = service["running"]
            metadata["application_name"] = application_name
            metadata["timestamp"] = time.time()
            metadata["data"] = service
            metadata["service_id"] = service["service_id"]
            self.dbClient.insert_one(self.service_collection,metadata)
        except Exception as e:
            logging.error("Error in `add_service_to_db` RoheNodeAndServiceManager: {}".format(e))

    def add_services(self, data):
        try:
            results = {}
            for app_key in data:
                application_name = data[app_key]
                for s_key in application_name:
                    service = application_name[s_key]
                    if self.is_service_exist(service["service_id"]):
                        self.update_service_to_db(service)
                        results[s_key] = "Updated"
                    else:
                        self.add_service_to_db(service, app_key)
                        results[s_key] = "Added"
            return {"result":results}
        except Exception as e:
            logging.error("Error in `add_services` RoheNodeAndServiceManager: {}".format(e))
            return {"result":"fail"}
    
    def update_service_to_db(self, service):
        try:
            service_db = list(self.dbClient.aggregate(self.service_collection, {"service_id":service["service_id"]}, [('timestamp', pymongo.DESCENDING)]))[0]
            service_db.pop("_id")
            service_db["status"] = service["status"]
            service_db["replicas"] = service["replicas"]
            service_db["running"] = service["running"]
            service_db["timestamp"] = time.time()
            service_db["data"] = service
            # To do: improve merge_dict function to update service
            # service_db["data"] = merge_dict(service_db["data"],service)
            self.dbClient.insert_one(self.service_collection, service_db)
        except Exception as e:
            logging.error("Error in `update_service_to_db` RoheNodeAndServiceManager: {}".format(e))

    def get_services(self):
        try:
            pipeline = [{"$sort":{"timestamp":1}},{"$group": {"_id": "$service_id","replicas": {"$last": "$replicas"}, "running": {"$last": "$running"},"timestamp": {"$last": "$timestamp"}, "data":{"$last": "$data"}}}]
            service_list = list(self.dbClient.get(self.service_collection, pipeline))
            return service_list
        except Exception as e:
            logging.error("Error in `get_services` RoheNodeAndServiceManager: {}".format(e))
            return []

    ################################ REST FUNCTIONS ################################
        
    def get(self):
        try:
            args = request.query_string.decode("utf-8").split("&")
            # get param from args here
            return jsonify({'status': args})
        except Exception as e:
            logging.error("Error in `get_nodes` RoheNodeAndServiceManager: {}".format(e))
            return jsonify({'status': 'unsupported'})


    def post(self):
        try:
            if request.is_json:
                args = request.get_json(force=True)
                response = {}
                if "command" in args:
                    command = args["command"]
                    if command == "ADD NODE":
                        response = self.add_nodes(args["data"])
                    elif command == "REMOVE ALL NODE":
                        self.dbClient.drop(self.node_collection)
                        response = {"result":"All nodes removed"}
                    elif command == "REMOVE NODE":
                        response =self.remove_nodes(args["data"])
                    elif command == "ADD SERVICE":
                        response =self.add_services(args["data"])
                    elif command == "REMOVE ALL SERVICE":
                        self.dbClient.drop(self.service_collection)
                        response = {"result":"All services removed"}
                    elif command == "REMOVE SERVICE":
                        response = self.remove_services(args["data"])
                    elif command == "GET ALL SERVICES":
                        response = {"result":self.get_services()}
                    elif command == "GET ALL NODES":
                        response = {"result":self.get_nodes()}
                    elif command == "START AGENT":
                        self.agent.start()
                        response = {"result":"Agent started"}
                    elif command == "STOP AGENT":
                        self.agent.stop()
                        response = {"result":"Agent Stop"}
                    else:
                        response = {"result":"Unknow command"}
                else:
                    response = {"result":"Command not found"}
            return jsonify({'status': "success", "response":response})
        except Exception as e:
            logging.error("Error in `get_nodes` RoheNodeAndServiceManager: {}".format(e))
            return jsonify({'status': 'fail'})

    def put(self):
        try:
            if request.is_json:
                args = request.get_json(force=True)
            # get param from args here
            return jsonify({'status': args})
        except Exception as e:
            logging.error("Error in `get_nodes` RoheNodeAndServiceManager: {}".format(e))
            return jsonify({'status': 'unsupported'})

    def delete(self):
        try:
            if request.is_json:
                args = request.get_json(force=True)
            # get param from args here
            return jsonify({'status': args})
        except Exception as e:
            logging.error("Error in `get_nodes` RoheNodeAndServiceManager: {}".format(e))
            return jsonify({'status': 'unsupported'})