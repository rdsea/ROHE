
import numpy as np
from lib import RoheObject
from examples.applications.NII.utilities.utils import get_image_dim_from_str

class ProcessingObject(RoheObject):
    def __init__(self, config, log_level= 2):
        super().__init__()
        self.set_logger_level(logging_level= log_level)
        self.config = config
        self.image_dim = config['image_dim']
        self.image_dim = get_image_dim_from_str(self.image_dim)

    def process(self, task) -> dict:
        # task is a dictionary contain 3 key, v pairs
        #     'timestamp': 
        #     'device_id': 
        #     'image_url': 
        # }

        processed_image = self._process(task)
        processing_result = {
            "processed_image": processed_image
        }
        return processing_result


    def _process(self, task) -> np.ndarray:
        return np.zeros(shape= self.image_dim)