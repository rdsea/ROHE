import qoa4ml.utils as utils
import uuid, pymongo, time
import pandas as pd
import argparse, random
import traceback,sys,pathlib
sys.path.append("../")
from roheOrchestrationAgent import Rohe_Orchestration_Agent
from utils.common import merge_dict


from flask import Flask, jsonify, request
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)

rohe_agent = None

def get_dict_at(dict, i):
    keys = list(dict.keys())
    return dict[keys[i]], keys[i]



class Rohe_Orchestration_Service(Resource):
    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.conf = kwargs
        self.agent = self.conf["agent"]
        self.db_config = self.conf["database"]
        self.mongo_client = pymongo.MongoClient(self.db_config["url"])
        self.db = self.mongo_client[self.db_config["db_name"]]
        self.node_collection = self.db[self.db_config["node_collection"]]
        self.service_collection = self.db[self.db_config["service_collection"]]

    def is_node_exist(self,mac_add):
        node = list(self.node_collection.find({"mac":mac_add}))
        return bool(node)
    
    def is_service_exist(self,service_id):
        service = list(self.service_collection.find({"service_id":service_id}))
        return bool(service)

    def get_node_status(self,mac_add):
        node_db = list(self.node_collection.find({"mac":mac_add}).sort([('timestamp', pymongo.DESCENDING)]))[0]
        return node_db["status"]

    def get_service_status(self,service_id):
        service_db = list(self.service_collection.find({"service_id":service_id}).sort([('timestamp', pymongo.DESCENDING)]))[0]
        return service_db["status"]
    
    def delete_node(self, mac_add):
        self.node_collection.delete_many({"mac":mac_add})
    
    def delete_service(self, service_id):
        self.service_collection.delete_many({"service_id":service_id})

    def update_node_db(self, node):
        node_db = list(self.node_collection.find({"mac":node["MAC"]}).sort([('timestamp', pymongo.DESCENDING)]))[0]
        node_db.pop("_id")
        node_db["status"] = node["status"]
        node_db["timestamp"] = time.time()
        node_db["data"] = merge_dict(node_db["data"],node)
        self.node_collection.insert_one(node_db)

    def add_node_db(self, node):
        metadata = {}
        metadata["status"] = node["status"]
        metadata["timestamp"] = time.time()
        metadata["data"] = node
        metadata["mac"] = node["MAC"]
        self.node_collection.insert_one(metadata)

    def add_nodes(self, node_data):
        for node_key in node_data:
            node = node_data[node_key]
            if self.is_node_exist(node["MAC"]):
                self.update_node_db(node)
                print("node updated")
            else:
                self.add_node_db(node)
                print("node added")
        return {"result":"Node Added"}
    
    def remove_node_db(self, node):
        self.node_collection.delete_many({"mac":node["MAC"]})

    def remove_nodes(self, node_data):
        for node_key in node_data:
            node = node_data[node_key]
            self.remove_node_db(node)
        return {"result":"Nodes removed"}
    
    def remove_service_db(self, service):
        self.service_collection.delete_many({"service_id":service["service_id"]})

    def remove_services(self, service_data):
        for app_key in service_data:
            application = service_data[app_key]
            for s_key in application:
                service = application[s_key]
                self.remove_service_db(service)
        return {"result":"Services removed"}


        
    def get(self):
        args = request.query_string.decode("utf-8").split("&")
        # get param from args here
        return jsonify({'status': args})
    
    def update_node_db(self, service):
        service_db = list(self.service_collection.find({"service_id":service["service_id"]}).sort([('timestamp', pymongo.DESCENDING)]))[0]
        service_db.pop("_id")
        service_db["status"] = service["status"]
        service_db["timestamp"] = time.time()
        service_db["data"] = merge_dict(service_db["data"],service)
        self.service_collection.insert_one(service_db)
    
    def add_service_db(self, service, application):
        metadata = {}
        metadata["status"] = service["status"]
        metadata["application"] = application
        metadata["timestamp"] = time.time()
        metadata["data"] = service
        metadata["service_id"] = service["service_id"]
        self.service_collection.insert_one(metadata)

    def add_services(self, data):
        for app_key in data:
            application = data[app_key]
            for s_key in application:
                service = application[s_key]
                if self.is_service_exist(service["service_id"]):
                    self.update_node_db(service)
                    print("service updated")
                else:
                    self.add_service_db(service, app_key)
                    print("service added")
        return {"result":"Services Added"}


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


if __name__ == '__main__': 
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Rohe Orchestration Service")
    parser.add_argument('--conf', help='configuration file', default=None)
    parser.add_argument('--path', help='default config path', default="/configurations/orchestration/orchestrationConfig.json")
    args = parser.parse_args()
    config_file = args.conf
    config_path = args.path
    if not config_file:
        config_file = utils.get_parent_dir(__file__,1)+config_path
        print(config_file)
    configuration = utils.load_config(config_file)
    rohe_agent = Rohe_Orchestration_Agent(configuration)
    configuration["agent"] = rohe_agent

    api.add_resource(Rohe_Orchestration_Service, '/management',resource_class_kwargs=configuration)
    app.run(debug=True, port=5002)