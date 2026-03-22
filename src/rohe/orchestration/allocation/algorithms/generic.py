from abc import ABC, abstractmethod

from rohe.common.data_models import OrchestrateAlgorithmConfig
from rohe.orchestration.resource_management import Node, Service


class GenericAlgorithm(ABC):
    @abstractmethod
    def find_allocate(
        self,
        p_service: Service,
        nodes: dict[str, Node],
        config: OrchestrateAlgorithmConfig,
    ) -> str | None:
        pass

    @abstractmethod
    def find_deallocate(
        self,
        p_service: Service,
        nodes: dict[str, Node],
        config: OrchestrateAlgorithmConfig,
    ) -> str | None:
        pass
