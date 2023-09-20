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
    lib_level = 5
main_path = config_file = get_parent_dir(__file__,lib_level)

def message_deserialize(string_object) -> dict:
    return json.loads(string_object.decode("utf-8"))

def send_predict_request(image_array, image_label, url, thread_id):
    payload = {
        'command': 'predict',
        'metadata': json.dumps({'shape': '32,32,3', 'dtype': str(image_array.dtype)})
    }
    files = {'image': ('image', image_array.tobytes(), 'application/octet-stream')}

    response = requests.post(url, data=payload, files=files)
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
    print(f"Thread {thread_id}, at {timestamp}, Received response {response}. Acc= {acc}")


def request_batch(images_data, images_label, server_address, rate, executor):
    for i in range(rate):
        executor.submit(send_predict_request, images_data[i], images_label[i], server_address, i)

def retrieve_class_label(labels_encoding):
    class_labels = np.argmax(labels_encoding, axis=1)
    return class_labels

def main(config):
    test_ds = config['test_ds']
    rate = config['rate']
    server_address = config['server_address']

    with h5py.File(test_ds, 'r') as f:
        X_test = np.array(f['images'])
        y_test = np.array(f['labels'])

        total_data = len(X_test)

    with ThreadPoolExecutor(max_workers=rate) as executor:
        num_seconds = 100000
        start_index = 0
        for i in range(num_seconds):
            images_data = X_test[start_index: start_index + rate]
            images_label = y_test[start_index: start_index + rate]
            images_label = retrieve_class_label(images_label)


            start_index = start_index + rate

            request_batch(images_data, images_label, server_address, rate, executor)
            time.sleep(1)

            if start_index + rate >= total_data:
                print("This is the end of the dataset.")
                print("about to reset the index into 0 to continue processing")
                start_index = 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for choosing model to request")
    parser.add_argument('--server_address', type=str, help='default service address',
                        default="http://127.0.0.1:30005/inference_service")
                        # default="http://edge-k3s-j6.cs.aalto.fi:30005/inference_service")
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
