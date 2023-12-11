import os
import requests
import logging
import json
import time
from typing import Callable

import numpy as np
import cv2

from concurrent.futures import ThreadPoolExecutor

import asyncio
import aiohttp
from aiohttp import FormData

from app.object_classification.lib.connectors.storage.minioStorageConnector import MinioConnector
import app.object_classification.modules.utils as pipeline_utils
import app.object_classification.modules.image_processing_functions as image_processing_func

from lib.rohe.roheObject import RoheObject

from qoa4ml.QoaClient import QoaClient

class ProcessingServiceExecutor(RoheObject):
    def __init__(self, config: dict, log_level=2):
        super().__init__(logging_level= log_level)

        self.max_thread: int = config['processing']['threading']['max_thread']
        self.thread_pool = ThreadPoolExecutor(self.max_thread)

        self.minio_connector = MinioConnector(storage_info= config['external_services']['minio_storage'])

        # 
        self.image_info_service_url = config['image_info_service']['url']
        self.inference_server_urls: tuple = config['inference_server']['urls']
        
        self.min_waiting_period: int = config['processing']['request']['retry_delay']['min']
        self.max_waiting_period: int = config['processing']['request']['retry_delay']['max']
        self.request_rate: int = config['processing']['request']['rate_per_second']
        

        # load processing function
        self.image_processing_func: Callable = pipeline_utils.get_function_from_module(module= image_processing_func, 
                                                                                       func_name= config['processing']['image_processing']['func_name'])

        self.image_dim = config['processing']['image_processing']['target_dim']
        self.image_dim = pipeline_utils.convert_str_to_tuple(self.image_dim)
        print(f"This is the image dim: {self.image_dim}")

        # create a temp folder to store temporary image file download from minio server 
        self.tmp_folder = "tmp_image_folder"
        if not os.path.exists(self.tmp_folder):
            os.mkdir(self.tmp_folder)

        if 'qoaClient' in config:
            print(f"\n\nThere is qoa service enable in the server")
            self.qoaClient: QoaClient = config['qoaClient']
            print(f"This is qoa client: {self.qoaClient}")

        else:
            self.qoaClient = None

    # running logic
    def run(self):
        self.waiting_period = self.min_waiting_period
        while True:
            task = self._get_image_from_image_info_service(requests)
            if task:
                self.thread_pool.submit(self._processing, task)
                self.waiting_period = self.min_waiting_period
                time.sleep(1/ self.request_rate)
            else:
                # if there is no image to be processed yet
                # sleep for a period, then continue to seek for taask
                time.sleep(self.waiting_period)
                self.waiting_period = self.waiting_period * 2
                self.waiting_period = min(self.max_waiting_period, self.waiting_period)


    # these functions to interact with the processing service controller
    def change_image_info_service_url(self, url: str) -> bool:
        try:
            print(f"Before the change, the url is: {self.image_info_service_url}")
            self.image_info_service_url = url
            print(f"\n\n\nchange info service url successfully. the url now is: {self.image_info_service_url}")
            return True
        except:
            return False

    def change_inference_service_url(self, urls: tuple) -> bool:
        try:
            self.inference_server_urls = urls
            return True
        except:
            return False

    def change_image_processing_function(self, func_name: str) -> bool:
    # the function must be defined in the image_processing_functions file in modules
        func: Callable = pipeline_utils.get_function_from_module(module= image_processing_func,
                                                                 func_name= func_name)
        if func is not None:
            self.image_processing_func = func
            return True
        else: 
            return False
        
    def _processing(self, task: dict):
        # task is a dictionary contain 6 key, v pairs
        #     'request_id':
        #     'timestamp': 
        #     'device_id': 
        #     'image_url': 
        #     'dtype': dtype,
        #     'shape': shape,
        # }

        # Process the image
        # download image from minio server
        temp_local_path = self._download_image_from_minio(image_url= task['image_url'])
        # temp_local_path = None
        # print(f"After downloading process")
        # if download fail, stop
        if not temp_local_path:
            logging.info(f"fail to download the image")
            return None
        
        task["temp_local_path"] = temp_local_path
        # process the image (in npy format or other type)
        processed_image: np.ndarray = self._image_processing(task)
        # print(f"This is the shape of the processed_image outside the calling function: {processed_image.shape}")
        del task['temp_local_path']

        # if fail to process the image
        if processed_image is None:
            logging.info(f"fail to process the image")
            return None
        

        processing_result = {
            "request_id": task['request_id'],
            "processed_image": processed_image
        }

        # Notify image info service of completion
        form_payload = task
        form_payload['command'] = 'complete'
        response = requests.post(self.image_info_service_url, data=form_payload)

        print(f"This is the response from image service info: {response.json()}")
        if response.status_code != 200:
            logging.info(f"Failed to notify Image Info Service the completion of task {task}")
            # logging.info(f"response from Image Info Service: {response.json()}")
            return None
        else:
            # Make a POST request to the inference servers
            logging.info(f"Make request to inference servers: {self.inference_server_urls}")
            self._make_inference_request(processing_result)
            return True



    def _get_image_from_image_info_service(self, requests) -> dict:
        response = requests.get(self.image_info_service_url)
        if response.status_code == 200:
            response_dict = json.loads(response.text) 
            try:
                task = response_dict['image_info']
            except Exception as e:
                # print(f"This is the error: {e}")
                # attempt to double decode to make it to be a dict
                task = json.loads(response_dict)['image_info']

                # ingestion_report = task['report']
                # self.qoaClient.importPReport(reports= ingestion_report)
                
            return task
        else:
            logging.info("No image to be processed yet")
            return None


    def _download_image_from_minio(self, image_url: str) -> str:
        logging.info(f"about to download image from minio: {image_url}")

        filename = image_url.split('/')[-1]
        temp_local_path = os.path.join(self.tmp_folder, filename)
        logging.info(f"This is temp file name: {temp_local_path}")
        success = self.minio_connector.download(remote_file_path= image_url,
                                         local_file_path= temp_local_path)
        if success:
            return temp_local_path
        return None

    def _image_processing(self, task: dict)-> np.ndarray:
        try:
            image_extension = pipeline_utils.extract_file_extension(task['image_url'])
            print(f"This is the image extension: {image_extension}")
            if image_extension == "npy":
                with open(task['temp_local_path'], "rb") as file:
                    raw_data = file.read()
                # shape = pipeline_utils.get_image_dim_from_str(task['shape'])
                shape = pipeline_utils.convert_str_to_tuple(task['shape'])
                image = np.frombuffer(raw_data, dtype=task['dtype']).reshape(shape)
            else:
                image = cv2.imread(task['temp_local_path'])
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                shape = image.shape
            
            if shape != self.image_dim:
                processed_image: np.ndarray = self.image_processing_func(image, self.image_dim)
            else:
                processed_image = image
            # print(f"This is the shape of the processed_image: {processed_image.shape}")
            return processed_image
        
        except Exception as e:
            print(f"This is the error in image process stage: {e}")
            return None

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
            # 'command': 'predict',
            'metadata': json.dumps(metadata)
        }

        files = {'image': ('image', image_bytes, 'application/octet-stream')}

        asyncio.run(self._make_requests(payload=payload, files=files))


    async def _make_requests(self, payload, files):
        print(f"\n\n\n\nabout to make request to inference servers: {self.inference_server_urls}")
        async with aiohttp.ClientSession() as session:
            tasks = [self._post_request(session, server, payload, files) for server in self.inference_server_urls]
            await asyncio.gather(*tasks)

    async def _post_request(self, session, url, payload, files):
        try:
            # Create a FormData object
            data = FormData()
            # data.add_field('command', payload['command'])
            data.add_field('metadata', payload['metadata'])

            # 'files' as {'file_name': ('filename', file_bytes, 'content_type')}
            for file_name, file_tuple in files.items():
                filename, file_bytes, content_type = file_tuple
                data.add_field(file_name, file_bytes, filename=filename, content_type=content_type)

            print(f"send request to this server {url} at timestamp {pipeline_utils.get_current_utc_timestamp()}")
            async with session.post(url, data=data) as response:
                print(f"Request sent to {url}, status code: {response.status}")
                if response.status == 200:
                    logging.debug("Inference successfully done")
                    message = await response.json()
                    logging.info(f"Inference server response: {message}")
                else:
                    message = await response.json()
                    logging.error(f"Inference failed with status code: {response.status}, message: {message}")

        except Exception as e:
            logging.error(f"Error while sending request to {url}: {e}")

