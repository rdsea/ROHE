
import os
import json
import tensorflow as tf
import numpy as np
from app.object_classification.lib.roheMLAgent import RoheMLAgent
import sys, os
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)

import app.object_classification.modules.utils as pipeline_utils

class ObjectClassificationAgent(RoheMLAgent):
    def __init__(self, load_model_params: dict, model_id: str,
                 input_shape: tuple = (32, 32, 3), 
                 log_level: int = 2, load_model_from_file_mode = True):
        
        self.load_model_from_file_mode = load_model_from_file_mode
        if type(input_shape) == str:
            input_shape = pipeline_utils.convert_str_to_tuple(input_shape)
            
        self.load_model_params: dict = self._structure_load_model_params(load_model_params)
        
        super() .__init__(load_model_params= self.load_model_params, model_id= model_id,
                          input_shape= input_shape, log_level= log_level)
        

    def load_model(self, load_model_params):
        files = load_model_params[self.model_id]['files']
        if self.load_model_from_file_mode:
            model = self._load_model_from_file(**files)
            return model
        else:
            raise ValueError("Now, only support load model from config files, not support loading model defined from code.")
        

    
    def predict(self, image: np.ndarray) -> dict:
        try:
            result = self._construct_prediction_result(image= image)
            return result
        except:
            try:
                image = image[np.newaxis, ...]  # Add a batch dimension
                result = self._construct_prediction_result(image= image)
            except:
                result = None

            return result
    
    def _construct_prediction_result(self, image: np.ndarray) -> dict:
        prediction: np.ndarray = self.model.predict(image)
        predicted_class_index: int = np.argmax(prediction)
        confidence_level: float = prediction[0, predicted_class_index]
        result = {"class": int(predicted_class_index), 
                "confidence_level": float(confidence_level), 
                "prediction": prediction.tolist()[0]}
        return result

    def get_weights(self):
        return self.model.get_weights()

    def set_weights(self, weights_array: np.ndarray):
        self.model.set_weights(weights_array)

    def load_weights(self, file_path: str):
        self.model.load_weights(file_path)
    

    def load_model_metadata(self, model_metadata: dict):
        metadata = {}
        if model_metadata:
            # load all the model metadata in the provided info
            for attribute, value in model_metadata.items():
                metadata[attribute] = value
        metadata["no_layer"] = len(self.model.layers)
        metadata["no_parameters"] = self.model.count_params()
        return metadata


    def get_model_system_files(self, model_id: str) -> dict:
        '''
        return model system file for the given model id
        '''
        return self.load_model_params[model_id]['files']


    def _structure_load_model_params(self, load_model_params: dict) -> dict:
        # print(f"\n\n\n This is input of load model params: {load_model_params}")
        model_params = {}
        # Extract necessary information
        # files_name = load_model_params.get('files_name', {})
        # architecture_file = files_name.get('architecture_file', '')
        # weights_file = files_name.get('weights_file', '')
        architecture_file = load_model_params['architecture_file']
        weights_file = load_model_params['weights_file']
        models = ROHE_PATH+load_model_params['model_directories']
        
        # construct full system path for each model
        for model_id, folder in models.items():
            # folder = info.get('folder', '')
            model_params[model_id] = {
                'files': {
                    'architecture_file': os.path.join(folder, architecture_file),
                    'weights_file': os.path.join(folder, weights_file)
                }
            }


        return model_params
    
        
    def _load_model_from_file(self, architecture_file, weights_file):
        '''
        
        '''
        with open(architecture_file, 'r') as f:
            model_architecture = json.load(f)
            model: tf.keras.Model = tf.keras.models.model_from_config(model_architecture)
            model.load_weights(weights_file)
        return model