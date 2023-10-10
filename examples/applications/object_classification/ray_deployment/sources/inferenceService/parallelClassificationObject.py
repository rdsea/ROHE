import ray
from lib.modules.object_classification.classificationObject import ClassificationObjectV1
import numpy as np

@ray.remote
class ParallelClassificationObjectV1(ClassificationObjectV1):
    def __init__(self, model_config: dict, model_files: dict, input_shape: tuple = (32, 32, 3), log_level: int = 2):
        super().__init__(model_config=model_config, input_shape=input_shape, log_level=log_level)
        self.model = self.load_init_model(model_files)

    def distributed_predict(self, image: np.ndarray) -> dict:
        return self.predict(image)
    
    def distributed_get_model_metadata(self) -> dict:
        return self.get_model_metadata()

    def set_weights(self, weights_array):
        self.set_weights(weights_array)

    def get_weights(self):
        return self.get_weights()
        
    def load_weights(self, weights_file):
        self.load_weights(weights_file)


