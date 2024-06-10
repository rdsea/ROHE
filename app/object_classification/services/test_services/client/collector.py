import argparse
import json
import os
import sys
import time
from threading import Thread

from dotenv import load_dotenv
from qoa4ml import qoaUtils as utils
from qoa4ml.collector.amqp_collector import Amqp_Collector

load_dotenv()

main_path = os.getenv("ROHE_PATH")
print(f"This is main path: {main_path}")
sys.path.append(main_path)
from userModule.common.parser import OCParser


class Collector(object):
    def __init__(self, config) -> None:
        self.config = config
        self.collector = Amqp_Collector(self.config["collector"], self)
        self.subthread = Thread(target=self.collector.start)

    def start(self):
        self.subthread.start()

    def message_processing(self, ch, method, props, body):
        mess = json.loads(str(body.decode("utf-8")))
        result = OCParser(mess, self.config["parser_config"])
        # temp = result
        # print(result)

    def stop(self):
        self.collector.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Node Monitoring")
    parser.add_argument("--conf", help="configuration file", default="./collector.json")
    parser.add_argument("--t", help="profiling time", default=300)
    args = parser.parse_args()

    profiling_time = args.t
    config_file = args.conf

    # Load collector configuration
    collector_conf = utils.load_config(config_file)

    # Init collector
    collector = Collector(collector_conf)

    # Name of the model
    folder_list = [
        "vgg",
        "vgg_0",
        "vgg_2_7",
        "vgg_2_12",
        "vgg_3_6",
        "vgg_6",
        "vgg_6_7",
        "vgg_7",
        "vgg_7_6",
    ]

    # Start collector
    collector.start()

    count = 0

    # Create folder to save raw data
    profile_folder = "./raw_data/" + folder_list[count]
    if not os.path.exists(profile_folder):
        os.makedirs(profile_folder)

    # Get file path for saving data
    collector_conf["parser_config"]["client"] = profile_folder + "/client.csv"
    collector_conf["parser_config"]["mlProvider"] = profile_folder + "/provider.csv"

    # Loop to save data from profiling different model
    while count < len(folder_list):
        print(collector_conf["parser_config"]["client"])
        print(collector_conf["parser_config"]["mlProvider"])
        profile_folder = "./raw_data/" + folder_list[count]
        if not os.path.exists(profile_folder):
            os.makedirs(profile_folder)
            # Creating new folder
            print(collector_conf["parser_config"]["client"])
            print(collector_conf["parser_config"]["mlProvider"])

        # Get file path for saving data
        collector_conf["parser_config"]["client"] = profile_folder + "/client.csv"
        collector_conf["parser_config"]["mlProvider"] = profile_folder + "/provider.csv"

        time.sleep(profiling_time)
        count += 1

    while True:
        print("loop end - Waiting")
        time.sleep(100)
