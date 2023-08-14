from qoa4ml.collector.amqp_collector import Amqp_Collector
from qoa4ml import utils
import pymongo
from threading import Thread, Timer
import json, sys, time
import uuid, pymongo
import pandas as pd

# Append syspath for dynamic import modules
lib_path = utils.get_parent_dir(__file__,3)
sys.path.append(lib_path)
from modules.roheObject import RoheObject
import modules.observation.streamAnalysis.functions as func
import modules.observation.streamAnalysis.parser as pars
from modules.observation.streamAnalysis.window import EventBuffer, TimeBuffer



class RoheObservationAgent(RoheObject):
    def __init__(self, configuration, mg_db=True, log_lev=2):
        super().__init__(logging_level=log_lev)
        self.conf = configuration
        # Init Metric collector 
        colletor_conf = self.conf["collector"]
        self.collector = Amqp_Collector(colletor_conf['amqp_collector']['conf'], host_object=self)
        self.log(self.conf["collector"],1) # for debugging

        #Init Database connection 
        db_conf = self.conf["database"]
        self.mongo_client = pymongo.MongoClient(db_conf["url"])
        self.db = self.mongo_client[db_conf["db_name"]]
        self.metric_collection = self.db[db_conf["metric_collection"]]
        
        """
        Agent Status
        0 - Ready
        1 - Running
        2 - Stop
        """
        self.status = 0
        

        # Inint processing configuration e.g., processing window (time/event), processing function, data parser
        self.agent_config = utils.load_config(lib_path+"/configurations/observation/agent/streamConfig.json")
        self.buff_config = self.agent_config["window"]
        self.proc_config = self.agent_config["processing"]
        """
        Processing Type: 
        1 - Event
        2 - Time
        """
        if self.buff_config["size"]["type"] == 1:
            # Init Time buffer
            self.buffer = TimeBuffer(self.buff_config["size"]["value"])
        elif self.buff_config["size"]["type"] == 2:
            # Init Event buffer
            self.buffer = EventBuffer(self.buff_config["size"]["value"])
        self.trigger = self.buff_config["interval"]
        
        # Save to database or not: True/False
        self.insert_db = mg_db
    
    # Drop all metric collection
    def reset_db(self):
        self.metric_collection.drop()

    # Start consumming metric reports
    def start_consuming(self):
        self.log("Start Consuming",2)
        self.collector.start()

    # Public start function
    def start(self):
        # Switch to running status
        self.status = 1
        # Start consumming metric reports from messaging broker
        sub_thread = Thread(target=self.start_consuming)
        sub_thread.start()
        self.log("Start consumming message",2)

        # Start trigger for window processing
        if self.trigger["type"] == 1:
            # Time window processing - Trigger after certain interval: self.trigger["value"]
            self.timer = Timer(self.trigger["value"], self.timeTrigger)
            self.timer.start()
        elif self.trigger["type"] == 2:
            # Event window processing - Reset trigger event count to 0
            self.trigger["count"] = 0




    def message_processing(self, ch, method, props, body):
        mess = json.loads(str(body.decode("utf-8")))

        # Add metric report to buffer - processing window
        self.buffer.append(mess)
        self.log(len(self.buffer.get()),2)

        if self.insert_db:
            # Insert to databased if insert_db is set to True
            insert_id = self.metric_collection.insert_one(mess)
            self.log("Insert to database {}".format(insert_id), 2)
        
        # Check event trigger
        if self.trigger["type"] == 2:
            self.eventTrigger()

    # Function for processing window
    def windowProcessing(self):
        self.log("Start Window Processing")
        # Get parser from configuration
        parser = getattr(pars, self.proc_config["parser"]["name"])
        data, feature_list = parser(self.buffer, self.proc_config["parser"])
        procFunc = getattr(func, self.proc_config["function"])
        for feature in feature_list:
            result_df, model = procFunc(data, feature)
            self.log("\n"+str(result_df))

    def eventTrigger(self):
        # Check trigger and reset counter
        self.trigger["count"] += 1
        if self.trigger["count"] == self.trigger["value"]:
            if self.status == 1:
                self.windowProcessing()
            self.trigger["count"] = 0

    def timeTrigger(self):
        try:
            # if status is running, call windowProcessing
            if self.status == 1:
                self.windowProcessing()
            # Start timer to trigger window processing after certain interval - self.trigger["value"]
            self.timer = Timer(self.trigger["value"], self.timeTrigger)
            self.timer.start()
        except Exception as e:
            self.log("Error {} while estimating contribution: {}".format(type(e),e.__traceback__), 4)

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
    