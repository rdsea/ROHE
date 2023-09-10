from concurrent.futures import ThreadPoolExecutor
import requests
import logging
import sys, os
import argparse
import json
import time


# set the ROHE to be in the system path
def get_parent_dir(file_path, levels_up=1):
    file_path = os.path.abspath(file_path)  # Get the absolute path of the running file
    parent_path = file_path
    for _ in range(levels_up):
        parent_path = os.path.dirname(parent_path)
    return parent_path

up_level = 7
root_path = get_parent_dir(__file__, up_level)
sys.path.append(root_path)

from examples.applications.NII.kube_deployment.dataProcessingService.modules import ProcessingObject
from lib import RoheObject


class ProcessService(RoheObject):
    def __init__(self, config, log_level=2):
        super().__init__()
        self.set_logger_level(logging_level=log_level)

        self.ProcessingAgent = ProcessingObject(config= config.get('processing_config', {}))
        self.thread_pool = ThreadPoolExecutor(config.get('max_threads', 3))

        self.task_coordinator_url = config['redis_server']['url']

        self.inference_server_url = config['inference_server']['url']

        self.min_request_period = config['processing_config']['min_request_period']
        self.max_request_period = config['processing_config']['max_request_period']
        self.request_period = self.min_request_period


    def _get_task_from_coordinator(self):
        response = requests.get(self.task_coordinator_url)
        if response.status_code == 200:
            response = json.loads(response.text)
            return response['image_info']
        else:
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
        # task is a dictionary contain 3 key, v pairs
        #     'timestamp': 
        #     'device_id': 
        #     'image_url': 
        # }

        # Process the image
        processing_result = self.ProcessingAgent.process(task)

        # Notify task coordinator of completion
        form_payload = {'command': 'complete'}
        response = requests.post(self.task_coordinator_url, data=form_payload)
        if response.status_code != 200:
            logging.error(f"Failed to notify Task Coordinator for {processing_result}")
            return False
        else:
            # Make a POST request to the inference server
            self._make_inference_request(processing_result)


    def _make_inference_request(self, processing_result) -> bool:
        # Convert the numpy array to bytes
        image_bytes = processing_result['processed_image'].tobytes()
        # Metadata and command
        shape_str = ','.join(map(str, processing_result['processed_image'].shape))

        metadata = {
            'shape': shape_str,
            'dtype': str(processing_result['processed_image'].dtype)
        }
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
            logging.info(response)
            logging.info("*" * 20)
            return True
        else:
            logging.error("Inference failed")
            return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Processing Service")
    parser.add_argument('--conf', type= str, help='configuration file', 
            default= "examples/applications/NII/kube_deployment/dataProcessingService/configurations/processing_service.json")
    parser.add_argument('--relative_path', type= bool, help='specify whether it is a relative path', default=True)

    # Parse the parameters
    args = parser.parse_args()

    port = int(args.port)
    config_file = args.conf
    relative_path = args.relative_path

    if relative_path:
        config_file = os.path.join(root_path, config_file)

    # load configuration file
    with open(config_file, 'r') as json_file:
        config = json.load(json_file)    

    service = ProcessService(config)
    service.run()