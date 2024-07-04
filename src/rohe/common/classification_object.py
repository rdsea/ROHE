# This file is used to define a module to manage ML model and inference

from abc import ABC, abstractmethod

import tensorflow as tf

from .logger import logger


class ClassificationObject(ABC):
    def __init__(self, model_info: dict, input_shape: tuple):
        self.logger = logger

        self.input_shape = input_shape
        self.model: tf.keras.Model = self.load_init_model(model_info=model_info)

    @abstractmethod
    def load_init_model(self, model_info) -> tf.keras.Model:
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
