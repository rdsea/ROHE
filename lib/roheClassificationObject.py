# This file is used to define a module to manage ML model and inference

from abc import ABC, abstractmethod
from lib.roheObject import RoheObject


class ClassificationObject(RoheObject, ABC):
    def __init__(self, model_config: dict, input_shape: tuple, log_level= 2):
        super() .__init__()
        self.set_logger_level(logging_level= log_level)
        
        self.input_shape= input_shape
        self.model = self.load_init_model(model_files= model_config)


    @abstractmethod
    def load_init_model(self, model_files):
        pass
        
    @abstractmethod
    def change_model(self, new_model) -> bool:
        pass
    
    @abstractmethod
    def predict(self, image) -> dict:
        pass

    @abstractmethod
    def get_weights(self) -> list:
        pass

    @abstractmethod
    def set_weights(self, weights_array) -> bool:
        pass

    @abstractmethod
    def load_weights(self, weights_file) -> bool:
        pass
