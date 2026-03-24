"""Inference orchestration sub-module.

Contains both legacy orchestrators (AdaptiveOrchestrator, DREAM, LLF)
and the production v2 orchestrator (InferenceOrchestrator).

Legacy imports are deferred to avoid triggering multimodal_abstration.py
import errors in environments without DuckDB or userModule.
"""

from __future__ import annotations

# Production orchestrator (v2) -- safe to import everywhere
from .orchestrator_v2 import InferenceOrchestrator, OrchestratorConfig

__all__ = [
    "InferenceOrchestrator",
    "OrchestratorConfig",
]
