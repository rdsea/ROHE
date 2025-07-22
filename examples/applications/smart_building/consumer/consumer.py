# Simple script to test the inference server

import requests
import argparse
from concurrent.futures import ThreadPoolExecutor
import random
import time
import yaml
import logging
import traceback
import threading
import os
import sys

parent_dir = os.path.abspath(os.path.join(os.getcwd(), '..'))
sys.path.append(parent_dir)
from rohe.orchestration.multimodal_abstration import InferenceQuery

MAX_WORKERS = 10
DEFAULT_MODALITY_LIST = ["video", "acc_phone", "acc_watch", "gyro", "orientation"]
CONSUMER_PREFIX = "aaltosea"
DEFAULT_URL = "http://localhost:5123/inference_request"
DEFAULT_CONFIG_FILE = "../config/consumer.yaml"


def inf_request(url: str, data: InferenceQuery):
    try:
        response = requests.post(url, json=data.to_dict())
        print(response.json())
        return response.json()
    except Exception as e:
        logging.error(f"Error in invoking inference service: {e}")
        logging.error(traceback.format_exc())
        return None

def send_request(start_time, n_consumer, url, testing_time, interval, inf_query, max_workers):
    threading.Timer(interval, send_request, args=(start_time, n_consumer, url, testing_time, interval, inf_query, max_workers)).start()
    if time.perf_counter() - start_time < testing_time:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for i in range(n_consumer):
                # random select item in inf_query
                key = random.choice(list(inf_query.keys()))
                print(f"Sending request {i} with item: {key}")
                i_query = InferenceQuery.model_validate(inf_query[key])
                executor.submit(inf_request, url, i_query)
        
        
if __name__ == "__main__":

    with open(DEFAULT_CONFIG_FILE, 'r') as stream:
        config = yaml.safe_load(stream)
        
    testing_time = config.get('testing_time', 30)
    max_workers = config.get('num_workers', MAX_WORKERS)
    url = config.get('inference_url', DEFAULT_URL)
    interval = config.get('interval', 1)
    inf_query_path = config.get('inf_query_path', './query.yaml')
    n_consumer = config.get('n_consumer', 1)
    
    print(f"Configuration")
    print(f"Testing time: {testing_time} seconds")
    print(f"Max workers: {max_workers}")
    print(f"URL: {url}")
    print(f"Interval: {interval} seconds")
    print(f"Number of consumers: {n_consumer}")
    print(f"Inference query path: {inf_query_path}")

    with open(inf_query_path, 'r') as f:
        inf_query = yaml.safe_load(f)
    
    start_time = time.perf_counter()
    send_request(start_time, n_consumer, url, testing_time, interval, inf_query, max_workers)
    while True:
        print("Sending request...")
        time.sleep(2)
        if time.perf_counter() - start_time > testing_time:
            print("Testing time is over, exiting...")
            break
    

