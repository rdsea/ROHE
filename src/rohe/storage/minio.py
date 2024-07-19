import boto3
from ..common.storage import StorageInfo
from botocore.client import Config

from .boto3 import Boto3Connector

# import logging

# logging.getLogger(__name__)


class MinioConnector(Boto3Connector):
    def __init__(self, storage_info, parent=None):
        storage_info = StorageInfo(**storage_info)

        super().__init__(storage_info=storage_info, parent=parent)

    def _setup_connection(self, storage_info: StorageInfo):
        print(
            f"About to setup connection to minio server with bucket name: {storage_info.bucket_name}"
        )
        self._access_key = storage_info.access_key
        self._secret_key = storage_info.secret_key
        self._bucket_name = storage_info.bucket_name
        self._endpoint_url = storage_info.endpoint_url

        self._s3 = boto3.client(
            "s3",
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            config=Config(signature_version="s3v4"),
        )

        try:
            self._s3.list_buckets()
            # logging.info(f'Connected to MinIO server')
            print("Connected to MinIO server")
        except Exception as e:
            # logging.error("Invalid MinIO Key.")
            print("Invalid MinIO Key.")
            raise e
