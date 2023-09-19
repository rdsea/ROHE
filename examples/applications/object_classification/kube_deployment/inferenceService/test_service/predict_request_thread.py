import requests
import json
import numpy as np
import time
from datetime import datetime
import h5py
import random
import argparse, os
import threading
from concurrent.futures import ThreadPoolExecutor
import pathlib

def get_file_dir(file, to_string=True):
    current_dir = pathlib.Path(file).parent.absolute()
    if to_string:
        return str(current_dir)
    else:
        return current_dir

def get_parent_dir(file, parent_level=1, to_string=True):
    current_dir = get_file_dir(file=file, to_string=False)
    for i in range(parent_level):
        current_dir = current_dir.parent.absolute()
    if to_string:
        return str(current_dir)
    else:
        return current_dir

lib_level = os.environ.get('LIB_LEVEL')
if not lib_level:
    lib_level = 6
main_path = config_file = get_parent_dir(__file__,lib_level)

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
                        # default="http://edge-k3s-j6.cs.aalto.fi:30005/inference_service")
                        default="http://127.0.0.1:30005/inference_service")
                        # default="http://127.0.0.1:39499/inference_service")
    parser.add_argument('--test_ds', type=str, help='default test dataset path',
                        default="/artifact/nii/datasets/BDD100K-Classification/test.h5")
    parser.add_argument('--rate', type=int, help='default number of requests per second', default=20)

    args = parser.parse_args()

    config = {
        'server_address': args.server_address,
        'test_ds': main_path+args.test_ds,
        'rate': args.rate,
    }

    main(config=config)
