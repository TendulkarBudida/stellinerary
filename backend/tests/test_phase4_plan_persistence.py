"""Phase 4 tests for durable plan retrieval and refresh endpoints."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.plan_store import PlanStore


def test_plan_store_survives_new_store_instance(tmp_path: Path):
    from app.models import ExpeditionPlan, PlanRequest

    path = tmp_path / "plans.db"
    plan = ExpeditionPlan(request=PlanRequest(
        user_lat=12.97, user_lon=77.59, date_start="2026-12-12", date_end="2026-12-12",
    ))
    stored = PlanStore(path).save(plan)
    loaded = PlanStore(path).get(stored.plan_id)

    assert loaded is not None
    assert loaded.plan_id == stored.plan_id


def test_plan_endpoints_persist_retrieve_and_refresh(tmp_path: Path, monkeypatch):
    store = PlanStore(tmp_path / "plans.db")
    monkeypatch.setattr("app.main.plan_store", store)
    with patch("app.agents.weather.fetch_astro_weather", new_callable=AsyncMock, return_value=None):
        with patch("app.agents.story.chat_completion", new_callable=AsyncMock, side_effect=Exception("offline")):
            with TestClient(app) as client:
                created = client.post("/plan", json={
                    "user_lat": 12.9716, "user_lon": 77.5946,
                    "date_start": "2026-12-12", "date_end": "2026-12-12",
                })
                assert created.status_code == 200
                plan_id = created.json()["plan_id"]
                assert client.get(f"/plans/{plan_id}").status_code == 200
                refreshed = client.post(f"/plans/{plan_id}/refresh")

    assert refreshed.status_code == 200
    assert refreshed.json()["plan_id"] == plan_id
    assert "refreshed" in refreshed.json()["contingency_note"].lower()
