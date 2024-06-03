from enum import Enum
from typing import Dict, List

from pydantic import BaseModel


class StatusEnum(str, Enum):
    running = "running"
    queueing = "queueing"


class SensitivityEnum(int, Enum):
    not_sensitive = 0
    cpu_sensitive = 1
    memory_sensitive = 2
    cpu_memory_sensitive = 3


class NodeResources(BaseModel):
    capacity: List[float] | Dict | float
    used: List[float] | Dict | float


class AcceleratorResource(BaseModel):
    mode: str
    accelerator_type: str
    core: int
    capacity: float
    used: float


class NodeData(BaseModel):
    node_name: str
    mac_address: str
    status: StatusEnum
    frequency: float
    accelerator: Dict[str, AcceleratorResource]
    cpu: NodeResources
    memory: NodeResources
    cores: NodeResources


class ServiceData(BaseModel):
    service_name: str
    service_id: str
    node: Dict
    status: StatusEnum
    instance_ids: List
    running: bool
    # NOTE: why this should be a list
    ports: List
    port_mapping: List[Dict]
    cpu_required: int
    accelerator_required: Dict
    memory_required: Dict
    cores: List
    sensitivity: SensitivityEnum
    replicas: int


class AddNodeRequest(BaseModel):
    data: Dict[str, NodeData]


class AddServiceRequest(BaseModel):
    data: Dict[str, Dict[str, ServiceData]]
