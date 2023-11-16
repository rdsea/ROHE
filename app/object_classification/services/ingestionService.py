from flask import request
import requests
import json
import uuid
import random
import string


from app.object_classification.lib.roheService import RoheRestObject
from app.object_classification.lib.connectors.storage.minioStorageConnector import MinioConnector
import app.object_classification.modules.utils as pipeline_utils



class IngestionService(RoheRestObject):
    def __init__(self, **kwargs):
        super().__init__()
        # to get configuration for resource
        configuration = kwargs
        self.conf = configuration
        log_lev = self.conf.get('log_lev', 2)
        self.set_logger_level(logging_level= log_lev)

        self.minio_connector: MinioConnector = self.conf['minio_connector']
        self.image_info_service_url: str = self.conf['image_info_server']['endpoint_url']

    def get(self):
        """
        return message to client to notify them that they are accessing the correct ingestion server
        """
        response = "Welcome to Ingestion Server of Object Classification pipeline. You can send either numpy array or imag. Accepted format are [npy, jpg, jpeg, png, webp]"
        return json.dumps({"response": response}), 200, {'Content-Type': 'application/json'}


    def post(self):
        """
        Handles POST requests to send image/ numpy array from client

        Sample request
            # Prepare the data to send
            data = {
                'timestamp': '2023-11-07T12:00:00Z',
                'device_id': 'device123',
                'image_extension': 'npy',
                'shape': ','.join(map(str, array_data.shape)),  # Example: '100,100,3'
                'dtype': str(array_data.dtype)  # Example: 'uint8'
            }

            # Prepare the files to send
            files = {
                'image': ('image.npy', image_bytes, 'application/octet-stream')
            }

            # Send the POST request
            response = requests.post(ingestion_service_url, data=data, files=files)

        :return: JSON response indicating the status of the command or an error message.
        """

        # Retrieve the metadata from the form-data
        timestamp = request.form.get('timestamp')
        device_id = request.form.get('device_id')
        image_extension = request.form.get('image_extension')

        if not image_extension:
            return json.dumps({"message": "No image type provided. cannot further process"}), 400

        # check whether the file format is supported 
        # if ingestion_func.validate_image_extension(image_extension):
        if self._validate_image_extension(image_extension):
            binary_file = request.files.get('image')
            if binary_file is None:
                return json.dumps({'message': 'No image provided'}), 400

            # upload image to minio storage
            # generate request id
            # request_id = ingestion_func.generate_request_id()
            request_id = self._generate_request_id()
            # create remote file path to save in minio server
            try:
                # use the datetime the request provided
                # if any problem, use the current datetime
                date_str = pipeline_utils.convert_str_to_datetime(str_time=timestamp, option= 'date_only')
            except:
                date_str = pipeline_utils.get_current_utc_timestamp(option='date_only')

            remote_filename = f"{device_id}/{str(date_str)}/{request_id}.{image_extension}"
            upload_success = self.minio_connector.upload_binary_data(binary_data= binary_file, remote_file_path= remote_filename)

            # send request info to image info service
            if not upload_success:
                response = "Error in uploading image to Storage Server."
                return json.dumps({"response": response}), 400

            else:
                # if the image is an array, 
                # # need to have info about dtype and shape to retrieve the image
                if image_extension == "npy":
                    dtype = request.form.get('dtype')
                    shape = request.form.get('shape')
                else:
                    dtype = None
                    shape = None

                # Prepare the payload for Image Info service
                payload = {
                    "command": "add",
                    "request_id": request_id,
                    "timestamp": pipeline_utils.get_current_utc_timestamp(),
                    "device_id": device_id,
                    'image_url': remote_filename,
                    'dtype': dtype,
                    'shape': shape,
                }

                print(f"This is the payload: {payload}")

                # upload request info to Image Info Service
                response = requests.post(self.image_info_service_url, data=payload)
                if response.status_code == 200:
                    print(f"\nSuccessfully upload request {request_id} to Image Info Service")
                    # return True
                    response = f"Successfully forward the request to the next step. Request id: {request_id}"
                    return json.dumps({"response": response}), 200, {'Content-Type': 'application/json'}
                else:
                    print(f"\n\nThis is the response from image info server: {response.json()}")
                    message = f"Failed to upload request {request_id} to Image Info Service"
                    print(message)
                    # return False
                    return json.dumps({"response": message}), 400



    def _validate_image_extension(self, file_extension, supported_extensions: list = None):
        if not supported_extensions:
            supported_extensions = ['npy', 'jpg', 'jpeg', 'png', 'webp']
        # print("This is supported extension: ")
        return file_extension.lower() in supported_extensions

    def _generate_request_id(self) -> str:
        # Get current date and time in the specified format
        date_str = pipeline_utils.get_current_utc_timestamp()
        # Generate a random UUID4
        uuid_str = str(uuid.uuid4())
        # Generate additional random string of 16 characters
        additional_str = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        # Combine them to create the request_id
        request_id = f"{date_str}-{uuid_str}-{additional_str}"
        return request_id


