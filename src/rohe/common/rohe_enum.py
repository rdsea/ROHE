from enum import Enum


class StatusEnum(str, Enum):
    running = "running"
    queueing = "queueing"


class SensitivityEnum(int, Enum):
    not_sensitive = 0
    cpu_sensitive = 1
    memory_sensitive = 2
    cpu_memory_sensitive = 3


class OrchestrateAlgorithmEnum(str, Enum):
    priority = "priority"
