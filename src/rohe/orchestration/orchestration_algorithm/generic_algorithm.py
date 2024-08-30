from abc import ABC, abstractmethod
from typing import Dict, Optional

from ...common.data_models import OrchestrateAlgorithmConfig
from ..resource_management import Node, Service


class GenericAlgorithm(ABC):
    @abstractmethod
    def find_allocate(
        self,
        p_service: Service,
        nodes: Dict[str, Node],
        config: OrchestrateAlgorithmConfig,
    ) -> Optional[str]:
        pass

    @abstractmethod
    def find_deallocate(
        self,
        p_service: Service,
        nodes: Dict[str, Node],
        config: OrchestrateAlgorithmConfig,
    ) -> Optional[str]:
        pass
