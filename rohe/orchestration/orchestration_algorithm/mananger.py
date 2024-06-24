import importlib
from typing import Dict, Optional

from ...common.data_models import OrchestrateAlgorithmConfig
from ...common.rohe_enum import OrchestrateAlgorithmEnum
from ..resource_management import Node, Service, ServiceQueue
from .generic_algorithm import GenericAlgorithm


class AlgorithmManager:
    def __init__(
        self,
        orchestrate_algorithm_config: OrchestrateAlgorithmConfig,
    ):
        """
        algorithm: default to priority
        """
        self.config = orchestrate_algorithm_config
        self.__current_algorithm: Optional[GenericAlgorithm] = None
        self.load_algorithm(orchestrate_algorithm_config.algorithm)

    def load_algorithm(self, algorithm: OrchestrateAlgorithmEnum):
        if algorithm == OrchestrateAlgorithmEnum.priority:
            priority_module = importlib.import_module(".priority", package=__name__)
            self.__current_algorithm = priority_module.PriorityAlgorithm()
        else:
            raise ValueError(f"{algorithm} hasn't been implemented")

    def calculate(
        self,
        nodes: Dict[str, Node],
        services: Dict[str, Service],
        service_queue: ServiceQueue,
    ):
        if self.__current_algorithm is None:
            raise RuntimeError("No algorithm is currently loaded")
        return self.__current_algorithm.calculate(
            nodes, services, service_queue, self.config
        )
