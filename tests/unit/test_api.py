from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from rohe.api.app import create_app


@pytest.fixture
def app():
    return create_app(title="Test ROHE")


@pytest.mark.asyncio
async def test_health_check(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_openapi_docs(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "Test ROHE"


@pytest.mark.asyncio
async def test_404_for_unknown_route(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/nonexistent")
        assert response.status_code == 404
