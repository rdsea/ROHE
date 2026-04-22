"""Shared enumerations for the orchestration domain."""

from __future__ import annotations

from enum import Enum


class TaskStatus(str, Enum):
    """Status of an inference task within a pipeline execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    FAILED = "failed"
    DROPPED = "dropped"


class CommonMetric(str, Enum):
    """Standard metric names used in SLA evaluation."""

    RESPONSE_TIME = "response_time"
    ACCURACY = "accuracy"
    LATENCY = "latency"
    THROUGHPUT = "throughput"


class InstanceStatus(str, Enum):
    """Status of a running inference service instance."""

    AVAILABLE = "available"
    FAILURE = "failure"
    CONTENTION = "contention"
    INACTIVE = "inactive"


class Explainability(str, Enum):
    """Whether explainability is requested for inference."""

    DISABLED = "normal"
    ENABLED = "explainability"
