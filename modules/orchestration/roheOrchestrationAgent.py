import pymongo
from threading import Thread, Timer
import time
import qoa4ml.utils as utils
import pymongo, time
import pandas as pd
import argparse, random, sys
lib_path = utils.get_parent_dir(__file__,2)
sys.path.append(lib_path)
from lib.roheObject import RoheObject



from modules.orchestration.resourceManagement.resource import Node, Service, Service_Queue
from modules.orchestration.algorithm.priorityOrchestrate import orchestrate as prioriryOrchestrate

# def get_dict_at(dict, i):
#     keys = list(dict.keys())
#     return dict[keys[i]], keys[i]

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
            prioriryOrchestrate(self.nodes, self.services, self.service_queue, self.orchestrateConfig)
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



############################################## TESTING ##############################################
import argparse

if __name__ == '__main__': 
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Orchestration Algorithm")

    # TO DO: read from database
    parser.add_argument('--conf', help='Orchestrator configuration file', default="../configurations/orchestration/orchestrationConfig.json")
    args = parser.parse_args()
    config = utils.load_config(args.conf)
    print(config)
    agent = RoheOrchestrationAgent(config)
    
    # agent.show_services()
    agent.orchestrate()
    # agent.show_services()
    # agent.show_nodes()
    
    