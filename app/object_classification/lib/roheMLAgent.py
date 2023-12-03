# This file is used to define a module to manage ML model and inference

from abc import ABC, abstractmethod
from lib.rohe.roheObject import RoheObject

import tensorflow as tf

import numpy as np

class RoheMLAgent(RoheObject, ABC):
    '''
    Abstract base class for managing machine learning models, particularly those using TensorFlow and Keras. 
    It provides a framework for loading models, changing model parameters, and making predictions. The class 
    is designed to be flexible, supporting different model loading scenarios, including models defined in 
    JSON files or directly in code.

    Attributes:
        input_shape (tuple): The shape of the input data expected by the model.
        model_id (str): id of model, for service management.
        model (e.g: tf.keras.Model): The current TensorFlow/Keras model.
        model_metadata (dict, optional): Dictionary to store additional information about the model

    Args:
        load_model_params (dict): Information required to load the model, varying based on the model's framework and definition.
        model_id: id of the model
        input_shape (tuple): The expected shape of the model's input data.
        log_level (int, optional): The logging level for the underlying RoheObject.
        model_metadata (dict, optional): A dictionary containing metadata about the model.
    '''

    def __init__(self, load_model_params: dict, model_id: str,
                 input_shape: tuple, log_level: int= 2,
                 model_metadata: dict = None):

        super() .__init__(logging_level= log_level)
        self.input_shape: tuple = input_shape
        self.model_id: str = model_id
        self.model: tf.keras.Model = self.load_model(load_model_params)
        self.model_meta_data: dict = self.load_model_metadata(model_metadata)


    @abstractmethod
    def load_model(self, load_model_params: dict) -> tf.keras.Model:
        '''
        Load a machine learning model based on the provided information. The load_model_params parameter is flexible 
        to accommodate different frameworks and scenarios. 

        E.g: For models defined in JSON, load_model_params could include paths to the model's architecture file (json) 
        and its weights file. For models defined directly in code, load_model_params typically requires the weights 
        file path and may include additional parameters necessary for model construction.

        input:
            load_model_params: A dictionary or other data structure containing all necessary information to load the model. 
                        The exact contents will vary depending on the model's framework and definition method.

        output:
            A model object.
        '''
        pass

        
    def change_model(self, new_model: tf.keras.Model) -> bool:
        '''
        change the current ML model to a new one
        '''
        try:
            self.model = new_model
            return True
        except:
            return False


    @abstractmethod
    def predict(self, image: np.ndarray) -> dict:
        '''
        return a dictionary, as the result of the prediction can be vary 
        depend on the nature of task (classification, regression,etc) 
        and specific use case 
        '''
        pass

    @abstractmethod
    def get_weights(self) -> np.ndarray:
        '''
        output: the current weights of the ML model.
        It can be a list of numpy array or a numpy array
        '''
        pass

    @abstractmethod
    def set_weights(self, weights_array: np.ndarray) -> bool:
        '''
        set weights for ML model from list of numpy array or a numpy array
        '''
        pass

    @abstractmethod
    def load_weights(self, file_path: str) -> np.ndarray:
        '''
        input: a system file path (it can be a .h5 file for keras model)
        output: a list of numpy array or a numpy array
        '''
        pass
    
    @abstractmethod
    def load_model_metadata(self, model_metadat) -> dict:
        '''
        return a dictionary store meta data info of the model
        varies on specific used case
        '''
        pass

    def get_model_metadata(self) -> dict:
        return self.model_meta_data
    
    def get_model_id(self) -> str:
        return self.model_id
    
    def change_model_id(self, new_model_id) -> bool:
        try:
            self.model_id = new_model_id
            return True
        except:
            return False
        
    def get_input_shape(self) -> tuple:
        return self.input_shape
        
    def change_input_shape(self, new_input_shape: tuple) -> bool:
        '''
        change the current input shape to a new one
        be careful when using this function as each model architecture may work with a specific set o input shape only
        '''
        try:
            self.input_shape = new_input_shape
            return True
        except:
            return False