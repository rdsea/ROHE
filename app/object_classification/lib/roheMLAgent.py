# This file is used to define a module to manage ML model and inference

from abc import ABC, abstractmethod
from .roheObject import RoheObject
import tensorflow as tf

import numpy as np

class RoheMLAgent(RoheObject, ABC):
    '''
    '''
    def __init__(self, model_info: dict, input_shape: tuple, log_level= 2):
        super() .__init__(logging_level= log_level)
        self.input_shape = input_shape
        self.model: tf.keras.Model = self.load_init_model(model_info= model_info)


    @abstractmethod
    def load_init_model(self, model_info) -> tf.keras.Model:
        pass
        
    @abstractmethod
    def change_model(self, new_model) -> bool:
        pass
    
    @abstractmethod
    def predict(self, image) -> dict:
        '''
        return a dictionary as the result of the prediction can be vary 
        depend on the nature of task (classification, regression,etc) 
        and specific use case 
        '''
        pass

    @abstractmethod
    def get_weights(self) -> list:
        pass

    @abstractmethod
    def set_weights(self, weights_array: np.ndarray) -> bool:
        '''
        set weights for ML model from numpy array
        '''
        pass

    @abstractmethod
    def load_weights(self, file_path: str) -> bool:
        '''
        set weight for ML model from a file path (this file store a numpy array)
        '''
        pass
