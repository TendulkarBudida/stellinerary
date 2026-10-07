from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from app import scheduler
from app.models import HourlyWeather, SiteWeatherForecast


@pytest.mark.asyncio
async def test_check_all_contingencies_uses_weather_agent_contract(monkeypatch):
    plan = SimpleNamespace(
        plan_id="plan-1",
        chosen_site=SimpleNamespace(id="nandi-hills", lat=13.37, lon=77.68),
        request=SimpleNamespace(date_start=date(2026, 12, 14), date_end=date(2026, 12, 15)),
    )
    weather = SiteWeatherForecast(
        site_id="nandi-hills",
        fetched_at=datetime.now(timezone.utc),
        hourly=[HourlyWeather(
            datetime_utc=datetime.now(timezone.utc),
            cloud_cover_pct=80,
        )],
    )
    calls = []
    updated_plan = SimpleNamespace(plan_id="plan-1")
    saved = []

    class FakePlanStore:
        def active(self):
            return [plan]

        def save(self, stored_plan):
            saved.append(stored_plan)

    async def fake_get_weather_forecast(*, site_id, lat, lon):
        calls.append((site_id, lat, lon))
        return weather

    def fake_check_contingency(current_plan, new_weather):
        assert current_plan is plan
        assert new_weather is weather
        return True, updated_plan

    monkeypatch.setattr(scheduler, "get_weather_forecast", fake_get_weather_forecast)
    monkeypatch.setattr(scheduler, "check_contingency", fake_check_contingency)
    monkeypatch.setattr(scheduler, "plan_store", FakePlanStore())

    await scheduler.check_all_contingencies()

    assert calls == [("nandi-hills", 13.37, 77.68)]
    assert saved == [updated_plan]
