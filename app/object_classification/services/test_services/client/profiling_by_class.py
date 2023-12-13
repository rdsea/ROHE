
import os, sys
import time
import argparse
from datetime import datetime

import h5py
import numpy as np

import threading

from dotenv import load_dotenv
load_dotenv()

main_path = os.getenv('ROHE_PATH')
print(f"This is main path: {main_path}")
sys.path.append(main_path)

# from client import InferenceServiceClient

from app.object_classification.services.test_services.client.client import InferenceServiceClient

from tool.profiling.collector import Collector
import lib.roheUtils as roheUtils

# from typing import List

def load_dataset(dataset_path: str):
    with h5py.File(dataset_path, 'r') as f:
        X_test = np.array(f['images'])
        y_test = np.array(f['labels'])
        dataset = {
            'X': X_test,
            'y': y_test,
        }
        total_data = len(X_test)
        print(f"This is the total data used: {total_data}")

    return dataset


def list_files_in_directory(directory_path):
    # Check if the directory exists
    if not os.path.exists(directory_path):
        print(f"Directory does not exist. {directory_path}")
        return []

    # List all file paths within the directory
    file_paths = []
    for file in os.listdir(directory_path):
        full_path = os.path.join(directory_path, file)
        if os.path.isfile(full_path):
            file_paths.append(full_path)

    return file_paths

def get_filename_without_extension(file_path):
    base_name = os.path.basename(file_path)
    file_name_without_extension = os.path.splitext(base_name)[0]
    return file_name_without_extension

class CollectorJob:
    def __init__(self, config: dict, client: InferenceServiceClient, 
                 ds_paths: list,
                 save_root_path: str = None, save_root_folder: str = None):
        self.config: dict = config

        self.ds_paths = ds_paths
        self.client = client

        self.save_root_path = save_root_path or os.getcwd()
        self.save_root_folder = save_root_folder or "raw_data"
        self.collector_config: dict = self.config['collector_config']
        

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

        for ds_path in self.ds_paths:
            print(f"\n\n\nThis is the ds_path: {ds_path}")
            time.sleep(10)
            dataset = load_dataset(ds_path)
            class_name = get_filename_without_extension(ds_path)
            self.client.change_dataset(new_dataset= dataset)

            # profiling path
            profile_folder = os.path.join(root_save_folder, class_name) 
            if not os.path.exists(profile_folder):
                os.makedirs(profile_folder)

            # Get file path for saving data
            self.collector.config["parser_config"]["client"] = os.path.join(profile_folder, self.client_file_name)
            self.collector.config["parser_config"]["mlProvider"] = os.path.join(profile_folder, self.provider_file_name)

            print(self.collector.config["parser_config"]["client"])
            print(self.collector.config["parser_config"]["mlProvider"])

            self.client.run()
            time.sleep(30)

        print("About to exit the process")
        self.collector.stop()

        # try:
        #     self.collector.stop()
        # except:
        #     pass
        # exit(0)




if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Automatic Profiling Models")
    # for client
    parser.add_argument('--ds_folder', type=str, default="/artifact/nii/datasets/BDD100K-Classification/test_set/class")
    parser.add_argument('--rate', type=int, default=1)
    parser.add_argument('--conf', type=str, default="client_config.yaml")


    # for collector
    parser.add_argument('--interval', help='specify period of time to collect data for each model', type=int, default= 5)
    parser.add_argument('--collector_conf', help='configuration file', default="collector_config.yaml")


    args = parser.parse_args()
    ds_folder = main_path + args.ds_folder
    ds_paths = list_files_in_directory(ds_folder) 
    
    # create client
    client_config = roheUtils.load_config(args.conf)
    server_address = client_config["server_address"]

    # create collector
    collector_conf = roheUtils.load_config(args.collector_conf)
    print(f"This is the config of the collector: {collector_conf}")


    config = {
        'server_address': server_address,
        'rate': args.rate,
        'qoa_config': client_config["qoa_config"],
    }

    client = InferenceServiceClient(config= config, dataset= None)

    collector_job = CollectorJob(config=collector_conf, client= client,
                                 ds_paths= ds_paths)

    collector_job.run()
    # # # start collector
    # collector_thread = threading.Thread(target=collector_job.run)
    # collector_thread.daemon = True  # Set the thread as a daemon thread.
    # collector_thread.start()


    # time.sleep(15)
    # # start client
    # client.run()


