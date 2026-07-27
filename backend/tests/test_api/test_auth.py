from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("healthy", "degraded")


@pytest.mark.asyncio
async def test_login_admin(client: AsyncClient):
    resp = await client.post("/auth/login", json={"username": "admin", "password": "admin"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["username"] == "admin"
    assert isinstance(data["user_id"], str)


@pytest.mark.asyncio
async def test_login_invalid(client: AsyncClient):
    resp = await client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    uname = f"regtest_{__import__('uuid').uuid4().hex[:6]}"
    resp = await client.post("/auth/register", json={"username": uname, "password": "pass123456"})
    assert resp.status_code == 201, f"Register failed: {resp.text}"
    data = resp.json()
    assert "access_token" in data
    assert data["username"] == uname
    assert isinstance(data["user_id"], str)


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient):
    resp = await client.post("/auth/register", json={"username": "admin", "password": "pass123456"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_me(client: AsyncClient, user_token: str):
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "testuser"
    assert isinstance(data["is_admin"], bool)


@pytest.mark.asyncio
async def test_me_unauthorized(client: AsyncClient):
    resp = await client.get("/auth/me")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_chat_requires_auth(client: AsyncClient):
    resp = await client.post("/chat", json={"message": "hello", "session_id": "test"})
    assert resp.status_code in (403, 401)
