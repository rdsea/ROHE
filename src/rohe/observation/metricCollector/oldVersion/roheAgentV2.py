import json
from threading import Thread

import pymongo
from qoa4ml.collector.amqp_collector import Amqp_Collector


def get_dict_at(dict, i):
    keys = list(dict.keys())
    return dict[keys[i]], keys[i]


class RoheObservationAgent:
    def __init__(self, configuration, mg_db=True):
        self.conf = configuration
        colletor_conf = self.conf["collector"]
        self.collector = Amqp_Collector(
            colletor_conf["amqp_collector"]["conf"], host_object=self
        )
        db_conf = self.conf["database"]
        self.mongo_client = pymongo.MongoClient(db_conf["url"])
        self.db = self.mongo_client[db_conf["db_name"]]
        self.metric_collection = self.db[db_conf["metric_collection"]]
        print(self.conf["collector"])
        self.status = 0
        """
        Agent Status
        0 - Ready
        1 - Running
        2 - Stop
        """
        self.insert_db = mg_db

    def reset_db(self):
        self.metric_collection.drop()

    def start_consuming(self):
        print("Start Consuming")
        self.collector.start()

    def start(self):
        sub_thread = Thread(target=self.start_consuming)
        sub_thread.start()
        self.insert_db = True
        self.status = 1
        print("start consumming message")

    def message_processing(self, ch, method, props, body):
        mess = json.loads(str(body.decode("utf-8")))

        if self.insert_db:
            print("Receive QoA Report: \n", mess)
            insert_id = self.metric_collection.insert_one(mess)
            print("Insert to database", insert_id)

    def stop(self):
        # self.collector.stop()
        self.insert_db = False
        self.status = 2
        # Todo:
        # Stop consumming message

    def restart(self):
        # self.collector.stop()
        self.insert_db = True
        self.status = 1
