import io
import logging
import os
import re
import sys
from abc import ABC, abstractmethod

logging.getLogger(__name__)

from ..common.storage import StorageInfo


class Boto3Connector(ABC):
    def __init__(self, storage_info: StorageInfo, parent=None):
        self._parent_thread = parent
        self._bucket_name: str = ""

        # s3 is the return object of the function boto3.client
        self._s3 = None
        self._setup_connection(storage_info=storage_info)

    @abstractmethod
    def _setup_connection(self, storage_info: StorageInfo):
        pass

    def upload_binary_data(self, binary_data: bytes, remote_file_path: str, try_time=5):
        """
        Uploads binary data directly to S3/MinIO.

        Args:
            binary_data (in bytes or io.ByteIO format): The binary data to upload.
            remote_file_path (str): The S3 path where the binary data will be stored.
            try_time (int): Number of attempts for the upload operation. Defaults to 5.

        Returns:
            bool: True if upload is successful, False otherwise.
        """

        if isinstance(binary_data, bytes):
            binary_data = io.BytesIO(binary_data)

        # Upload the file-like object to S3
        success = False
        for attempt in range(try_time):
            try:
                logging.info(f"Uploading data to {remote_file_path}...")
                self._s3.upload_fileobj(
                    binary_data, self._bucket_name, remote_file_path
                )
                logging.info(f"Successfully uploaded data to {remote_file_path}")
                success = True
                break
            except Exception as e:
                logging.error(e)

        # binary_data.close()
        return success

    def upload(self, local_file_path: str, remote_file_path: str, try_time=5):
        # check if local_file_path is exist, if not create one
        if not os.path.exists(local_file_path):
            os.makedirs(local_file_path.split(os.path.sep)[:-1])
        # call synchronously
        if self._parent_thread is None:
            try:
                logging.info(f"Uploading {local_file_path} to {remote_file_path}...")
                self._s3.upload_file(
                    local_file_path, self._bucket_name, remote_file_path
                )
                logging.info(
                    f"Successfully uploaded {local_file_path} to {remote_file_path}"
                )
                return True
            except Exception as e:
                logging.error(e)
                return False
        else:  # call asynchronously
            t = 1
            while t < try_time:
                try:
                    logging.info(
                        f"Uploading {local_file_path} to {remote_file_path}..."
                    )
                    self._s3.upload_file(
                        local_file_path, self._bucket_name, remote_file_path
                    )
                    logging.info(
                        f"Successfully uploaded {local_file_path} to {remote_file_path}"
                    )
                    self._parent_thread.on_upload(True)
                    break
                except Exception as e:
                    logging.error(e)

            self._parent_thread.on_upload(False)

    def download(self, remote_file_path, local_file_path, try_time=5):
        # call synchronously
        if self._parent_thread is None:
            try:
                logging.info(f"Saving {remote_file_path} to {local_file_path}...")
                self._s3.download_file(
                    self._bucket_name, remote_file_path, local_file_path
                )
                logging.info(f"Saved {remote_file_path} to {local_file_path}")
                return True
            except Exception:
                # raise e
                return False
        else:  # call asynchronously
            result = False
            t = 1
            while t < try_time:
                try:
                    logging.info(f"Saving {remote_file_path} to {local_file_path}...")
                    self._s3.download_file(
                        self._bucket_name, remote_file_path, local_file_path
                    )
                    logging.info(f"Saved {remote_file_path} to {local_file_path}")
                    result = True
                    break
                except Exception as e:
                    logging.error(e)
            self._parent_thread.on_download(result)

    def is_file_exists(self, file_path: str) -> bool:
        """
        Check if a file with the given file_path exists in the bucket with the given bucket_name.

        Args:
            bucket_name (str): The name of the S3 bucket.
            file_path (str): The path of the file to check.

        Returns:
            bool: True if the file exists in the bucket, False otherwise.
        """
        try:
            response = self._s3.list_objects_v2(
                Bucket=self._bucket_name, Prefix=file_path
            )
            for obj in response.get("Contents", []):
                if obj["Key"] == file_path:
                    return True
            return False
        except Exception as e:
            logging.error(
                f"Error occurred while checking if file {file_path} exists in bucket {self._bucket_name}. Error: {e}"
            )
            return False

    def create_bucket(self):
        # check whether the bucket name is in the valid format
        valid_bucket_name = self._check_valid_bucket_name()
        if valid_bucket_name:
            try:
                logging.info(f"Creating bucket {self._bucket_name}")
                self._s3.create_bucket(
                    Bucket=self._bucket_name,
                )
                logging.info(f"Created bucket {self._bucket_name}")
                # self._s3.put_object(Bucket=self._bucket_name, Key= f'{self._global_model_root_folder}/')

            except Exception as e:
                if "BucketAlreadyOwnedByYou" in str(e):
                    logging.info(f"Bucket {self._bucket_name} already exists")
                else:
                    logging.info("=" * 20)
                    logging.error(e)
                    logging.info("=" * 20)
                    sys.exit(0)

        else:
            logging.info(
                f"Bucket name {self._bucket_name} is not valid. Exit the program"
            )
            sys.exit(0)

    def _check_valid_bucket_name(self) -> bool:
        # Bucket name length should be between 3 and 63
        if len(self._bucket_name) < 3 or len(self._bucket_name) > 63:
            logging.info("Bucket name length should be between 3 and 63 characters.")
            return False

        # Bucket name should start and end with a number or lowercase letter
        if not re.match("^[a-z0-9]", self._bucket_name) or not re.match(
            ".*[a-z0-9]$", self._bucket_name
        ):
            logging.info(
                "Bucket name should start and end with a lowercase letter or number."
            )
            return False

        # Bucket name should not contain underscore, double dots, dash next to dots,
        # end with a dash, start with 'xn--', end with '-s3alias' or '--ol-s3'.
        if re.search(
            r"_|\.\.|\-$|\-\.|\.\-|^xn--|\-s3alias$|--ol-s3$", self._bucket_name
        ):
            logging.info(
                "Bucket name should not contain underscore, double dots, dash next to dots, end with a dash, start with 'xn--', end with '-s3alias' or '--ol-s3'."
            )
            return False

        # Bucket name should not be in IP format
        if re.match(r"\d+\.\d+\.\d+\.\d+", self._bucket_name):
            logging.info("Bucket name should not be in IP format.")
            return False

        return True
