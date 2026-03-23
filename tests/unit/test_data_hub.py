"""Tests for the DataHub service."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sys import path as sys_path
sys_path.insert(0, "examples/applications")

from common.data_hub_service import create_data_hub_app


@pytest.fixture
def client() -> TestClient:
    app = create_data_hub_app(max_cache_size=100)
    return TestClient(app)


class TestStore:
    def test_store_and_fetch(self, client: TestClient) -> None:
        resp = client.post("/store", json={
            "query_id": "q1",
            "data_key": "timeseries",
            "data": [1.0, 2.0, 3.0],
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["query_id"] == "q1"
        assert body["data_key"] == "timeseries"

        resp = client.get("/fetch/q1/timeseries")
        assert resp.status_code == 200
        assert resp.json()["data"] == [1.0, 2.0, 3.0]

    def test_store_multiple_keys(self, client: TestClient) -> None:
        client.post("/store", json={"query_id": "q2", "data_key": "video", "data": "frame1"})
        client.post("/store", json={"query_id": "q2", "data_key": "audio", "data": "wav1"})

        resp = client.get("/fetch/q2")
        assert resp.status_code == 200
        entries = resp.json()["entries"]
        assert "video" in entries
        assert "audio" in entries

    def test_store_overwrites_key(self, client: TestClient) -> None:
        client.post("/store", json={"query_id": "q3", "data_key": "k", "data": "old"})
        client.post("/store", json={"query_id": "q3", "data_key": "k", "data": "new"})

        resp = client.get("/fetch/q3/k")
        assert resp.json()["data"] == "new"


class TestFetch:
    def test_fetch_missing_query(self, client: TestClient) -> None:
        resp = client.get("/fetch/nonexistent/key")
        assert resp.status_code == 404

    def test_fetch_missing_key(self, client: TestClient) -> None:
        client.post("/store", json={"query_id": "q4", "data_key": "a", "data": 1})
        resp = client.get("/fetch/q4/missing_key")
        assert resp.status_code == 404


class TestEvict:
    def test_evict(self, client: TestClient) -> None:
        client.post("/store", json={"query_id": "q5", "data_key": "x", "data": "y"})
        resp = client.delete("/evict/q5")
        assert resp.json()["status"] == "evicted"

        resp = client.get("/fetch/q5/x")
        assert resp.status_code == 404

    def test_evict_nonexistent(self, client: TestClient) -> None:
        resp = client.delete("/evict/nonexistent")
        assert resp.json()["status"] == "not_found"


class TestHealth:
    def test_health(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestCacheEviction:
    def test_lru_eviction(self) -> None:
        app = create_data_hub_app(max_cache_size=3)
        client = TestClient(app)

        for i in range(4):
            client.post("/store", json={"query_id": f"q{i}", "data_key": "k", "data": i})

        # q0 should have been evicted
        resp = client.get("/fetch/q0/k")
        assert resp.status_code == 404

        # q3 should still be there
        resp = client.get("/fetch/q3/k")
        assert resp.status_code == 200
