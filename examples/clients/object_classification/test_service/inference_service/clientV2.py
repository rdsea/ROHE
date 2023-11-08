import requests
import json
import numpy as np
import time
from datetime import datetime
import h5py
import argparse
import os, sys
import random
from concurrent.futures import ThreadPoolExecutor
import pathlib
import qoa4ml.qoaUtils as qoa_utils
from qoa4ml.QoaClient import QoaClient
from qoa4ml import qoaUtils as qoa_utils

import threading
import qoa4ml.qoaUtils as qoa_utils


# set the ROHE to be in the system path
from dotenv import load_dotenv
load_dotenv()

main_path = os.getenv('ROHE_PATH')
print(f"This is main path: {main_path}")
sys.path.append(main_path)



class InferenceServiceClientV2:
    def __init__(self, config, dataset: dict):
        self.config = config
        self.server_address = config['server_address']
        # self.test_ds = config['test_ds']
        self.dataset = dataset
        self.rate: int = config['rate']
        self.qoaclient = QoaClient(config["qoa_config"])

    def set_qoa_timer(self):
        if hasattr(self, 'qoaclient'):
            self.qoaclient.timer()

    def message_deserialize(self, string_object) -> dict:
        return json.loads(string_object.decode("utf-8"))

    def send_predict_request(self, image_array, image_label, url, thread_id):
        payload = {
            'command': 'predict',
            'metadata': json.dumps({'shape': '32,32,3', 'dtype': str(image_array.dtype)})
        }
        files = {'image': ('image', image_array.tobytes(), 'application/octet-stream')}
        self.set_qoa_timer()
        response = requests.post(url, data=payload, files=files)
        self.set_qoa_timer()
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        response_dict = json.loads(response.text) 

        try:
            response = response_dict['response']
            prediction = response['class']
        except Exception as e:
            response_dict = json.loads(response_dict)
            response = response_dict['response']
            prediction = response['class']

        acc = int(prediction) == int(image_label)
        response['accuracy'] = acc
        
        if hasattr(self, 'qoaclient'):
            self.qoaclient.observeInferenceMetric("confidence", float(response['confidence_level']))
            self.qoaclient.observeInferenceMetric("accuracy", int(acc))
            self.qoaclient.observeInferenceMetric("predict_object", int(prediction))
            self.qoaclient.observeMetric("class_object", int(image_label), 1)
            self.qoaclient.report(submit=True)

        print(f"Thread {thread_id}, at {timestamp}, Received response {response}")
    
    def request_batch(self, images_data, images_label, executor):
        # print(f"This is the len of image data: {len(images_data)}")
        for i in range(self.rate):
            executor.submit(self.send_predict_request, images_data[i], images_label[i], self.server_address, i)

    def retrieve_class_label(self, labels_encoding):
        class_labels = np.argmax(labels_encoding, axis=1)
        return class_labels
    
    def main(self):
        X_test = self.dataset['X']
        y_test = self.dataset['y']

        total_sample = len(X_test)
        with ThreadPoolExecutor(max_workers=self.rate) as executor:
            for start_index in range(0, total_sample, self.rate):
            # for start_index in range(26550, total_sample, 100):
            # for start_index in range(0, 310, self.rate):
                print(f"Start index now: {start_index}")
                end_index = start_index + self.rate
                end_index = min(end_index, total_sample - 1)
                # images_data = X_test[start_index: start_index + self.rate]
                # images_label = y_test[start_index: start_index + self.rate]

                images_data = X_test[start_index: end_index]
                images_label = y_test[start_index: end_index]
                images_label = self.retrieve_class_label(images_label)

                self.request_batch(images_data, images_label, executor)

                # send x request every 1 second
                time.sleep(1)


        #     # executor.shutdown(wait=True) 
        # print("time to exit")
        # exit(0)
            


    def run(self):
        self.main()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for choosing model to request")
    parser.add_argument('--test_ds', type=str, default="/artifact/nii/datasets/BDD100K-Classification/test.h5")
    parser.add_argument('--rate', type=int, default=100)
    parser.add_argument('--conf', type=str, default="./config.yaml")

    args = parser.parse_args()
    client_config = qoa_utils.load_config(args.conf)
    server_address = client_config["server_address"]

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
        # 'dataset': dataset,
        'rate': args.rate,
        'qoa_config': client_config["qoa_config"],
    }

    client = InferenceServiceClientV2(config=config, dataset= dataset)
    client.run()
