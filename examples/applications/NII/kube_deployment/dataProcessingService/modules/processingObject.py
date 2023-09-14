
import numpy as np
from lib import RoheObject
from examples.applications.NII.utilities.utils import get_image_dim_from_str
from examples.applications.NII.utilities.minioStorageConnector import MinioConnector

class ProcessingObject(RoheObject):
    def __init__(self, config, log_level= 2):
        super().__init__()
        self.set_logger_level(logging_level= log_level)
        self.config = config
        self.image_dim = config['image_dim']
        self.image_dim = get_image_dim_from_str(self.image_dim)

    def process(self, task, minio_connector: MinioConnector) -> dict:
        # task is a dictionary contain 4 key, v pairs
        #     'request_id':
        #     'timestamp': 
        #     'device_id': 
        #     'image_url': 
        # }

        # # download image from minio storage
        # tmp_array = "./tmp_array.npy"
        # success = minio_connector.download(remote_file_path= task['image_url'],
        #                                  local_file_path= tmp_array)
        # if success:
        if True:
            processed_image = self._process(task)
            processing_result = {
                "processed_image": processed_image
            }
            return processing_result
        else:
            return None


    def _process(self, task) -> np.ndarray:
        return np.zeros(shape= self.image_dim)