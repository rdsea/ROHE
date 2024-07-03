import importlib
from typing import Dict, Optional

from ...common.data_models import OrchestrateAlgorithmConfig
from ...common.rohe_enum import OrchestrateAlgorithmEnum
from ..resource_management import Node, Service
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
            priority_module = importlib.import_module(
                "rohe.orchestration.orchestration_algorithm.priority"
            )
            self.__current_algorithm = priority_module.PriorityAlgorithm()
        else:
            raise ValueError(f"{algorithm} hasn't been implemented")

    def find_allocate(
        self,
        p_service: Service,
        nodes: Dict[str, Node],
    ) -> Optional[str]:
        if self.__current_algorithm is None:
            raise RuntimeError("No algorithm is currently loaded")
        return self.__current_algorithm.find_allocate(p_service, nodes, self.config)

    def find_deallocate(
        self,
        p_service: Service,
        nodes: Dict[str, Node],
    ):
        pass
