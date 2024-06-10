from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel


class StatusEnum(str, Enum):
    running = "running"
    queueing = "queueing"


class SensitivityEnum(int, Enum):
    not_sensitive = 0
    cpu_sensitive = 1
    memory_sensitive = 2
    cpu_memory_sensitive = 3


class MemoryNodeResources(BaseModel):
    capacity: Dict
    used: Dict


class CpuNodeResources(BaseModel):
    capacity: float
    used: float


class CoresNodeResources(BaseModel):
    capacity: List[float]
    used: List[float]


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
    cpu: CpuNodeResources
    memory: MemoryNodeResources
    cores: CoresNodeResources
    services: Optional[Dict] = None


class ServiceData(BaseModel):
    service_name: str
    service_id: str
    node: Dict
    status: StatusEnum
    instance_ids: List
    running: int
    image: str
    # NOTE: why this should be a list
    ports: List
    port_mapping: List[Dict]
    cpu_required: int
    accelerator_required: Dict
    memory_required: Dict
    cores_required: List
    sensitivity: SensitivityEnum
    replicas: int


class AddNodeRequest(BaseModel):
    data: Dict[str, NodeData]


class NodeAddress(BaseModel):
    mac_address: str


class RemoveNodeRequest(BaseModel):
    data: Dict[str, NodeAddress]


class AddServiceRequest(BaseModel):
    data: Dict[str, Dict[str, ServiceData]]


class RegistrationRequest(BaseModel):
    application_name: str
    run_id: str
    user_id: str
    stage_id: Optional[str] = None
    instance_id: Optional[str] = None


class AgentMangerRequest(BaseModel):
    application_name: str
    agent_image: Optional[str] = None
    stream_config: Optional[Dict] = None
