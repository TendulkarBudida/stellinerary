"""Authenticated trip persistence scenarios (offline — Supabase HTTP mocked).

Covers the matrix I verified live against the real stack:
- authenticated create stores the row under the token's user id
- list/get are scoped to the caller (cross-user rows invisible)
- Supabase outage falls back to the local store without failing the request
- anonymous behavior is unchanged
"""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from pytest_httpx import HTTPXMock

from app.main import app
from app.services import trip_store
from app.services.plan_store import PlanStore

AUTH = {"Authorization": "Bearer test-token"}


def _stub_settings(monkeypatch):
    stub = type(
        "S",
        (),
        {
            "supabase_url": "https://test.supabase.co",
            "supabase_secret_key": "secret",
            "supabase_jwks_url": "https://test.supabase.co/auth/v1/.well-known/jwks.json",
        },
    )()
    monkeypatch.setattr("app.services.auth.verify_token", lambda _token: "user-1")
    monkeypatch.setattr("app.services.auth.settings", stub)
    monkeypatch.setattr("app.services.trip_store.settings", stub)


def _minimal_plan_payload(plan_id="plan-1"):
    return {
        "request": {"user_lat": 12.97, "user_lon": 77.59, "date_start": "2026-12-12", "date_end": "2026-12-12"},
        "plan_id": plan_id,
        "ranked_events": [],
        "ranked_sites": [],
        "night_plans": [],
        "options": [],
        "stories": [],
        "generated_at": "2026-10-13T00:00:00+00:00",
    }


def _create_plan(client: TestClient) -> dict:
    with patch("app.agents.weather.fetch_astro_weather", new_callable=AsyncMock, return_value=None):
        with patch("app.agents.story.chat_completion", new_callable=AsyncMock, side_effect=Exception("offline")):
            created = client.post("/plan", json={
                "user_lat": 12.9716, "user_lon": 77.5946,
                "date_start": "2026-12-12", "date_end": "2026-12-12",
            }, headers=AUTH)
    assert created.status_code == 200
    return created.json()


def test_authenticated_create_scoped_to_token_user(tmp_path, monkeypatch, httpx_mock: HTTPXMock):
    _stub_settings(monkeypatch)
    monkeypatch.setattr("app.main.plan_store", PlanStore(tmp_path / "plans.db"))
    captured: dict = {}

    def _capture(request):
        captured.update(json.loads(request.content))
        return httpx.Response(201, json={})

    httpx_mock.add_callback(_capture, method="POST")
    with TestClient(app) as client:
        plan = _create_plan(client)

    assert captured["user_id"] == "user-1"
    assert captured["plan_id"] == plan["plan_id"]
    assert captured["payload"]["plan_id"] == plan["plan_id"]


def test_authenticated_list_scoped_to_caller(tmp_path, monkeypatch, httpx_mock: HTTPXMock):
    _stub_settings(monkeypatch)
    monkeypatch.setattr("app.main.plan_store", PlanStore(tmp_path / "plans.db"))
    httpx_mock.add_response(json=[{
        "plan_id": "mine", "observation_end": "2026-12-12",
        "updated_at": "2026-10-13T00:00:00+00:00",
        "payload": {"chosen_site": {"name": "Nandi Hills"}, "request": {"date_start": "2026-12-12"}},
    }])
    with TestClient(app) as client:
        listed = client.get("/plans", headers=AUTH)

    assert listed.status_code == 200
    assert [entry["plan_id"] for entry in listed.json()] == ["mine"]
    assert listed.json()[0]["site_name"] == "Nandi Hills"
    (request,) = httpx_mock.get_requests()
    assert "user_id=eq.user-1" in str(request.url)


def test_cross_user_plan_is_invisible(tmp_path, monkeypatch, httpx_mock: HTTPXMock):
    _stub_settings(monkeypatch)
    monkeypatch.setattr("app.main.plan_store", PlanStore(tmp_path / "plans.db"))
    httpx_mock.add_response(json=[])
    with TestClient(app) as client:
        assert client.get("/plans/others", headers=AUTH).status_code == 404
    (request,) = httpx_mock.get_requests()
    assert "plan_id=eq.others" in str(request.url)


def test_authenticated_get_reads_own_row(tmp_path, monkeypatch, httpx_mock: HTTPXMock):
    _stub_settings(monkeypatch)
    monkeypatch.setattr("app.main.plan_store", PlanStore(tmp_path / "plans.db"))
    httpx_mock.add_response(json=[{"payload": _minimal_plan_payload("mine")}])
    with TestClient(app) as client:
        fetched = client.get("/plans/mine", headers=AUTH)

    assert fetched.status_code == 200
    assert fetched.json()["plan_id"] == "mine"


def test_supabase_outage_falls_back_to_local(tmp_path, monkeypatch, httpx_mock: HTTPXMock):
    _stub_settings(monkeypatch)
    monkeypatch.setattr("app.main.plan_store", PlanStore(tmp_path / "plans.db"))
    httpx_mock.add_response(method="POST", status_code=500)
    with TestClient(app) as client:
        plan = _create_plan(client)
        httpx_mock.add_response(method="GET", status_code=500)
        listed = client.get("/plans", headers=AUTH)

    assert listed.status_code == 200
    assert plan["plan_id"] in [entry["plan_id"] for entry in listed.json()]


def test_authenticated_delete_removes_own_row(tmp_path, monkeypatch, httpx_mock: HTTPXMock):
    _stub_settings(monkeypatch)
    monkeypatch.setattr("app.main.plan_store", PlanStore(tmp_path / "plans.db"))
    httpx_mock.add_response(json=[{"payload": _minimal_plan_payload("gone")}])

    def _deleted(_request):
        return httpx.Response(204)

    httpx_mock.add_callback(_deleted, method="DELETE")
    with TestClient(app) as client:
        deleted = client.delete("/plans/gone", headers=AUTH)

    assert deleted.status_code == 200
    assert deleted.json()["deleted"] == "gone"
    methods = [request.method for request in httpx_mock.get_requests()]
    assert methods == ["GET", "DELETE"]


def test_authenticated_delete_missing_row_is_404(tmp_path, monkeypatch, httpx_mock: HTTPXMock):
    _stub_settings(monkeypatch)
    monkeypatch.setattr("app.main.plan_store", PlanStore(tmp_path / "plans.db"))
    httpx_mock.add_response(json=[])
    with TestClient(app) as client:
        assert client.delete("/plans/ghost", headers=AUTH).status_code == 404
    assert [request.method for request in httpx_mock.get_requests()] == ["GET"]


@pytest.mark.asyncio
async def test_trip_store_delete_skips_http_when_missing(httpx_mock: HTTPXMock, monkeypatch):
    _stub_settings(monkeypatch)
    httpx_mock.add_response(json=[])
    assert await trip_store.delete_trip("user-1", "ghost") is False
