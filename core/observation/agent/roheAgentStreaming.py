from qoa4ml.collector.amqp_collector import Amqp_Collector
from qoa4ml import qoaUtils
import pymongo, argparse
from threading import Thread, Timer
import json, sys, time, os
import uuid, pymongo
import traceback
import pandas as pd
main_path = config_file = qoaUtils.get_parent_dir(__file__,3)
sys.path.append(main_path)
DEFAULT_CONFIG_PATH="/configurations/observationConfig.yaml"
DEFAULT_DATA_PATH = "/agent/data/"


# Append syspath for dynamic import modules
lib_path = qoaUtils.get_parent_dir(__file__,4)
sys.path.append(lib_path)
from lib.modules.roheObject import RoheObject
import lib.modules.observation.streamAnalysis.functions as func
import lib.modules.observation.streamAnalysis.parser as pars
from lib.modules.observation.streamAnalysis.window import EventBuffer, TimeBuffer
import lib.roheUtils as rohe_utils

def get_app(collection, app_name):
    # Create sorted pipepline to query application list
    pipeline = [{"$sort":{"timestamp":1}},{"$group": {"_id": "$appID", "app_name": {"$last": "$app_name"},"timestamp": {"$last": "$timestamp"},"db": {"$last": "$db"},"client_count": {"$last": "$client_count"}, "agent_config":{"$last": "$agent_config"}}}]
    app_list = list(collection.aggregate(pipeline))
    for app in app_list:
        # return app with its configuration
        if app["app_name"] == app_name:
            return app
    return None


class RoheObservationAgent(RoheObject):
    def __init__(self, configuration, mg_db=False, log_lev=2):
        super().__init__(logging_level=log_lev)
        self.conf = configuration
        self.app_name = configuration["app_name"]
        self.temp_path = DEFAULT_DATA_PATH+self.app_name
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
        self.agent_config = self.conf["stream_config"]
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

        # Get parser from configuration
        parser_name =  self.proc_config["parser"]["name"]
        if parser_name == "dummy":
            print(mess)
        else:
            parser = getattr(pars, self.proc_config["parser"]["name"])
            # Parse data to DataFrame
            df_mess = parser(mess, self.proc_config["parser"])

            # Add metric report as dataframe to buffer - processing window
            self.buffer.append(df_mess)
            self.log(len(self.buffer.get()),2)

            if self.insert_db:
                # Insert raw data to databased if insert_db is set to True
                insert_id = self.metric_collection.insert_one(mess)
                self.log("Insert to database {}".format(insert_id), 2)
            
            # Check event trigger
            if self.trigger["type"] == 2:
                self.eventTrigger()

    # Function for processing window
    def windowProcessing(self):

        self.log("Start Window Processing")
        # Get data from buffer processing window
        data = self.buffer.get(dataframe=True)

        self.log(data, 1) # For Debugging

        # Load dynamic processing function from function configuration
        function_name = self.proc_config["function"]
        if function_name == "dummy":
            pass
        else:
            procFunc = getattr(func, self.proc_config["function"])
            feature_list = self.proc_config["parser"]["feature"]

            # data, feature_list = parser(self.buffer, self.proc_config["parser"])
            # 
            for feature in feature_list:
                result_df, model = procFunc(data, feature)
                rohe_utils.make_folder(self.temp_path)
                file_path = self.temp_path+"/"+str(feature)+".csv"
                rohe_utils.df_to_csv(file_path, result_df)
                # self.log("\n"+str(result_df))

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
    
if __name__ == '__main__': 
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Rohe Observation Agent")
    parser.add_argument('--conf', help='configuration file', default=None)

    # Parse the parameters
    args = parser.parse_args()
    config_file = args.conf

    # load configuration file
    if not config_file:
        config_file = main_path+DEFAULT_CONFIG_PATH
        print(config_file)
    try:
        
        configuration = rohe_utils.load_config(config_file)
        db_config = configuration["database"]
        mongo_client = pymongo.MongoClient(db_config["url"])
        db = mongo_client[db_config["db_name"]]
        collection = db[db_config["collection"]]

        app_name = os.environ.get('APP_NAME')
        if not app_name:
            app_name = "test"
        agent_config = get_app(collection, app_name)['agent_config']
        agent_config["app_name"] = app_name
        print(agent_config)
        agent = RoheObservationAgent(agent_config)
        agent.start()
    except:
        traceback.print_exc()