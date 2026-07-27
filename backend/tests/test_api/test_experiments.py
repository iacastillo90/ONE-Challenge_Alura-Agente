from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_experiments(client: AsyncClient, auth_headers: dict[str, str]):
    resp = await client.get("/experiments", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_list_builtins(client: AsyncClient, auth_headers: dict[str, str]):
    resp = await client.get("/experiments/builtins", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 4
    names = [e["name"] for e in data]
    assert "precision" in names
    assert "recall" in names


@pytest.mark.asyncio
async def test_create_and_get_experiment(client: AsyncClient, auth_headers: dict[str, str]):
    config = {"top_k": 3, "score_threshold": 0.6, "hybrid_search_alpha": 0.9}
    resp = await client.post(
        "/experiments",
        headers=auth_headers,
        json={"name": "test-exp", "config": config, "traffic_percent": 5},
    )
    assert resp.status_code == 201
    data = resp.json()
    exp_id = data["id"]
    assert data["name"] == "test-exp"
    assert data["config"]["top_k"] == 3
    assert data["traffic_percent"] == 5

    resp = await client.get(f"/experiments/{exp_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "test-exp"


@pytest.mark.asyncio
async def test_update_experiment(client: AsyncClient, auth_headers: dict[str, str]):
    config = {"top_k": 5, "score_threshold": 0.45}
    resp = await client.post(
        "/experiments",
        headers=auth_headers,
        json={"name": "upd-exp", "config": config, "traffic_percent": 10},
    )
    exp_id = resp.json()["id"]

    resp = await client.put(
        f"/experiments/{exp_id}",
        headers=auth_headers,
        json={"traffic_percent": 20, "is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["traffic_percent"] == 20
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_delete_experiment(client: AsyncClient, auth_headers: dict[str, str]):
    config = {"top_k": 1}
    resp = await client.post(
        "/experiments",
        headers=auth_headers,
        json={"name": "del-exp", "config": config, "traffic_percent": 1},
    )
    exp_id = resp.json()["id"]

    resp = await client.delete(f"/experiments/{exp_id}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get(f"/experiments/{exp_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_experiment_stats(client: AsyncClient, auth_headers: dict[str, str]):
    resp = await client.get("/experiments/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    control = [s for s in data if s["experiment_id"] is None]
    assert len(control) >= 1
    assert control[0]["experiment_name"] == "control (default)"
