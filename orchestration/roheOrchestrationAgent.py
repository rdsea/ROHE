import pymongo
from threading import Thread, Timer
import json

class Rohe_Orchestration_Agent(object):
    def __init__(self, configuration):
        self.conf = configuration
        self.db_config = self.conf["database"]
        self.mongo_client = pymongo.MongoClient(self.db_config["url"])
        self.db = self.mongo_client[self.db_config["db_name"]]
        self.node_collection = self.db[self.db_config["node_collection"]]
        self.service_collection = self.db[self.db_config["service_collection"]]
    
    