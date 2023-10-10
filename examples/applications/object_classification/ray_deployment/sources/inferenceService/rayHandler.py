import ray
from parallelClassificationObject import ParallelClassificationObjectV1

class RayHandler:
    def __init__(self, ray_object_ref):
        self.ray_object_ref = ray_object_ref
        
    def async_predict(self, image):
        return ray.get(self.ray_object_ref.distributed_predict.remote(image))
    
    def async_get_model_metadata(self):
        return ray.get(self.ray_object_ref.distributed_get_model_metadata.remote())
    
    def sync_set_weights(self, weights_array):
        ray.get(self.ray_object_ref.set_weights.remote(weights_array))
        
    def sync_get_weights(self):
        return ray.get(self.ray_object_ref.get_weights.remote())
        
    def sync_load_weights(self, weights_file):
        ray.get(self.ray_object_ref.load_weights.remote(weights_file))


ray.init()  # Initialize Ray
model_config = {}
model_files = {}
input_shape = (32, 32, 3)
log_level = 2
parallel_classification_obj = ParallelClassificationObjectV1.remote(model_config=model_config, model_files=model_files, input_shape=input_shape, log_level=log_level)

handler = RayHandler(parallel_classification_obj)