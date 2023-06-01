from qoa4ml.collector.amqp_collector import Amqp_Collector
import pymongo
from threading import Thread, Timer
import json

class Rohe_Agent(object):
    def __init__(self, configuration, mg_db=False):
        self.conf = configuration
        colletor_conf = self.conf["collector"]
        self.collector = Amqp_Collector(colletor_conf['amqp_collector']['conf'], host_object=self)
        db_conf = self.conf["database"]
        self.mongo_client = pymongo.MongoClient(db_conf["url"])
        self.db = self.mongo_client[db_conf["db_name"]]
        self.metric_collection = self.db[db_conf["metric_collection"]]

        self.insert_db = mg_db
    
    def reset_db(self):
        self.metric_collection.drop()

    def start_consuming(self):
        print("Start Consuming")
        self.collector.start()

    def start(self):
        sub_thread = Thread(target=self.start_consuming)
        sub_thread.start()
        print("start consumming message")



    def message_processing(self, ch, method, props, body):
        mess = json.loads(str(body.decode("utf-8")))
        print("Receive QoA Report: \n", mess)
        if self.insert_db:
            insert_id = self.metric_collection.insert_one(mess)
            print("Insert to database", insert_id)

    def stop(self):
        # self.collector.stop()
        self.insert_db = False
    def restart(self):
        # self.collector.stop()
        self.insert_db = True
    