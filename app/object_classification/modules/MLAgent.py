
import os
import json
import tensorflow as tf
import numpy as np
from app.object_classification.lib.roheMLAgent import RoheMLAgent

import app.object_classification.modules.utils as pipeline_utils

class ObjectClassificationAgent(RoheMLAgent):
    def __init__(self, model_info: dict, input_shape: tuple = (32, 32, 3), 
                 log_level: int = 2, model_from_config = True):
        
        if type(input_shape) == str:
            input_shape = pipeline_utils.convert_str_to_tuple(input_shape)
            
        self.model_from_config = model_from_config
        self.current_model_id: str = model_info['chosen_model_id']
        
        super() .__init__(model_info= model_info, input_shape= input_shape, log_level= log_level)
        
        
    def load_model_info(self, model_info) -> dict:
        new_dict = {}
        # Extract necessary information
        files_name = model_info.get('files_name', {})
        architecture_file = files_name.get('architecture_file', '')
        weights_file = files_name.get('weights_file', '')
        models = model_info.get('models', {})
        
        # Construct the new dictionary
        for model_id, model_info in models.items():
            folder = model_info.get('folder', '')
            new_dict[model_id] = {
                'files': {
                    'architecture_file': os.path.join(folder, architecture_file),
                    'weights_file': os.path.join(folder, weights_file)
                }
            }

        return new_dict

    def get_model_files(self, model_id: str) -> dict:
        return self.model_info[model_id]['files']
    
    def set_model_id(self, model_id):
        self.current_model_id = model_id

    def get_model_id(self):
        return self.current_model_id
        
    def load_init_model(self, model_info):
        self.model_info: dict = self.load_model_info(model_info= model_info)

        print(f"This is the loaded model info: {self.model_info}")

        files = self.model_info[self.current_model_id]['files']
        if self.model_from_config:
            model = self.load_model_from_config(**files)
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
            predicted_class_index, confidence_level, prediction = self._predict(image)
            result = {"class": int(predicted_class_index), 
                    "confidence_level": float(confidence_level), 
                    "prediction": prediction.tolist()[0]}
        except:
            # predicted_class_index = -1
            # confidence_level = -1
            # prediction = None
            result = None

        return result
    
    def _predict(self, image: np.ndarray):
        prediction: np.ndarray = self.model.predict(image)
        predicted_class_index: int = np.argmax(prediction)
        confidence_level: float = prediction[0, predicted_class_index]
        # prediction = prediction.tolist()
        return predicted_class_index, confidence_level, prediction

    def get_weights(self):
        return self.model.get_weights()

    def set_weights(self, weights_array: np.ndarray):
        self.model.set_weights(weights_array)

    def load_weights(self, file_path: str):
        self.model.load_weights(file_path)
    
    def get_model_metadata(self):
        metadata = {}
        metadata["no_layer"] = len(self.model.layers)
        metadata["no_parameters"] = self.model.count_params()
        return(metadata)

