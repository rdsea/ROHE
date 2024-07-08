from abc import ABC, abstractmethod

from ...common import rohe_utils
from . import algorithm


class EnsembleOptimization(ABC):
    """
    Abstract class for ensemble optimization of services in EEMLS
    Init the class using ofConfig: configuration include name and module to load the objective function
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
    def get_ml_service_performance(
        self,
        database,
        model_collection: str,
        infrastructure_collection: str,
        model_cost_collection: str,
        infrastructure_cost_collection: str,
        metric_config: dict,
        timestamp=None,
        limit=10000,
    ) -> list:
        """Return list of ML services (deployments of specific ML models on specific infrastructures) with their performance"""
        return []

    @abstractmethod
    def select(self, ml_service_list: list, contract: dict) -> list:
        "From list of ML services return optimal ensemble of ML services using the objective function (self.objective_function)"
        return []
