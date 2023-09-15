
import numpy as np
from lib.roheObject import RoheObject
from examples.applications.NII.utilities.utils import get_image_dim_from_str
from examples.applications.NII.utilities.minioStorageConnector import MinioConnector

class ProcessingObject(RoheObject):
    def __init__(self, config, log_level= 2):
        super().__init__()
        self.set_logger_level(logging_level= log_level)
        self.config = config
        self.image_dim = config['image_dim']
        self.image_dim = get_image_dim_from_str(self.image_dim)
        self.width: int = int(self.image_dim[0])


    def process(self, task, minio_connector: MinioConnector) -> dict:
        # task is a dictionary contain 4 key, v pairs
        #     'request_id':
        #     'timestamp': 
        #     'device_id': 
        #     'image_url': 
        # }

        # download image from minio storage
        tmp_array_path = "./tmp_array.npy"
        success = minio_connector.download(remote_file_path= task['image_url'],
                                         local_file_path= tmp_array_path)
        if success:
            print("successfully download the image to local storage")
        # if True:
            processed_image = self._process(tmp_array_path)
            processing_result = {
                "processed_image": processed_image
            }
            return processing_result
        else:
            return None


    def _process(self, tmp_array_path) -> np.ndarray:
        # open the array
        processing_array = np.load(tmp_array_path)
        shape = processing_array.shape
        print(f"This is the shape of the image: {shape}")
        # check the dim of the array
        # if not the same as the require input shape
        # reshape it
        if shape != self.image_dim:
            print("Array needed to be reshape.")
            processing_array = self._reshape_and_pad(processing_array)
        processed_array = processing_array
        return processed_array

    def _reshape_and_pad(self, array):
        # Calculate scaling factor based on the larger dimension
        height, width, _ = array.shape
        larger_dim = max(height, width)
        scale_factor = float(self.width) / larger_dim
        
        # Resize the array while maintaining the aspect ratio
        new_height = int(height * scale_factor)
        new_width = int(width * scale_factor)
        
        resized_array = np.array([[[np.mean(array[int(i/scale_factor):int((i+1)/scale_factor),
                                                int(j/scale_factor):int((j+1)/scale_factor), :])
                                    for j in range(new_width)] 
                                for i in range(new_height)]
                                for k in range(3)]).transpose(1, 2, 0)
        
        # Calculate padding dimensions
        pad_height = self.width - new_height
        pad_width = self.width - new_width

        pad_height_before = pad_height // 2
        pad_height_after = pad_height - pad_height_before

        pad_width_before = pad_width // 2
        pad_width_after = pad_width - pad_width_before

        # Pad the array to make it square
        padded_array = np.pad(resized_array, ((pad_height_before, pad_height_after), (pad_width_before, pad_width_after), (0, 0)), 'constant')
        
        return padded_array