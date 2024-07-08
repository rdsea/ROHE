import argparse
import json
import os
from threading import Thread, Timer

import pymongo
from qoa4ml.collector.amqp_collector import Amqp_Collector

from ....common import rohe_utils
from ....common.logger import logger
from ....common.window import EventBuffer, TimeBuffer
from ....variable import ROHE_PATH

# set default global variable for loading configuration/functions and saving processed data
DEFAULT_CONFIG_PATH = "configurations/observationConfigLocal.yaml"
DEFAULT_DATA_PATH = "/agent/data/"
DEFAULT_MODULE_PATH = "/agent/userModule/"


def get_app(collection, application_name):
    # get application data from databased
    # Create sorted pipeline to query application list
    pipeline = [
        {"$sort": {"timestamp": 1}},
        {
            "$group": {
                "_id": "$appID",
                "application_name": {"$last": "$application_name"},
                "user_id": {"$last": "$user_id"},
                "run_id": {"$last": "$run_id"},
                "timestamp": {"$last": "$timestamp"},
                "db": {"$last": "$db"},
                "client_count": {"$last": "$client_count"},
                "agent_config": {"$last": "$agent_config"},
            }
        },
    ]
    app_list = list(collection.aggregate(pipeline))
    for app in app_list:
        # return app with its configuration
        if app["application_name"] == application_name:
            return app
    return None


class RoheObservationAgent:
    def __init__(self, configuration, mg_db=False):
        self.conf = configuration
        self.application_name = configuration["application_name"]
        self.temp_path = DEFAULT_DATA_PATH + self.application_name
        # Init Metric collector
        colletor_conf = self.conf["collector"]
        self.collector = Amqp_Collector(
            colletor_conf["amqp_collector"]["conf"], host_object=self
        )
        logger.debug(self.conf["collector"])  # for debugging

        # Init Database connection
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
        self.module_path = DEFAULT_MODULE_PATH + "{}.py".format(
            self.proc_config["module"]
        )
        self.proc_module = rohe_utils.load_module(
            self.module_path, self.proc_config["module"]
        )
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
        logger.info("Start Consuming")
        self.collector.start_collecting()

    # Public start function
    def start(self):
        # Switch to running status
        self.status = 1
        # Start consumming metric reports from messaging broker
        sub_thread = Thread(target=self.start_consuming)
        sub_thread.start()
        logger.info("Start consumming message")

        # Start trigger for window processing
        if self.trigger["type"] == 1:
            # Time window processing - Trigger after certain interval: self.trigger["value"]
            self.timer = Timer(self.trigger["value"], self.time_trigger)
            self.timer.start()
        elif self.trigger["type"] == 2:
            # Event window processing - Reset trigger event count to 0
            self.trigger["count"] = 0

    def message_processing(self, ch, method, props, body):
        # Consume message from Broker
        mess = json.loads(str(body.decode("utf-8")))

        # Get parser from configuration
        parser_name = self.proc_config["parser"]["name"]
        if parser_name == "dummy":
            logger.info(mess)
        else:
            # get parser by its name from userModule
            parser = getattr(self.proc_module, self.proc_config["parser"]["name"])
            # Parse data to DataFrame
            df_mess = parser(mess, self.proc_config["parser"])
            file_path = self.temp_path + "/raw_message.csv"
            rohe_utils.df_to_csv(file_path, df_mess)

            # Add metric report as dataframe to buffer - processing window
            self.buffer.append(df_mess)
            logger.info(len(self.buffer.get()))

            if self.insert_db:
                # Insert raw data to databased if insert_db is set to True
                insert_id = self.metric_collection.insert_one(mess)
                logger.info(f"Insert to database {insert_id}")

            # Check event trigger
            if self.trigger["type"] == 2:
                self.event_trigger()

    # Function for processing window
    def window_processing(self):
        logger.info("Start Window Processing")
        # Get data from buffer processing window
        data = self.buffer.get(dataframe=True)

        # self.log(data, 1) # For Debugging

        # Load dynamic processing function from function configuration
        function_name = self.proc_config["function"]
        if function_name == "dummy":
            pass
        else:
            proc_func = getattr(self.proc_module, self.proc_config["function"])
            feature_list = self.proc_config["parser"]["feature"]

            # data, feature_list = parser(self.buffer, self.proc_config["parser"])
            #
            for feature in feature_list:
                result_df, model = proc_func(data, feature)
                if result_df is not None:
                    rohe_utils.make_folder(self.temp_path)
                    file_path = self.temp_path + "/" + str(feature) + ".csv"
                    rohe_utils.df_to_csv(file_path, result_df)

                    errors = result_df.loc[result_df["anomaly"] == -1]
                    if len(errors) > 0:
                        print(errors)
                        err_file_path = (
                            self.temp_path + "/error_" + str(feature) + ".csv"
                        )
                        rohe_utils.df_to_csv(err_file_path, errors)
                    # self.log("\n"+str(result_df))

    def event_trigger(self):
        # Check trigger and reset counter
        self.trigger["count"] += 1
        if self.trigger["count"] == self.trigger["value"]:
            if self.status == 1:
                self.window_processing()
            self.trigger["count"] = 0

    def time_trigger(self):
        try:
            # if status is running, call windowProcessing
            if self.status == 1:
                self.window_processing()
            # Start timer to trigger window processing after certain interval - self.trigger["value"]
            self.timer = Timer(self.trigger["value"], self.time_trigger)
            self.timer.start()
        except Exception as e:
            logger.exception(
                f"Error {type(e)} while estimating contribution",
            )

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


if __name__ == "__main__":
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for Rohe Observation Agent")
    parser.add_argument("--conf", help="configuration file", default=None)

    # Parse the parameters
    args = parser.parse_args()
    config_file = args.conf

    # load configuration file
    if not config_file:
        config_file = ROHE_PATH + DEFAULT_CONFIG_PATH
        print(config_file)

    try:
        # read the configuration
        configuration = rohe_utils.load_config(config_file)
        db_config = configuration["database"]
        # connect to database
        mongo_client = pymongo.MongoClient(db_config["url"])
        db = mongo_client[db_config["db_name"]]
        collection = db[db_config["collection"]]

        # get application_name from Container Environment
        application_name = os.environ.get("APP_NAME")
        if not application_name:
            application_name = "test"
        # get agent configuration from database
        agent_config = get_app(collection, application_name)["agent_config"]
        agent_config["application_name"] = application_name
        print(agent_config)
        agent = RoheObservationAgent(agent_config)
        agent.start()
    except Exception:
        logger.exception("Exception in rohe_agent_streaming")
