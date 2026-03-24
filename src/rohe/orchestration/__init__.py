"""Orchestration module.

Provides inference orchestration (v2) and resource allocation.
Legacy orchestrators archived in _v1_archive/orchestration/.
"""
from __future__ import annotations

ORCHESTRATOR_REGISTRY: dict[str, str] = {
    "v2": "rohe.orchestration.inference.orchestrator_v2.InferenceOrchestrator",
}
