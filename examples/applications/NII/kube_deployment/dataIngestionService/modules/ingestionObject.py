import os

import numpy as np

import base64
# import gzip
import datetime
import string
import random
import uuid
from PIL import Image

from lib import RoheObject
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

    def save_to_minio(self, minio_connector: MinioConnector, payload: dict) -> str:
        print("About to upload to minio storage.")
        # save the image in numpy format locally
        # random_string = self._generate_random_string()
        file_name = f"{payload['request_id']}.{self.file_extension}"
        local_file_path = os.path.join(self.tmp_image_folder, file_name)
        print(f"local file path: {local_file_path}")
        self._save_numpy_array(payload['image'], local_file_path)

        print(f"after saving to local file path")

        # upload to the cloud storage
        # remote_file_path = f"{payload['device_id']}_{payload['timestampt']}_{random_string}.{self.file_extension}"
        date_str = datetime.datetime.utcnow().strftime('%d-%m-%y')
        remote_file_path = f"{payload['device_id']}/{str(date_str)}/{file_name}"
        print(f"This is the remote file path: {remote_file_path}")
        success = minio_connector.upload(local_file_path= local_file_path,
                                    remote_file_path= remote_file_path)
        # after uploading to the cloud storage, erase the temp file
        os.remove(local_file_path)
        if not success:
            remote_file_path = None
        return remote_file_path

    def ingest(self, payload: dict) -> dict:
        # payload template = {
        #     'timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        #     'device_id': "camera01",
        #     'image': image_b64,
        #     'file_extension': file_extension,
        #     'shape': None,
        #     'dtype': None,
        # }
        file_extension = payload['file_extension']
        print(f"\n\n Received the payload from ingestion service")
        # print("\n\nthis is for loading the payload")
        for k, v in payload.items():
            print(f"This is the key: {k}")
        print("\n\n")

        print(f"this is the file extension: {file_extension}")
        if file_extension == 'npy':
            numpy_image = self._reconstrucre_image_from_array(payload)
        else:
            print("Load from file...")
            numpy_image = self._reconstrucre_image_from_file(payload)

        print("succesffuly receive the numpy image")
        # create and assign an request id to the request
        request_id = self._generate_request_id()
        print(f"successfully generate the request id:{request_id}")

        result = {
            'request_id': request_id,
            'timestamp': datetime.datetime.strptime(payload['timestamp'], '%Y-%m-%dT%H:%M:%SZ'),
            'device_id': payload['device_id'],
            'image': numpy_image
        }

        # print(f"This is the result of ingestion: {result}")

        return result

    def _reconstructure_image_from_array(self, payload) -> np.ndarray:

        # Get the dimensions and type of the array
        shape = tuple(map(int, payload['shape'].strip('()').split(',')))
        dtype = np.dtype(payload['dtype'])

        print(f"{shape, dtype}")

        array_b64 = payload.get('image')
        array_bytes = base64.b64decode(array_b64)

        # Reconstruct the array from bytes
        array = np.frombuffer(array_bytes, dtype).reshape(shape)

        return array
    
    def _reconstrucre_image_from_file(self, payload) -> np.ndarray:
        print("Enter inside the function")
        # Get the dimensions and type of the array
        # shape = tuple(map(int, payload['shape'].strip('()').split(',')))
        shape = payload['shape']
        dtype = np.dtype(payload['dtype'])

        print(f"{shape, dtype}")

        image_b64 = payload.get('image')
        image_data = base64.b64decode(image_b64)
        
        # Save to a temporary file
        file_extension = payload.get('file_extension')
        print(f"This is the file extension: {file_extension}")

        with open(f"temp.{file_extension}", "wb") as image_file:
            image_file.write(image_data)

        # Open the image with PIL and convert to NumPy array
        with Image.open(f"temp.{file_extension}") as img:
            image_np = np.array(img)

        print(f"This is the image numpy shape: {image_np.shape}")

        return image_np


    def _generate_request_id(self) -> str:
        # Get current date and time in the specified format
        # date_str = datetime.datetime.utcnow().strftime('%d-%m-%y-%H-%M-%S-%f')
        date_str = datetime.datetime.utcnow().strftime('%d-%m-%y')

        # Generate a random UUID4
        uuid_str = str(uuid.uuid4())
        
        # Generate additional random string of 16 characters
        additional_str = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        
        # Combine them to create the request_id
        request_id = f"{date_str}-{uuid_str}-{additional_str}"
        
        return request_id

    # def _decompress(self, compressed_data):
    #     return gzip.decompress(compressed_data)
    
    # def _generate_random_string(length= 6):
    #     letters = string.ascii_letters + string.digits  # includes both letters and numbers
    #     return ''.join(random.choice(letters) for i in range(length))

    def _save_numpy_array(self, arr, file_path):
        """
        Saves a numpy array to a file at the specified file path.
        """
        np.save(file_path, arr)