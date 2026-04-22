import importlib

from rohe.common.data_models import OrchestrateAlgorithmConfig
from rohe.common.rohe_enum import OrchestrateAlgorithmEnum
from rohe.orchestration.allocation.algorithms.generic import GenericAlgorithm
from rohe.orchestration.resource_management import Node, Service


class AlgorithmManager:
    def __init__(
        self,
        orchestrate_algorithm_config: OrchestrateAlgorithmConfig,
    ):
        """
        algorithm: default to priority
        """
        self.config = orchestrate_algorithm_config
        self.__current_algorithm: GenericAlgorithm | None = None
        self.load_algorithm(orchestrate_algorithm_config.algorithm)

    def load_algorithm(self, algorithm: OrchestrateAlgorithmEnum):
        if algorithm == OrchestrateAlgorithmEnum.priority:
            priority_module = importlib.import_module(
                "rohe.orchestration.allocation.algorithms.priority"
            )
            self.__current_algorithm = priority_module.PriorityAlgorithm()
        else:
            raise ValueError(f"{algorithm} hasn't been implemented")

    def find_allocate(
        self,
        p_service: Service,
        nodes: dict[str, Node],
    ) -> str | None:
        if self.__current_algorithm is None:
            raise RuntimeError("No algorithm is currently loaded")
        return self.__current_algorithm.find_allocate(p_service, nodes, self.config)

    def find_deallocate(
        self,
        p_service: Service,
        nodes: dict[str, Node],
    ):
        pass
