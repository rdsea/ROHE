import requests
import json
import numpy as np
import time
from datetime import datetime
import h5py
import random

def send_predict_request(image_array, url='http://localhost:9000/inference_service'):
    payload = {
        'command': 'predict',
        'metadata': json.dumps({'shape': '32,32,3', 'dtype': str(image_array.dtype)})
    }
    files = {'image': ('image', image_array.tobytes(), 'application/octet-stream')}
    
    response = requests.post(url, data=payload, files=files)
    return response.json()

def main():
    url = 'http://localhost:9000/inference_service'
    # rate = 10  # Number of requests per second
    rate = 1  # Number of requests per second
    sleep_time = 1.0 / rate

    # # Create some dummy image data (32x32x3)
    # image_data = np.random.randint(0, 128, (32, 32, 3), dtype=np.uint8)
    test_ds = "/home/vtn/aalto-internship/test_model/datasets/BDD100K-Classification/test.h5"
    with h5py.File(test_ds, 'r') as f:
        X_test = np.array(f['images'])
        y_test = np.array(f['labels'])

    image_data = X_test[random.randint(0, 50000)]

    for i in range(1, 10000):
        # Create some dummy image data (32x32x3)
        # image_data = np.random.randint(0, 128, (32, 32, 3), dtype=np.uint8)
        response = send_predict_request(image_data, url)
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        print(f"at {timestamp}, Request number {i}, Received response {response} ")
        time.sleep(sleep_time)

if __name__ == '__main__':
    main()
