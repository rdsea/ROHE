# This file is used to define a module to manage ML model and inference
import json
import tensorflow as tf
import numpy as np

from lib.roheObject import RoheObject
from examples.applications.NII.utilities.utils import get_image_dim_from_str

class ClassificationObject(RoheObject):
    def __init__(self, files, input_shape= (32, 32, 3), model_from_config= True, log_level= 2):
        super() .__init__()
        self.set_logger_level(logging_level= log_level)
        
        # now, support only loading tensorflow model from config
        self.model: tf.keras.Model = self.load_model(files= files, model_from_config= model_from_config)
        self.input_shape= input_shape
        if type(self.input_shape) == str:
            self.input_shape = get_image_dim_from_str(self.input_shape)

    def load_model(self, files, model_from_config= True):
        print("#" * 50)
        print(f"This is the files used to load new model: {files}")
        print("#" * 50)
        if model_from_config:
            model = self._load_model_from_config(**files)
            return model
        else:
            raise ValueError("Now, only support load model from config files")
        
    def _load_model_from_config(self, architecture_file, weights_file):
        print("-" * 20)
        print(architecture_file, weights_file)
        print("-" * 20)
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

        # try:
        #     predicted_class_index, confidence_level = self._predict(image)
        # except:
        #     try:
        #         image = image[np.newaxis, ...]  # Add a batch dimension
        #         predicted_class_index, confidence_level = self._predict(image)
        #     except:
        #         # some other error that didn't handle yet
        #         predicted_class_index = -1
        #         confidence_level = -1

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