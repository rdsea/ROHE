from lib import RoheObject
import numpy as np
import base64
import gzip
import datetime
import string
import random
import os

from examples.applications.NII.utilities import MinioConnector
from examples.applications.NII.utilities.utils import get_image_dim_from_str

class IngestionObject(RoheObject):
    def __init__(self, tmp_image_folder='tmp_image_folder',
                        file_extension='npy', log_level= 2):
        super() .__init__()
        self.set_logger_level(logging_level= log_level)
        self.tmp_image_folder = tmp_image_folder
        self.file_extension = file_extension

        if not os.path.isdir(self.tmp_image_folder):
            os.mkdir(self.tmp_image_folder)

    def save_to_minio(self, minio_connector: MinioConnector, payload) -> str:
        # save the image in numpy format locally
        random_string = self._generate_random_string()
        local_file_path = os.path.join(self.tmp_image_folder, f"{random_string}.{self.file_extension}")
        self._save_numpy_array(payload['image'], local_file_path)
        # upload to the cloud storage
        remote_file_path = f"{payload['device_id']}_{payload['timestampt']}_{random_string}.{self.file_extension}"

        success = minio_connector.upload(local_file_path= local_file_path,
                                    remote_file_path= remote_file_path)
        # after uploading to the cloud storage, erase the temp file
        os.remove(local_file_path)
        if not success:
            remote_file_path = None
        return remote_file_path

    def ingest(self, payload) -> dict:
        # Extract and decode the image
        image_b64 = payload.get('image', '')
        image_bytes = base64.b64decode(image_b64)

        # Get the dimensions and type of the image
        shape = get_image_dim_from_str(payload['shape'])
        
        dtype = np.dtype(payload['dtype'])
        is_compressed = payload.get('is_compressed', False)

        # Reconstruct the image from bytes
        image = np.frombuffer(image_bytes, dtype).reshape(shape)

        # If the image is compressed, decompress it
        if is_compressed:
            image = self._decompress(image)

        result = {
            'timestamp': datetime.strptime(payload['timestamp'], '%Y-%m-%dT%H:%M:%SZ'),
            'device_id': payload['device_id'],
            'image': image
        }

        return result


    def _decompress(self, compressed_data):
        return gzip.decompress(compressed_data)
    
    def _generate_random_string(length= 6):
        letters = string.ascii_letters + string.digits  # includes both letters and numbers
        return ''.join(random.choice(letters) for i in range(length))

    def _save_numpy_array(self, arr, file_path):
        """
        Saves a numpy array to a file at the specified file path.
        """
        np.save(file_path, arr)