# This file is used to define a module to manage ML model and inference
import json
import tensorflow as tf
import numpy as np

from lib.roheClassificationObject import ClassificationObject


class NIIClassificationObject(ClassificationObject):
    def __init__(self, model_config: dict, input_shape: tuple = (32, 32, 3), log_level: int = 2, model_from_config = True):
        if type(input_shape) == str:
            input_shape = get_image_dim_from_str(input_shape)
        self.model_from_config = model_from_config

        super() .__init__(model_config= model_config, input_shape= input_shape, log_level= log_level)
        self.set_logger_level(logging_level= log_level)
        
        
    def load_init_model(self, model_files):
        if self.model_from_config:
            model = self.load_model_from_config(**model_files)
            return model
        else:
            raise ValueError("Now, only support load model from config files")
        
    def load_model_from_config(self, architecture_file, weights_file):
        with open(architecture_file, 'r') as f:
            model_architecture = json.load(f)
            model = tf.keras.models.model_from_config(model_architecture)
            model.load_weights(weights_file)
        return model
    

    def change_model(self, new_model):
        self.model = new_model
        return True
    
    def predict(self, image: np.ndarray) -> dict:
        try:
            image = image[np.newaxis, ...]  # Add a batch dimension
            predicted_class_index, confidence_level = self._predict(image)
        except:
            # some other error that didn't handle yet
            predicted_class_index = -1
            confidence_level = -1

#         # try:
#         #     predicted_class_index, confidence_level = self._predict(image)
#         # except:
#         #     try:
#         #         image = image[np.newaxis, ...]  # Add a batch dimension
#         #         predicted_class_index, confidence_level = self._predict(image)
#         #     except:
#         #         # some other error that didn't handle yet
#         #         predicted_class_index = -1
#         #         confidence_level = -1

        result = {"class": int(predicted_class_index), "confidence_level": float(confidence_level)}

        return result
    
    def _predict(self, image: np.ndarray):
        prediction = self.model.predict(image)
        predicted_class_index = np.argmax(prediction)
        confidence_level = prediction[0, predicted_class_index]
        return predicted_class_index, confidence_level

    def get_weights(self):
        return self.model.get_weights()

    def set_weights(self, weights_array):
        self.model.set_weights(weights_array)

    def load_weights(self, weights_file):
        self.model.load_weights(weights_file)

def get_image_dim_from_str(str_obj) -> tuple:
    return tuple(map(int, str_obj.split(',')))