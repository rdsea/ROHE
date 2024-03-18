import qoa4ml.qoaUtils as qoaUtils
import sys, os
import pymongo, time
from flask import Flask, jsonify, request
from flask_restful import Resource, Api
from threading import Thread, Timer
# User must export ROHE_PATH befor using
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)

from core.orchestration.resourceManagement.resource import Node, Service, Service_Queue
from core.orchestration.ensembleOptimization.scoring import orchestrate as scoringOrchestrate
from lib.rohe.roheObject import RoheObject

main_path = config_file = qoaUtils.get_parent_dir(__file__,3)
sys.path.append(main_path)




app = Flask(__name__)
api = Api(app)

rohe_agent = None


class RoheOrchestrationService(Resource):
    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.conf = kwargs
        self.agent = self.conf["agent"]
        self.db_config = self.conf["database"]
        self.mongo_client = pymongo.MongoClient(self.db_config["url"])
        self.db = self.mongo_client[self.db_config["db_name"]]
        self.node_collection = self.db[self.db_config["node_collection"]]
        self.service_collection = self.db[self.db_config["service_collection"]]


    ################################ NODE FUNCTIONS ################################
    # check if node exist in database
    def is_node_exist(self,mac_add):
        node = list(self.node_collection.find({"mac":mac_add}))
        return bool(node)
    
    # check node status
    def get_node_status(self,mac_add):
        node_db = list(self.node_collection.find({"mac":mac_add}).sort([('timestamp', pymongo.DESCENDING)]))[0]
        return node_db["status"]

    def delete_node(self, mac_add):
        self.node_collection.delete_many({"mac":mac_add})

    def update_node_to_db(self, node):
        node_db = list(self.node_collection.find({"mac":node["MAC"]}).sort([('timestamp', pymongo.DESCENDING)]))[0]
        node_db.pop("_id")
        node_db["status"] = node["status"]
        node_db["timestamp"] = time.time()
        node_db["data"] = node
        # To do: improve merge_dict function to update node
        # node_db["data"] = merge_dict(node_db["data"],node)
        self.node_collection.insert_one(node_db)

    def add_node_to_db(self, node):
        metadata = {}
        metadata["status"] = node["status"]
        metadata["timestamp"] = time.time()
        metadata["data"] = node
        metadata["mac"] = node["MAC"]
        self.node_collection.insert_one(metadata)

    def add_nodes(self, node_data):
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
    
    def remove_node_db(self, node):
        self.node_collection.delete_many({"mac":node["MAC"]})

    def remove_nodes(self, node_data):
        results = {}
        for node_key in node_data:
            node = node_data[node_key]
            self.remove_node_db(node)
            results[node_key] = "Removed"
        return {"result":results}
    
    def get_nodes(self):
        pipeline = [{"$sort":{"timestamp":1}},{"$group": {"_id": "$mac", "status": {"$last": "$status"},"timestamp": {"$last": "$timestamp"}, "data":{"$last": "$data"}}}]
        node_list = list(self.node_collection.aggregate(pipeline))
        return node_list

    ################################ SERVICE FUNCTIONS ################################

    def is_service_exist(self,service_id):
        service = list(self.service_collection.find({"service_id":service_id}))
        return bool(service)

    def get_service_status(self,service_id):
        service_db = list(self.service_collection.find({"service_id":service_id}).sort([('timestamp', pymongo.DESCENDING)]))[0]
        return {"status": {"running": service_db["running"], "replicas": service_db["replicas"]}}
    
    def remove_service_db(self, service):
        self.service_collection.delete_many({"service_id":service["service_id"]})

    def remove_services(self, service_data):
        results = {}
        for app_key in service_data:
            appName = service_data[app_key]
            for s_key in appName:
                service = appName[s_key]
                self.remove_service_db(service)
                results[s_key] = "Removed"
        return {"result":results}
    
    def add_service_to_db(self, service, appName):
        metadata = {}
        metadata["status"] = service["status"]
        metadata["replicas"] = service["replicas"]
        metadata["running"] = service["running"]
        metadata["appName"] = appName
        metadata["timestamp"] = time.time()
        metadata["data"] = service
        metadata["service_id"] = service["service_id"]
        self.service_collection.insert_one(metadata)

    def add_services(self, data):
        results = {}
        for app_key in data:
            appName = data[app_key]
            for s_key in appName:
                service = appName[s_key]
                if self.is_service_exist(service["service_id"]):
                    self.update_service_to_db(service)
                    results[s_key] = "Updated"
                else:
                    self.add_service_to_db(service, app_key)
                    results[s_key] = "Added"
        return {"result":results}
    
    def update_service_to_db(self, service):
        service_db = list(self.service_collection.find({"service_id":service["service_id"]}).sort([('timestamp', pymongo.DESCENDING)]))[0]
        service_db.pop("_id")
        service_db["status"] = service["status"]
        service_db["replicas"] = service["replicas"]
        service_db["running"] = service["running"]
        service_db["timestamp"] = time.time()
        service_db["data"] = service
        # To do: improve merge_dict function to update service
        # service_db["data"] = merge_dict(service_db["data"],service)
        self.service_collection.insert_one(service_db)

    def get_services(self):
        pipeline = [{"$sort":{"timestamp":1}},{"$group": {"_id": "$service_id","replicas": {"$last": "$replicas"}, "running": {"$last": "$running"},"timestamp": {"$last": "$timestamp"}, "data":{"$last": "$data"}}}]
        service_list = list(self.service_collection.aggregate(pipeline))
        return service_list

    ################################ REST FUNCTIONS ################################
        
    def get(self):
        args = request.query_string.decode("utf-8").split("&")
        # get param from args here
        return jsonify({'status': args})


    def post(self):
        if request.is_json:
            args = request.get_json(force=True)
            response = {}
            if "command" in args:
                command = args["command"]
                if command == "ADD NODE":
                    response = self.add_nodes(args["data"])
                elif command == "REMOVE ALL NODE":
                    self.node_collection.drop()
                    response = {"result":"All nodes removed"}
                elif command == "REMOVE NODE":
                    response =self.remove_nodes(args["data"])
                elif command == "ADD SERVICE":
                    response =self.add_services(args["data"])
                elif command == "REMOVE ALL SERVICE":
                    self.service_collection.drop()
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

    def put(self):
        if request.is_json:
            args = request.get_json(force=True)
        # get param from args here
        return jsonify({'status': True})

    def delete(self):
        if request.is_json:
            args = request.get_json(force=True)
        # get param from args here
        return jsonify({'status': args})

class RoheOrchestrationAgent(RoheObject):
    def __init__(self, configuration, sync=True, log_lev=2):
        super().__init__(logging_level=log_lev)
        self.conf = configuration
        self.db_config = self.conf["database"]
        self.mongo_client = pymongo.MongoClient(self.db_config["url"])
        self.db = self.mongo_client[self.db_config["db_name"]]
        self.node_collection = self.db[self.db_config["node_collection"]]
        self.service_collection = self.db[self.db_config["service_collection"]]
        self.nodes = {}
        self.services = {}
        self.orchestrateConfig = configuration["orchestrateConfig"]
        self.service_queue = Service_Queue(configuration["service_queue"])
        if sync:
            self.sync_from_db()
        self.orches_flag = True
        self.update_flag = False
        # self.show_services()
        # self.show_nodes()
        

    def start(self):
        # Periodically check service queue and allocate service 
        self.orches_flag = True
        self.orchestrate()

    def allocate_service(self):
        pass
    
    def sync_from_db(self):
        self.sync_node_from_db()
        self.sync_service_from_db()
        


    

    def orchestrate(self):
        if self.orches_flag:
            self.log("Agent Start Orchestrating")
            self.sync_from_db()
            self.log("Sync completed")
            scoringOrchestrate(self.nodes, self.services, self.service_queue, self.orchestrateConfig)
            self.show_services()
            self.sync_node_to_db()
            self.sync_service_to_db()
            self.log("Sync nodes and services to Database completed")
            self.timer = Timer(self.conf["timer"], self.orchestrate)
            self.timer.start()

    
        

    def stop(self):
        self.orches_flag = False

    def sync_node_from_db(self, node_mac=None, replace=True):
        # Sync specific node
        if node_mac != None:
            # query node from db
            node_res = list(self.node_collection.find({"mac":node_mac}).sort([('timestamp', pymongo.DESCENDING)]))
            if len(node_res) > 0:
                node_db = node_res[0]
                #if replace -> completely replace local node by node from database
                if replace:
                    self.nodes[node_mac] = node_db["data"]
                #if not replace -> update local node using node from database: To do
                else:
                    pass
        # Sync all node
        else:
            # query the last updated nodes
            pipeline = [{"$sort":{"timestamp":1}},{"$group": {"_id": "$mac", "timestamp": {"$last": "$timestamp"}, "data":{"$last": "$data"}}}]
            node_list = list(self.node_collection.aggregate(pipeline))
            self.nodes = {}
            for node in node_list:
                #if replace -> completely replace local nodes by nodes from database
                if replace:
                    self.nodes[node["_id"]] = Node(node["data"])
                #if not replace -> update local nodes using nodes from database: To do
                else:
                    pass
        self.log("Agent Sync nodes from Database complete")

    def sync_service_from_db(self, service_id=None, replace=True):
        # Sync specific service
        if service_id != None:
            # query service from db
            service_res = list(self.service_collection.find({"service_id":service_id}).sort([('timestamp', pymongo.DESCENDING)]))
            if len(service_res) > 0:
                service_db = service_res[0]
                #if replace -> completely replace local service by service from database
                if replace:
                    self.services[service_id] = Service(service_db)
                else: 
                    pass
                # if number of service instance running lower than its required replicas, put it to service queue
        else:
            pipeline = [{"$sort":{"timestamp":1}},
                {"$group": {"_id": "$service_id","replicas": {"$last": "$replicas"}, "running": {"$last": "$running"},"timestamp": {"$last": "$timestamp"}, "data":{"$last": "$data"}}}]
            service_list = list(self.service_collection.aggregate(pipeline))
            self.services = {}
            for service in service_list:
                #if replace -> completely replace local services by services from database
                if replace:
                    self.services[service["_id"]] = Service(service["data"])
                else:
                    pass
        self.log("Agent Sync services from Database complete")
    
    def sync_node_to_db(self, node_mac=None):
        if node_mac != None:
            node_db = list(self.node_collection.find({"mac":node_mac}).sort([('timestamp', pymongo.DESCENDING)]))[0]
            node_db["data"] = self.nodes[node_mac].config
            node_db.pop("_id")
            node_db["timestamp"] = time.time()
            self.node_collection.insert_one(node_db)
        else:
            for key in self.nodes:
                self.sync_node_to_db(key)
        

    def sync_service_to_db(self, service_id=None):
        if service_id != None:
            service_db = list(self.service_collection.find({"service_id":service_id}).sort([('timestamp', pymongo.DESCENDING)]))[0]
            service_db["data"] = self.services[service_id].config
            service_db["replicas"] = self.services[service_id].replicas
            service_db["running"] = self.services[service_id].running
            service_db.pop("_id")
            service_db["timestamp"] = time.time()
            self.service_collection.insert_one(service_db)
        else:
            for key in self.services:
                self.log(key)
                self.sync_service_to_db(key)

    def show_nodes(self):
        self.log("############ NODES LIST ############")
        for node_key in self.nodes:
            self.log("{} : {}".format(self.nodes[node_key], node_key))
        self.log("Nodes Size: {}".format(len(self.nodes)))

    def show_services(self):
        self.log("############ SERVICES LIST ############")
        for service_key in self.services:
            self.log(self.services[service_key])
        self.log("Services Size: ".format(len(self.services)))

    
    