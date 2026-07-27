from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import settings

settings.jwt_secret = "test-secret-not-for-production"
settings.redis_url = "redis://localhost:6379/1"
settings.enable_registration = True
settings.otel_enabled = False
# httpx AsyncClient uses base_url http://test → allow that host through
# TrustedHostMiddleware (evaluated at app import, which happens after this).
settings.allowed_hosts = ["localhost", "127.0.0.1", "test", "testserver"]


@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def app():
    from app.main import app
    yield app


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient) -> str:
    resp = await client.post("/auth/login", json={"username": "admin", "password": "admin"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def user_token(client: AsyncClient) -> str:
    resp = await client.post("/auth/register", json={"username": "testuser", "password": "testpass123"})
    if resp.status_code == 409:
        resp = await client.post("/auth/login", json={"username": "testuser", "password": "testpass123"})
    assert resp.status_code == 200, f"Register/login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def auth_headers(user_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {user_token}"}
