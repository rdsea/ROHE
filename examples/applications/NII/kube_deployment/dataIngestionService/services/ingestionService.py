from concurrent.futures import ThreadPoolExecutor
import requests
import sys, os
import json

import argparse

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

from lib import RoheObject
from examples.applications.NII.utilities import MqttSubscriber, MinioConnector
from examples.applications.NII.kube_deployment.dataIngestionService.modules import IngestionObject

class IngestionService(RoheObject):
    def __init__(self, config):
        super().__init__()
        self.log_level = config.get('log_level', 2)
        self.set_logger_level(logging_level= self.log_level)
        
        # ingestion object to deal with the ingestion process
        ingestion_config = config.get('ingestion_config', {})
        self.IngestionAgent = IngestionObject(**ingestion_config) 

        # MQTT subscriber to get message from IoT devices
        self.mqtt_subscriber = MqttSubscriber(host_object=self, **config['mqtt_config']) 

        # Minio Connector for uploading image
        self.minio_connector = MinioConnector(storage_info= config['minio_config'])

        # create multi threads to handle the upcomming message
        self.max_thread = config.get('max_thread', 3)
        self.thread_pool = ThreadPoolExecutor(self.max_threads)

        # to notify the redis server - communicate with the processing stage
        self.redis_like_service_url = config['redis_server']['url']


    def message_processing(self, client, userdata, msg):
        self.thread_pool.submit(self._process_message, client, userdata, msg)


    def _process_message(self, client, userdata, msg):
        # Deserialize the incoming JSON message payload
        payload = json.loads(msg.payload.decode('utf-8'))

        # go through the ingestion stage 
        ingestion_result = self.IngestionAgent.ingest(payload)

        # upload to cloud storage
        image_url = self.IngestionAgent.save_to_minio(minio_connector= self.minio_connector,
                                                      payload= payload)
        
        # notify task coordinator
        if image_url:
            # Prepare the payload for Redis-like service
            payload = {
                "timestamp": ingestion_result.get("timestamp", ""),
                "device_id": ingestion_result.get("device_id", ""),
                "image_url": ingestion_result.get("image_url")
            }

            # Notify Redis-like service
            response = requests.post(self.redis_like_service_url, json=payload)
            if response.status_code == 200:
                print(f"Successfully notified Redis-like service for {payload}")
                return True
            else:
                print(f"Failed to notify Redis-like service for {payload}")
                return False

        else:
            print("Fail to upload image to Minio Storage")
            return False

    
    def run(self):
        self.mqtt_subscriber.run()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Ingestion Service")
    parser.add_argument('--conf', type= str, help='configuration file', 
            default= "examples/applications/NII/kube_deployment/dataIngestionService/configurations/ingestion_service.json")
    parser.add_argument('--relative_path', type= bool, help='specify whether it is a relative path', default=True)

    # Parse the parameters
    args = parser.parse_args()

    config_file = args.conf
    relative_path = args.relative_path

    if relative_path:
        config_file = os.path.join(root_path, config_file)

    # load configuration file
    with open(config_file, 'r') as json_file:
        config = json.load(json_file)    

    config['minio_config']['access_key'] = os.getenv("minio_client_access_key")
    config['minio_config']['secret_key'] = os.getenv("minio_client_secret_key")

    service = IngestionService(config= config)
    service.run()
