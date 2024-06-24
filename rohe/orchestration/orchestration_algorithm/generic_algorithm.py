from abc import ABC, abstractmethod
from typing import Dict

from ...common.data_models import OrchestrateAlgorithmConfig
from ..resource_management import Node, Service, ServiceQueue


class GenericAlgorithm(ABC):
    @abstractmethod
    def calculate(
        self,
        nodes: Dict[str, Node],
        services: Dict[str, Service],
        service_queue: ServiceQueue,
        config: OrchestrateAlgorithmConfig,
    ):
        pass
