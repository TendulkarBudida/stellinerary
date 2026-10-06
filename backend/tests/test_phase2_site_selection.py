"""Phase 2 tests: bounded concurrent weather and explainable site ranking."""

import asyncio
from datetime import date, datetime, timezone

import pytest

from app.agents.location_scout import rank_sites
from app.models import ForecastConfidence, HourlyWeather, SiteWeatherForecast


def _forecast(site_id: str) -> SiteWeatherForecast:
    return SiteWeatherForecast(
        site_id=site_id,
        fetched_at=datetime.now(timezone.utc),
        hourly=[HourlyWeather(datetime_utc=datetime.now(timezone.utc), cloud_cover_pct=10)],
        forecast_confidence=ForecastConfidence.medium,
    )


@pytest.mark.asyncio
async def test_weather_is_requested_only_for_shortlisted_sites_concurrently(monkeypatch):
    active = 0
    peak_active = 0
    calls: list[str] = []

    async def fake_forecast(site_id, lat, lon):
        nonlocal active, peak_active
        calls.append(site_id)
        active += 1
        peak_active = max(peak_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        return _forecast(site_id)

    monkeypatch.setattr("app.agents.location_scout.get_weather_forecast", fake_forecast)
    ranked = await rank_sites(12.9716, 77.5946, max_results=3, shortlist_size=3)

    assert len(ranked) == 3
    assert len(calls) == 3
    assert peak_active > 1


@pytest.mark.asyncio
async def test_travel_constraint_filters_sites_before_weather(monkeypatch):
    calls: list[str] = []

    async def fake_forecast(site_id, lat, lon):
        calls.append(site_id)
        return _forecast(site_id)

    monkeypatch.setattr("app.agents.location_scout.get_weather_forecast", fake_forecast)
    ranked = await rank_sites(
        12.9716, 77.5946, max_results=5, max_travel_minutes=120, shortlist_size=5,
    )

    assert ranked
    assert all(site.travel_time_estimate_min <= 120 for site in ranked)
    assert len(calls) == len(ranked)


@pytest.mark.asyncio
async def test_ranked_sites_include_explainable_score_components():
    ranked = await rank_sites(
        12.9716, 77.5946, max_results=3, fetch_weather=False,
        observation_dates=[date(2026, 12, 14)],
    )

    for site in ranked:
        assert set(site.score_components) == {"event_visibility", "weather", "bortle", "distance"}
        assert 0 <= site.event_visibility_score <= 1
        assert site.ranking_reason
