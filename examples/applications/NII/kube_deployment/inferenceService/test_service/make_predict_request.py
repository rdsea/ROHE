import requests
import json
import numpy as np
import time
from datetime import datetime
import h5py
import random
import argparse


def send_predict_request(image_array, url='http://edge-k3s-j6.cs.aalto.fi:9000/inference_service'):
    payload = {
        'command': 'predict',
        'metadata': json.dumps({'shape': '32,32,3', 'dtype': str(image_array.dtype)})
    }
    files = {'image': ('image', image_array.tobytes(), 'application/octet-stream')}
    
    response = requests.post(url, data=payload, files=files)
    return response.json()

def main(config):
    test_ds = config['test_ds']
    rate = config['rate']  # Number of requests per second
    server_address = config['server_address']

    print(f"This is server address: {server_address}")
    sleep_time = 1.0 / rate

    # # Create some dummy image data (32x32x3)
    # image_data = np.random.randint(0, 128, (32, 32, 3), dtype=np.uint8)
    with h5py.File(test_ds, 'r') as f:
        X_test = np.array(f['images'])
        # y_test = np.array(f['labels'])

    index = random.randint(0, 50000)
    image_data = X_test[index]
    # # fixed index
    # image_data = X_test[100]

    for i in range(1, 10000):
        # Create some dummy image data (32x32x3)
        # image_data = np.random.randint(0, 128, (32, 32, 3), dtype=np.uint8)
        response = send_predict_request(image_data, server_address)
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        print(f"at {timestamp}, Request number {i} for image index of {index}, Received response {response} ")
        time.sleep(sleep_time)

if __name__ == '__main__':
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for choosingg model to request")
    parser.add_argument('--server_address', type= str, help='default service address', 
                        # default= "http://127.0.0.1:39499/inference_service")
                        default= "http://edge-k3s-j6.cs.aalto.fi:39499/inference_service")
    parser.add_argument('--test_ds', type= str, help='default test dataset path', 
                default= "/home/vtn/aalto-internship/test_model/datasets/BDD100K-Classification/test.h5")
    parser.add_argument('--rate', type= int, help='default number of requests per second', default= 20)

    # Parse the parameters
    args = parser.parse_args()

    config = {
        'server_address': args.server_address,
        'test_ds': args.test_ds,
        'rate': args.rate,
    }
    main(config= config)
