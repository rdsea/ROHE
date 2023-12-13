import os, sys

import io
import time
from datetime import datetime
import argparse

import requests
import json
import numpy as np
import h5py
from concurrent.futures import ThreadPoolExecutor


import qoa4ml.qoaUtils as qoa_utils
from qoa4ml.QoaClient import QoaClient



# set the ROHE to be in the system path
from dotenv import load_dotenv
load_dotenv()

main_path = os.getenv('ROHE_PATH')
print(f"This is main path: {main_path}")
sys.path.append(main_path)



class InferenceServiceClient:
    def __init__(self, config, dataset: dict):
        self.config = config
        self.server_address = config['server_address']
        self.dataset = dataset
        self.rate: int = config['rate']
        if config.get('qoa_config'):
            self.qoaclient = QoaClient(config["qoa_config"])

        # self.complete_job = False

    # def set_qoa_timer(self):
    #     if hasattr(self, 'qoaclient'):
    #         self.qoaclient.timer()

    def message_deserialize(self, string_object) -> dict:
        return json.loads(string_object.decode("utf-8"))

    def send_request(self, image_array, image_label, url, thread_id):
        image_bytes = io.BytesIO(image_array.tobytes())  

        data = {
            'timestamp': str(time.time()),
            'device_id': 'aaltosea-cam-test',
            'image_extension': 'npy',
            'shape': ','.join(map(str, image_array.shape)),  # Example: '100,100,3'
            'dtype': str(image_array.dtype)  # Example: 'uint8'
        }
        # Prepare the files to send
        files = {
            'image': ('image.npy', image_bytes, 'application/octet-stream')
        }
        

        # Send the POST request
        # self.set_qoa_timer()
        response = requests.post(url, data=data, files=files)
        # self.set_qoa_timer()
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        response_dict = json.loads(response.text) 


        print(f"Thread {thread_id}, at {timestamp}, Received response {response_dict}")
    
    def request_batch(self, images_data, images_label, executor):
        n = len(images_data)
        for i in range(n):
            executor.submit(self.send_request, images_data[i], images_label[i], self.server_address, i)


    def retrieve_class_label(self, labels_encoding):
        class_labels = np.argmax(labels_encoding, axis=1)
        return class_labels
    
    def main(self):
        X_test = self.dataset['X']
        y_test = self.dataset['y']

        total_sample = len(X_test)
        # total_sample = 16

        with ThreadPoolExecutor(max_workers=self.rate) as executor:
            for start_index in range(0, total_sample, self.rate):
                print(f"Start index now: {start_index}")
                end_index = start_index + self.rate
                end_index = min(end_index, total_sample - 1)

                images_data = X_test[start_index: end_index]
                images_label = y_test[start_index: end_index]
                images_label = self.retrieve_class_label(images_label)

                self.request_batch(images_data, images_label, executor)

                # send x request every 1 second
                time.sleep(1)



    def change_dataset(self, new_dataset):
        self.dataset = new_dataset

    def run(self):
        self.main()

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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for choosing model to request")
    # parser.add_argument('--test_ds', type=str, default="/artifact/nii/datasets/BDD100K-Classification/test.h5")
    parser.add_argument('--ds_folder', type=str, default="/artifact/nii/datasets/BDD100K-Classification/test_set/class")

    parser.add_argument('--rate', type=int, default=100)
    parser.add_argument('--conf', type=str, default="./client_config.yaml")

    args = parser.parse_args()
    client_config = qoa_utils.load_config(args.conf)
    server_address = client_config["server_address"]
    ds_folder = main_path + args.ds_folder


    config = {
        'server_address': server_address,
        'rate': args.rate,
        'qoa_config': client_config["qoa_config"],
    }

    client = InferenceServiceClient(config=config, dataset= None)
    ds_paths = list_files_in_directory(ds_folder) 
    for ds_path in ds_paths:
        print(f"\n\n\nThis is the ds_path: {ds_path}")
        time.sleep(10)
        dataset = load_dataset(ds_path)
        client.change_dataset(new_dataset= dataset)
        client.run()
