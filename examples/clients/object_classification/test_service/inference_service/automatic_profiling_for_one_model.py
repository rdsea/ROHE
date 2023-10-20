
import os, sys
import requests
import json
import time
import argparse
import threading

import qoa4ml.qoaUtils as qoa_utils
from datetime import datetime

import h5py
import numpy as np

# from client import InferenceServiceClient
from clientV2 import InferenceServiceClientV2


# set the ROHE to be in the system path
lib_level = os.environ.get('LIB_LEVEL')
if not lib_level:
    lib_level = 5
main_path = config_file = qoa_utils.get_parent_dir(__file__,lib_level)
sys.path.append(main_path)


from core.profiling.collector import Collector
import lib.roheUtils as roheUtils

# global qoaclient 
# qoaclient = None  

class CollectorJob:
    def __init__(self, interval: int, config: dict,
                 server_address: str = None, chosen_model_id: str = "vgg",
                 save_root_path: str = None, save_root_folder: str = None):
        self.interval: int = int(interval)
        self.config: dict = config


        self.server_address = server_address
        self.save_root_path = save_root_path or os.getcwd()
        self.save_root_folder = save_root_folder or "raw_data"
        self.collector_config: dict = self.config['collector_config']
        # self.model_info: dict = self.config['model_info']
        self.model_info = {chosen_model_id: self.config['model_info'][chosen_model_id]}

        self.client_file_name: str = self.collector_config['parser_config']['client'] 
        self.provider_file_name: str = self.collector_config['parser_config']['mlProvider'] 
        self.temp_file_name: str = "temp.csv"

        print(f"Save folder: {save_root_path}, client filename: {self.client_file_name}, provider file name: {self.provider_file_name}")
        self.collector = Collector(config= self.collector_config)

    def run(self):
        # Start collector
        self.collector.start()

        root_save_folder = os.path.join(self.save_root_path, self.save_root_folder) 
        if not os.path.exists(root_save_folder):
            os.makedirs(root_save_folder)
        print(f"\n\n\n\n\n this is the root save folder: {root_save_folder}")

        for model_id, info in self.model_info.items():
            print(f"This is the chosen model: {model_id}")

            model_path = info['folder']
            print(f"This is the model path: {model_path}")

            # change the model by making request to the server
            weights_path = os.path.join(model_path, "model.h5")
            architecture_path = os.path.join(model_path, "model.json")
            print(f"This is the weights and architecture path of the model:\n\t{weights_path}\n\t{architecture_path}")   # Prepare payload

            payload = {
                'command': 'load_new_model',
                'local_file': True,
                'weights_url': weights_path,
                'architecture_url': architecture_path
            }

            # Make POST request to load new model
            try:
                response = requests.post(self.server_address, data= payload)
                response_json = response.json()
                timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

                print(f"At {timestamp}, this is the result of call for model {model_id}")
                if response.status_code == 200:
                    print(f"Success: {response_json}")
                else:
                    print(f"Failed: {response_json}")

                time.sleep(5)

                # profiling path
                profile_folder = os.path.join(root_save_folder, model_id) 
                if not os.path.exists(profile_folder):
                    os.makedirs(profile_folder)

                # Get file path for saving data
                self.collector.config["parser_config"]["client"] = os.path.join(profile_folder, self.client_file_name)
                self.collector.config["parser_config"]["mlProvider"] = os.path.join(profile_folder, self.provider_file_name)

                print(self.collector.config["parser_config"]["client"])
                print(self.collector.config["parser_config"]["mlProvider"])

                # write the record of this model
                # for a period of time
                # time.sleep(self.interval)

                # # let the collector write data in a tempt file
                # self.collector.config["parser_config"]["client"] = os.path.join(root_save_folder, self.temp_file_name)
                # self.collector.config["parser_config"]["mlProvider"] = os.path.join(root_save_folder, self.temp_file_name)

                # # Loop to save data from profiling different model
                # print(self.collector.config["parser_config"]["client"])
                # print(self.collector.config["parser_config"]["mlProvider"])
                

            except Exception as e:
                print(f"An error occurred at client request side: {e}")
        # print("Time to exit")
        # exit(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Automatic Profiling Models")
    # for client
    parser.add_argument('--test_ds', type=str, default="/artifact/nii/datasets/BDD100K-Classification/test.h5")
    parser.add_argument('--conf', type=str, help='config file path', default="./config.yaml")

    parser.add_argument('--rate', type=int, default=50)
    parser.add_argument('--model', type=str, help='specify the model', default="vgg_0")
    # for collector
    parser.add_argument('--interval', help='specify period of time to collect data for each model', type=int, default= 5)
    parser.add_argument('--collector_conf', help='configuration file', default="collector.yaml")


    args = parser.parse_args()
    
    # create client
    client_config = roheUtils.load_config(args.conf)
    server_address = client_config["server_address"]
    profiling_time = args.interval
    # create collector
    collector_conf = roheUtils.load_config(args.collector_conf)
    print(f"This is the config of the collector: {collector_conf}")
    collector_job = CollectorJob(interval=profiling_time, config=collector_conf, 
                                server_address = server_address, chosen_model_id= args.model)


    dataset_path = main_path + args.test_ds
    with h5py.File(dataset_path, 'r') as f:
        X_test = np.array(f['images'])
        y_test = np.array(f['labels'])
        dataset = {
            'X': X_test,
            'y': y_test,
        }
        total_data = len(X_test)
        print(f"This is the total data used: {total_data}")


    config = {
        'server_address': server_address,
        # 'test_ds': main_path + args.test_ds,
        'rate': args.rate,
        'qoa_config': client_config["qoa_config"],
    }
    client = InferenceServiceClientV2(config=config, dataset= dataset)


    # start collector
    collector_thread = threading.Thread(target=collector_job.run)
    collector_thread.daemon = True  # Set the thread as a daemon thread.
    collector_thread.start()


    time.sleep(15)
    # start client
    client.run()


