"""Tests for the orchestrator service phase condition evaluation.

Note: Phase condition logic moved to InferenceOrchestrator (v2).
Tests are now in test_orchestrator_v2.py. This file kept for backward compat
and tests the orchestrator service app creation.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sys import path as sys_path
sys_path.insert(0, "examples/applications")

from common.orchestrator_service import create_orchestrator_app


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestOrchestratorServiceApp:
    def test_health_endpoint(self) -> None:
        app = create_orchestrator_app()
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "orchestrator"
        assert "engine" in data
        assert data["engine"] == "InferenceOrchestrator_v2"

    def test_plans_endpoint_empty(self) -> None:
        app = create_orchestrator_app()
        client = TestClient(app)
        resp = client.get("/plans")
        assert resp.status_code == 200

    def test_orchestrate_no_plan(self) -> None:
        app = create_orchestrator_app()
        client = TestClient(app)
        resp = client.post("/orchestrate", json={
            "query_id": "test",
            "pipeline_id": "nonexistent",
            "modalities": ["ts"],
        })
        assert resp.status_code == 200
        assert resp.json()["model_count"] == 0
