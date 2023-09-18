import requests
import json
import numpy as np
import time
from datetime import datetime
import h5py
import random
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor

def send_predict_request(image_array, url, thread_id):
    payload = {
        'command': 'predict',
        'metadata': json.dumps({'shape': '32,32,3', 'dtype': str(image_array.dtype)})
    }
    files = {'image': ('image', image_array.tobytes(), 'application/octet-stream')}

    # print(f"Thread {thread_id}, at {timestamp}, make a request.")
    response = requests.post(url, data=payload, files=files)
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    print(f"Thread {thread_id}, at {timestamp}, Received response {response.json()}")

def request_batch(image_data, server_address, rate, executor):
    for i in range(rate):
        executor.submit(send_predict_request, image_data, server_address, i)

def main(config):
    test_ds = config['test_ds']
    rate = config['rate']
    server_address = config['server_address']

    with h5py.File(test_ds, 'r') as f:
        X_test = np.array(f['images'])

    index = random.randint(0, 50000)
    image_data = X_test[index]

    with ThreadPoolExecutor(max_workers=rate) as executor:
        num_seconds = 100000
        for _ in range(num_seconds):
            request_batch(image_data, server_address, rate, executor)
            time.sleep(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for choosing model to request")
    parser.add_argument('--server_address', type=str, help='default service address',
                        default="http://127.0.0.1:9999/inference_service")
                        # default="http://127.0.0.1:9000/inference_service")
                        # default="http://127.0.0.1:39499/inference_service")
    parser.add_argument('--test_ds', type=str, help='default test dataset path',
                        default="/home/vtn/aalto-internship/test_model/datasets/BDD100K-Classification/test.h5")
    parser.add_argument('--rate', type=int, help='default number of requests per second', default=20)

    args = parser.parse_args()

    config = {
        'server_address': args.server_address,
        'test_ds': args.test_ds,
        'rate': args.rate,
    }

    main(config=config)
