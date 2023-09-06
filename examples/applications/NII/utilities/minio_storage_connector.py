import os
import logging

import boto3
from botocore.client import Config

from time import sleep

logging.getLogger(__name__)

from .boto3_storage_connector import Boto3Connector, StorageInfo

class MinioConnector(Boto3Connector):
    time_sleep = 10
    def __init__(self, storage_info, parent= None):
        storage_info = StorageInfo(**storage_info)
        
        super().__init__(storage_info= storage_info, parent= parent)


    def _setup_connection(self, storage_info: StorageInfo):
        self._access_key = storage_info.access_key
        self._secret_key = storage_info.secret_key
        self._bucket_name = storage_info.bucket_name
        self._endpoint_url = storage_info.endpoint_url

        self._s3 = boto3.client('s3',
                                endpoint_url=self._endpoint_url,
                                aws_access_key_id=self._access_key, 
                                aws_secret_access_key=self._secret_key, 
                                config=Config(signature_version='s3v4'))

        try:
            self._s3.list_buckets()
            logging.info(f'Connected to MinIO server')
        except Exception as e:
            logging.error("Invalid MinIO Key.")
            raise e

