from typing import Dict, List, Optional

from pydantic import BaseModel

from .rohe_enum import OrchestrateAlgorithmEnum, SensitivityEnum, StatusEnum


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


class PortMapping(BaseModel):
    con_port: int
    phy_port: int


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
    port_mapping: List[PortMapping]
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


class MongoAuthentication(BaseModel):
    url: str
    prefix: str
    username: str
    password: str


class MongoCollection(BaseModel):
    collection: str
    database: str


class ServiceQueueConfig(BaseModel):
    priority: int
    queue_balance: int


# TODO:custom error when algorithm name is wrong
class OrchestrateAlgorithmConfig(BaseModel):
    algorithm: OrchestrateAlgorithmEnum
    weights: Dict[str, int]
    strategy: int


class OrchestrationServiceConfig(BaseModel):
    db_authentication: MongoAuthentication
    db_node_collection: MongoCollection
    db_service_collection: MongoCollection
    orchestration_interval: float
    output_folder: str
    service_queue_config: ServiceQueueConfig
    orchestrate_algorithm_config: OrchestrateAlgorithmConfig
