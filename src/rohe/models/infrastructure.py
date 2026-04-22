from __future__ import annotations

from pydantic import BaseModel, Field

from .common import SensitivityEnum, StatusEnum


class MemoryNodeResources(BaseModel):
    capacity: dict[str, float]
    used: dict[str, float]


class CpuNodeResources(BaseModel):
    capacity: float
    used: float


class CoresNodeResources(BaseModel):
    capacity: list[float]
    used: list[float]


class AcceleratorResource(BaseModel):
    mode: str
    accelerator_type: str
    core: int
    capacity: float
    used: float


class NodeData(BaseModel):
    node_name: str = Field(..., pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    mac_address: str
    status: StatusEnum
    frequency: float
    accelerator: dict[str, AcceleratorResource]
    cpu: CpuNodeResources
    memory: MemoryNodeResources
    cores: CoresNodeResources
    services: dict[str, list[str]] | None = None


class PortMapping(BaseModel):
    con_port: int
    phy_port: int


class ServiceData(BaseModel):
    service_name: str
    service_id: str
    node: dict[str, str]
    status: StatusEnum
    instance_ids: list[str]
    running: int
    image: str
    ports: list[int]
    port_mapping: list[PortMapping]
    cpu_required: int
    accelerator_required: dict[str, int]
    memory_required: dict[str, float]
    cores_required: list[float]
    sensitivity: SensitivityEnum
    replicas: int


class MongoAuthentication(BaseModel):
    url: str
    prefix: str
    username: str
    password: str


class MongoCollection(BaseModel):
    collection: str
    database: str


class StorageInfo(BaseModel):
    endpoint_url: str
    access_key: str = ""
    secret_key: str = ""
    bucket_name: str = ""


class ServiceQueueConfig(BaseModel):
    priority: int
    queue_balance: int


class OrchestrateAlgorithmConfig(BaseModel):
    algorithm: str
    weights: dict[str, int]
    strategy: int


class OrchestrationServiceConfig(BaseModel):
    db_authentication: MongoAuthentication
    db_node_collection: MongoCollection
    db_service_collection: MongoCollection
    orchestration_interval: float
    output_folder: str
    service_queue_config: ServiceQueueConfig
    orchestrate_algorithm_config: OrchestrateAlgorithmConfig


class AddNodeRequest(BaseModel):
    data: dict[str, NodeData]


class NodeAddress(BaseModel):
    mac_address: str


class RemoveNodeRequest(BaseModel):
    data: dict[str, NodeAddress]


class AddServiceRequest(BaseModel):
    data: dict[str, dict[str, ServiceData]]


class RegistrationRequest(BaseModel):
    application_name: str
    run_id: str
    user_id: str
    stage_id: str | None = None
    instance_id: str | None = None


class AgentManagerRequest(BaseModel):
    application_name: str
    agent_image: str | None = None
    stream_config: dict[str, str] | None = None
