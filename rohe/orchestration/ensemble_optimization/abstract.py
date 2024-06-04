from abc import ABC, abstractmethod

from ...lib import rohe_utils
from . import algorithm


class EnsembleOptimization(ABC, object):
    """
    Abstract class for ensemble optimiztion of services in EEMLS
    Init the class using ofConfig: configuration include name and module to load the objective funtion
    """

    def __init__(
        self, objective_func_name: str, model_list: list, infrastructure_list: list
    ):
        super().__init__()
        self.objective_funtion = objective_func_name
        # self.objective_funtion = rUtils.get_function_from_module(objective, objective_func_name)
        self.model_list = model_list
        self.infrastructure_list = infrastructure_list

    def update_model_list(self, model_list: list):
        self.model_list = model_list

    def update_infrastructure_list(self, infrastructure_list: list):
        self.infrastructure_list = infrastructure_list

    def set_optimization_algorithm(self, algo_name: str):
        self.optimization_algorithm = rohe_utils.get_function_from_module(
            algorithm, algo_name
        )

    @abstractmethod
    def get_ml_service_performance(self) -> dict:
        """Return list of ML services (deployments of specific ML models on specific infrastructures) with their performance"""
        return {}

    @abstractmethod
    def select(self, ml_service_list: list, contract: dict) -> dict:
        "From list of ML services return optimal ensemble of ML services using the objective function (self.objective_function)"
        return []
