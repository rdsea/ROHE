from concurrent.futures import ThreadPoolExecutor
import requests
import json
from threading import Lock


from lib.modules.roheObject import RoheObject
from lib.service_connectors.mqttSubscriber import MqttSubscriber
from lib.service_connectors.minioStorageConnector import MinioConnector
from lib.modules.object_classification.ingestionObject import IngestionObject


class IngestionService(RoheObject):
    def __init__(self, config):
        super().__init__()
        self.log_level = config.get('log_level', 2)
        self.set_logger_level(logging_level= self.log_level)
        
        # ingestion object to deal with the ingestion process
        ingestion_config = config.get('ingestion_config', {})


        # # Minio Connector for uploading image
        # self.minio_connector = MinioConnector(storage_info= config['minio_config'])
        self.minio_connector: MinioConnector = config['minio_connector']

        self.storage_lock: Lock = config['storage_lock']

        # to notify the redis server - communicate with the processing stage
        self.redis_like_service_url = config['redis_server']['url']
        print(f"\n\n\n This is the address of redis server: {self.redis_like_service_url}")

        # create multi threads to handle the upcomming message
        self.max_thread = config.get('max_thread', 3)
        self.thread_pool = ThreadPoolExecutor(self.max_thread)
        
        self.IngestionAgent = IngestionObject(**ingestion_config) 

        # MQTT subscriber to get message from IoT devices
        self.mqtt_subscriber = MqttSubscriber(host_object=self, **config['mqtt_config']) 

    def message_processing(self, client, userdata, msg):
        # print(f'Receive message from mqtt broker: {msg}')
        self.thread_pool.submit(self._process_message, client, userdata, msg)
        # print("After submitting")

    def _process_message(self, client, userdata, msg):
        print(f"\nBegin to process image")
        # payload template = {
        #     'timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        #     'device_id': "camera01",
        #     'image': image_b64,
        #     'file_extension': file_extension,
        #     'shape': None,
        #     'dtype': None,
        # }
        # Deserialize the incoming JSON message payload
        payload = json.loads(msg.payload.decode('utf-8'))
        # print(f"This is the payload: {payload}")
        # go through the ingestion stage 
        ingestion_result = self.IngestionAgent.ingest(payload)
        if ingestion_result == None:
            print("Fail to process the file. User file extension is not supported yet.")
            return False
        
        image = ingestion_result['image']

        # # upload to cloud storage
        with self.storage_lock:
            image_url = self.IngestionAgent.save_to_minio(minio_connector= self.minio_connector,
                                                        payload= ingestion_result)
        
        # notify task coordinator
        if image_url is not None:
            # Prepare the payload for Redis-like service
            payload = {
                "command": "add",
                "request_id": ingestion_result.get("request_id"),
                "timestamp": ingestion_result.get("timestamp"),
                "device_id": ingestion_result.get("device_id"),
                "image_url": image_url,
            }

            # Notify Redis-like service
            response = requests.post(self.redis_like_service_url, data=payload)
            if response.status_code == 200:
                print(f"\nSuccessfully notified Redis-like service for {payload}\n\n")
                return True
            else:
                print(f"Failed to notify Redis-like service for {payload}")
                return False

        else:
            print("Fail to upload image to Minio Storage")
            return False

    
    def run(self):
        self.mqtt_subscriber.run()


# if __name__ == '__main__':
#     parser = argparse.ArgumentParser(description="Argument for Ingestion Service")
#     parser.add_argument('--conf', type= str, help='configuration file', 
#             default= "examples/applications/NII/kube_deployment/dataIngestionService/configurations/ingestion_service.json")
#     parser.add_argument('--relative_path', type= bool, help='specify whether it is a relative path', default=True)

#     # Parse the parameters
#     args = parser.parse_args()

#     config_file = args.conf
#     relative_path = args.relative_path

#     if relative_path:
#         config_file = os.path.join(root_path, config_file)

#     storage_lock = Lock()
#     # load configuration file
#     with open(config_file, 'r') as json_file:
#         config = json.load(json_file)    

#     config['minio_config']['access_key'] = os.getenv("minio_client_access_key")
#     config['minio_config']['secret_key'] = os.getenv("minio_client_secret_key")

#     # Minio Connector for uploading image
#     minio_connector = MinioConnector(storage_info= config['minio_config'])
#     config['minio_connector'] = minio_connector

#     config['storage_lock'] = storage_lock

#     print(f"This is the minio connector: {minio_connector}")
#     service = IngestionService(config= config)
#     service.run()
