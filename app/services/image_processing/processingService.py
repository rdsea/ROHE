from concurrent.futures import ThreadPoolExecutor
import requests
import logging
import sys, os
import argparse
import json
import time


from app.modules.image_processing.processingObject import ProcessingObject
from app.object_classification.lib.connectors.storage.minioStorageConnector import MinioConnector

from lib.modules.roheObject import RoheObject


class ProcessingService(RoheObject):
    def __init__(self, config, log_level=2):
        super().__init__()
        self.set_logger_level(logging_level=log_level)
        

        self.minio_connector = config['minio_connector']

        self.ProcessingAgent = ProcessingObject(config= config.get('processing_config', {}))
        self.thread_pool = ThreadPoolExecutor(config.get('max_threads', 3))

        self.task_coordinator_url = config['redis_server']['url']

        self.inference_server_url = config['inference_server']['url']

        self.min_request_period = config['processing_config']['min_request_period']
        self.max_request_period = config['processing_config']['max_request_period']
        self.request_period = self.min_request_period


    def _get_task_from_coordinator(self) -> dict:
        response = requests.get(self.task_coordinator_url)
        if response.status_code == 200:
            print("This is the source text from task coordinator:", response.text)
            response_dict = json.loads(response.text) 
            # response_dict = json.loads(json.loads(response.text))  # Double json.loads()
            # print(f"This is the response_dict: {response_dict}")  
            # print(f"This is the response_dict type: {type(response_dict)}")  
            try:
                task = response_dict['image_info']
            except Exception as e:
                # print(f"This is the error: {e}")
                # attempt to double decode to make it to be a dict
                task = json.loads(response_dict)['image_info']
                # print(f"The second attempt to load text: {task}")
            return task
        else:
            logging.info("No image to be processed yet")
            return None
    
    def run(self):
        while True:
            task = self._get_task_from_coordinator()
            if task:
                self.thread_pool.submit(self._process_task, task)
                self.request_period = max(1, self.request_period // 2)
            else:
                time.sleep(self.request_period)
                self.request_period = min(self.max_request_period, self.request_period * 2)

    def _process_task(self, task):
        # task is a dictionary contain 6 key, v pairs
        #     'request_id':
        #     'timestamp': 
        #     'device_id': 
        #     'image_url': 
        
        # }

        # Process the image
        processing_result = self.ProcessingAgent.process(task, self.minio_connector)
        
        if processing_result is not None:
            # Notify task coordinator of completion
            form_payload = task
            form_payload['command'] = 'complete'

            # logging.info(f"This is the form sent to the server: {form_payload}")
            response = requests.post(self.task_coordinator_url, data=form_payload)
            if response.status_code != 200:
                logging.info(f"Failed to notify Task Coordinator the completion for {task}")
                logging.info(f"response from task coordinator: {response.json()}")
                return False
            else:
                # Make a POST request to the inference server
                logging.info(f"Make request to inference server")
                self._make_inference_request(processing_result)
                return True
        else:
            logging.info("fail to process the image (cannot download the image)")
            return False


    def _make_inference_request(self, processing_result) -> bool:
        # Convert the numpy array to bytes
        image_bytes = processing_result['processed_image'].tobytes()
        # Metadata and command
        shape_str = ','.join(map(str, processing_result['processed_image'].shape))

        metadata = {
            'request_id': processing_result['request_id'],
            'shape': shape_str,
            'dtype': str(processing_result['processed_image'].dtype)
        }
        print(f"\n\n\n\n\nThis is the metadata: {metadata}")
        # Create a dictionary to include both command and metadata
        payload = {
            'command': 'predict',
            'metadata': json.dumps(metadata)
        }

        files = {'image': ('image', image_bytes, 'application/octet-stream')}

        # Make the POST request to the inference server
        response = requests.post(self.inference_server_url, data=payload, files=files)

        if response.status_code == 200:
            logging.debug("Inference successfully done")
            logging.info("*" * 20)
            message = json.loads(response.text)

            logging.info(f"Inference server response: {message}")


            logging.info("*" * 20)
            return True
        else:
            logging.error("Inference failed")
            return False

def load_minio_storage(storage_info):
    minio_connector = MinioConnector(storage_info= storage_info)
    return minio_connector

