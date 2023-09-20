
import time
import os
import base64
from datetime import datetime
import time
import sys

import json

import argparse

import numpy as np
import h5py

import random

# set the ROHE to be in the system path
def get_parent_dir(file_path, levels_up=1):
    file_path = os.path.abspath(file_path)  # Get the absolute path of the running file
    parent_path = file_path
    for _ in range(levels_up):
        parent_path = os.path.dirname(parent_path)
    return parent_path

up_level = 4
root_path = get_parent_dir(__file__, up_level)
print(root_path)
sys.path.append(root_path)


from lib.service_connectors.mqttPublisher import MqttPublisher


def get_file_extension(file_path):
    return os.path.splitext(file_path)[1][1:]

def decode_image_file(image_path):
    # Read the image file and Base64 encode it
    with open(image_path, "rb") as image_file:
        image_data = image_file.read()

        image_b64 = base64.b64encode(image_data).decode('utf-8')
        return image_b64

def load_h5_data_set(data_path):
    with h5py.File(data_path, 'r') as f:
        X_test = np.array(f['images'])
        # y_test = np.array(f['labels'])
        return X_test

def load_numpy_image(data_path) -> np.ndarray:
    numpy_array= np.load(data_path)
    return numpy_array

def decode_numy_array(array: np.ndarray):
    # decoded_array = array.tobytes()
    decoded_array = base64.b64encode(array.tobytes()).decode('utf-8')

    return decoded_array

def main(config):
    publisher = MqttPublisher(broker_info= config['mqtt_config'], 
                    client_id= config['device_id'], pub_topic= config['mqtt_config']['topic'])

    rate = config['rate']
    data_path = config['test_ds']
    file_extension = get_file_extension(data_path)
    print(f"This is file extension: {file_extension}")

    if file_extension == 'h5' or file_extension == 'npy':
        print("decode numpy array type")
        if file_extension == 'h5':
            X_test = load_h5_data_set(data_path= data_path)
            index = random.randint(0, 50000)
            x = X_test[index]
        else:
            x = load_numpy_image(data_path= data_path)
        
        file_extension = 'npy'

        image_b64 = decode_numy_array(x)
        shape = x.shape
        dtype = x.dtype
    else:
        print("decode other format")
        # print("Data type is image")
        image_b64 = decode_image_file(data_path)

        shape = None
        dtype = None

    payload = {
        'timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'device_id': config['device_id'],
        'image': image_b64,
        'file_extension': file_extension,
        'shape': str(shape),
        'dtype': str(dtype),
    }
    print(f"shape of dtype: {shape}, {dtype}")

    time.sleep(2)

    for i in range(1, 10000000000000):
        publisher.send_data(payload)
        time.sleep(1)


    publisher.stop()

if __name__ == '__main__':
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for choosingg model to request")
    parser.add_argument('--conf', type= str, help='configuration file', 
                        default= "iot_device.json")
    parser.add_argument('--test_ds', type= str, help='default test dataset path', 
                default= "test_image/01.jpg")
    # parser.add_argument('--test_ds', type= str, help='default test dataset path', 
    #             default= "/home/vtn/aalto-internship/test_model/datasets/BDD100K-Classification/test.h5")
    parser.add_argument('--rate', type= int, help='default number of requests per second', default= 20)

    # Parse the parameters
    args = parser.parse_args()

    config_file = args.conf

    # load configuration file
    with open(config_file, 'r') as json_file:
        config = json.load(json_file)  

    config = {
        'device_id': config['device_id'],
        'mqtt_config': config['mqtt_config'],
        'test_ds': args.test_ds,
        'rate': args.rate,
    }
    main(config= config)