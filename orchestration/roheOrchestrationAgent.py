import pymongo
from threading import Thread, Timer
import json, time
from resource_management.resource import Node, Service, Service_Queue
from algorithm.selector import ex_orchestrate

class Rohe_Orchestration_Agent(object):
    def __init__(self, configuration, sync=True):
        self.conf = configuration
        self.db_config = self.conf["database"]
        self.mongo_client = pymongo.MongoClient(self.db_config["url"])
        self.db = self.mongo_client[self.db_config["db_name"]]
        self.node_collection = self.db[self.db_config["node_collection"]]
        self.service_collection = self.db[self.db_config["service_collection"]]
        self.nodes = {}
        self.update_flag = False
        self.services = {}
        self.service_queue = Service_Queue(configuration["service_queue"])
        if sync:
            self.sync_from_db()
        self.orches_flag = True
        
        # self.show_services()
        # self.show_nodes()
        


    def allocate_service(self):
        pass
    
    def sync_from_db(self):
        self.sync_node_from_db()
        self.sync_service_from_db()
        # queue_list = []
        # for key in self.services:
        #     if self.services[key]["status"] == "queueing":
        #         queue_list.append(key)

    

    def orchestrate(self):
        if self.orches_flag:
            print("Orchestrating")
            self.sync_from_db()
            ex_orchestrate(self.nodes, self.services, self.service_queue)
            # self.show_services()
            if self.update_flag:
                self.sync_node_to_db()
                self.sync_service_to_db()
                self.update_flag = False
                print("Updated")
            self.timer = Timer(self.conf["timer"], self.orchestrate)
            self.timer.start()

    def start(self):
        # Periodically check service queue and allocate service 
        self.orches_flag = True
        self.orchestrate()
        

    def stop(self):
        self.orches_flag = False

    def sync_node_from_db(self, node_mac=None):
        print("sync node from db")
        if node_mac != None:
            node_res = list(self.node_collection.find({"mac":node_mac}).sort([('timestamp', pymongo.DESCENDING)]))
            if len(node_res) > 0:
                node_db = node_res[0]
                self.nodes[node_mac] = node_db["data"]
        else:
            pipeline = [{"$sort":{"timestamp":1}},
                {"$group": {"_id": "$mac", "timestamp": {"$last": "$timestamp"}, "data":{"$last": "$data"}}}]
            node_list = list(self.node_collection.aggregate(pipeline))
            self.nodes = {}
            for node in node_list:
                self.nodes[node["_id"]] = Node(node["data"])

    def sync_service_from_db(self, service_id=None):
        print("sync service from db")
        if service_id != None:
            service_res = list(self.service_collection.find({"service_id":service_id}).sort([('timestamp', pymongo.DESCENDING)]))
            if len(service_res) > 0:
                service_db = service_res[0]
                if service_db["status"] == "queueing":
                    self.service_queue.put(Service(service_db["data"]))
                    self.update_flag = True
        else:
            pipeline = [{"$sort":{"timestamp":1}},
                {"$group": {"_id": "$service_id", "status": {"$last": "$status"},"timestamp": {"$last": "$timestamp"}, "data":{"$last": "$data"}}}]
            service_list = list(self.service_collection.aggregate(pipeline))
            self.services = {}
            for service in service_list:
                if service["status"] == "running":
                    self.services[service["_id"]] = Service(service["data"])
                if service["status"] == "queueing":
                    self.service_queue.put(Service(service["data"]))
                    self.update_flag = True
    
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
            service_db["status"] = self.services[service_id].status
            service_db.pop("_id")
            service_db["timestamp"] = time.time()
            self.service_collection.insert_one(service_db)
        else:
            for key in self.services:
                print(key)
                self.sync_service_to_db(key)

    def show_nodes(self):
        for node_key in self.nodes:
            print(self.nodes[node_key],":", node_key)
        print("Nodes Size: ",len(self.nodes))

    def show_services(self):
        for service_key in self.services:
            print(self.services[service_key])
        print("Services Size: ",len(self.services))



############################################## TESTING ##############################################
import argparse
import qoa4ml.utils as utils 

if __name__ == '__main__': 
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Orchestration Algorithm")

    # TO DO: read from database
    parser.add_argument('--conf', help='Orchestrator configuration file', default="../configurations/orchestration/orchestrationConfig.json")
    args = parser.parse_args()
    config = utils.load_config(args.conf)
    print(config)
    agent = Rohe_Orchestration_Agent(config)
    
    # agent.show_services()
    agent.orchestrate()
    # agent.show_services()
    # agent.show_nodes()
    
    