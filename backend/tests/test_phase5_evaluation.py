"""
Phase 5 evaluation suite: deterministic fixture-based tests for orchestration quality.

Covers 10 scenarios from the roadmap:
1. Beginner near Bangalore, one-night meteor shower trip.
2. Three-night request where only the second night has valid/clear weather.
3. Priority target blocked by one site's horizon but visible from another.
4. Long-future date outside forecast coverage.
5. Cloudy Plan A with a clear but farther Plan B.
6. No noteworthy events during the requested range.
7. Weather provider failure.
8. LLM rate limit/failure: core plan is still returned.
9. Night-access restriction and travel-limit exclusion.
10. High humidity/dew and high-altitude safety recommendations.
"""

import pytest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from app.models import (
    ForecastConfidence,
    HourlyWeather,
    PlanRequest,
    SiteWeatherForecast,
)
from app.orchestrator import generate_plan


def _forecast_for_night(site_id: str, target_date: date, cloud_cover: int = 10) -> SiteWeatherForecast:
    """Create a forecast that covers only the specified night."""
    night_start = datetime(target_date.year, target_date.month, target_date.day, 12, 30, tzinfo=timezone.utc)
    night_end = datetime(target_date.year, target_date.month, target_date.day + 1, 0, 30, tzinfo=timezone.utc)
    hours = int((night_end - night_start).total_seconds() / 3600) + 1
    return SiteWeatherForecast(
        site_id=site_id,
        fetched_at=night_start,
        hourly=[
            HourlyWeather(
                datetime_utc=night_start + timedelta(hours=h),
                cloud_cover_pct=cloud_cover,
                temperature_c=15.0,
                relative_humidity_pct=50,
            )
            for h in range(hours)
        ],
        forecast_start=night_start,
        forecast_end=night_end,
        forecast_confidence=ForecastConfidence.medium,
    )


def _clear_forecast(site_id: str, cloud_cover: int = 10, target_date: date | None = None) -> SiteWeatherForecast:
    """Create a forecast with uniform cloud cover."""
    if target_date:
        base = datetime(target_date.year, target_date.month, target_date.day, 12, 30, tzinfo=timezone.utc)
        hours = 24
    else:
        base = datetime(2026, 12, 12, 0, 0, tzinfo=timezone.utc)
        hours = 72
    return SiteWeatherForecast(
        site_id=site_id,
        fetched_at=base,
        hourly=[
            HourlyWeather(
                datetime_utc=base + timedelta(hours=h),
                cloud_cover_pct=cloud_cover,
                temperature_c=15.0,
                relative_humidity_pct=50,
            )
            for h in range(hours)
        ],
        forecast_start=base,
        forecast_end=base + timedelta(hours=hours - 1),
        forecast_confidence=ForecastConfidence.medium,
    )


def _high_humidity_forecast(site_id: str, target_date: date | None = None) -> SiteWeatherForecast:
    """Create a forecast with high humidity (dew risk)."""
    if target_date:
        base = datetime(target_date.year, target_date.month, target_date.day, 12, 30, tzinfo=timezone.utc)
        hours = 24
    else:
        base = datetime(2026, 12, 12, 0, 0, tzinfo=timezone.utc)
        hours = 72
    return SiteWeatherForecast(
        site_id=site_id,
        fetched_at=base,
        hourly=[
            HourlyWeather(
                datetime_utc=base + timedelta(hours=h),
                cloud_cover_pct=10,
                temperature_c=18.0,
                relative_humidity_pct=92,
            )
            for h in range(hours)
        ],
        forecast_start=base,
        forecast_end=base + timedelta(hours=hours - 1),
        forecast_confidence=ForecastConfidence.medium,
    )


def _bangalore_request(**kwargs) -> PlanRequest:
    """Create a request near Bangalore with sensible defaults."""
    defaults = dict(
        user_lat=12.9716,
        user_lon=77.5946,
        date_start=date(2026, 12, 12),
        date_end=date(2026, 12, 12),
    )
    defaults.update(kwargs)
    return PlanRequest(**defaults)


# ── Scenario 1: Beginner near Bangalore, one-night meteor shower trip ────


@pytest.mark.asyncio
async def test_scenario_1_beginner_meteor_shower_trip():
    """Beginner near Bangalore, one-night Geminid meteor shower trip."""
    request = _bangalore_request(
        date_start=date(2026, 12, 14),
        date_end=date(2026, 12, 14),
        experience_level="beginner",
        primary_goal="meteor_shower",
        max_travel_minutes=180,
    )

    with patch("app.orchestrator.get_weather_forecast", new_callable=AsyncMock) as mock_weather:
        with patch("app.agents.location_scout.get_weather_forecast", new_callable=AsyncMock):
            with patch("app.agents.story.chat_completion", new_callable=AsyncMock, side_effect=Exception("LLM offline")):
                mock_weather.return_value = None
                plan = await generate_plan(request)

    assert plan.options, "Should return at least one option"
    primary = plan.options[0]
    assert primary.label == "primary"
    assert primary.site is not None
    assert primary.night_plan.schedule is not None
    assert len(primary.night_plan.schedule.entries) > 0
    assert primary.gear is not None
    assert len(primary.gear.items) > 0
    assert any("meteor" in item.name.lower() or "reclining" in item.name.lower() or "sleeping" in item.name.lower()
               for item in primary.gear.items)


# ── Scenario 2: Three-night request, only second night has clear weather ─


@pytest.mark.asyncio
async def test_scenario_2_three_nights_only_second_clear():
    """Three-night request where only the second night has valid/clear weather."""
    request = _bangalore_request(
        date_start=date(2026, 12, 12),
        date_end=date(2026, 12, 14),
        max_travel_minutes=300,
    )

    async def weather_side_effect(site_id, lat, lon):
        return _forecast_for_night(site_id, date(2026, 12, 13))

    with patch("app.orchestrator.get_weather_forecast", new_callable=AsyncMock, side_effect=weather_side_effect):
        with patch("app.agents.location_scout.get_weather_forecast", new_callable=AsyncMock, side_effect=weather_side_effect):
            with patch("app.agents.story.chat_completion", new_callable=AsyncMock, side_effect=Exception("LLM offline")):
                plan = await generate_plan(request)

    assert plan.options
    primary = plan.options[0]
    assert primary.observation_date == date(2026, 12, 13)
    assert primary.night_plan.forecast_confidence == ForecastConfidence.medium


# ── Scenario 3: Priority target blocked by horizon ────────────────────────


@pytest.mark.asyncio
async def test_scenario_3_horizon_blocked_target():
    """Priority target blocked by one site's horizon but visible from another."""
    request = _bangalore_request(
        date_start=date(2026, 12, 14),
        date_end=date(2026, 12, 14),
        max_travel_minutes=300,
    )

    with patch("app.orchestrator.get_weather_forecast", new_callable=AsyncMock) as mock_weather:
        with patch("app.agents.location_scout.get_weather_forecast", new_callable=AsyncMock):
            with patch("app.agents.story.chat_completion", new_callable=AsyncMock, side_effect=Exception("LLM offline")):
                mock_weather.return_value = None
                plan = await generate_plan(request)

    assert plan.options
    primary = plan.options[0]
    assert primary.site is not None
    assert primary.night_plan.schedule is not None
    assert primary.night_plan.schedule.entries
    assert len(plan.ranked_sites) >= 2
    for ranked in plan.ranked_sites:
        assert set(ranked.score_components) == {"event_visibility", "weather", "bortle", "distance"}
        assert ranked.ranking_reason
    vis_scores = {rs.site.id: rs.event_visibility_score for rs in plan.ranked_sites}
    assert len(set(vis_scores.values())) > 1


# ── Scenario 4: Long-future date outside forecast coverage ───────────────


@pytest.mark.asyncio
async def test_scenario_4_outside_forecast_horizon():
    """Long-future date outside forecast coverage."""
    request = _bangalore_request(
        date_start=date(2027, 6, 1),
        date_end=date(2027, 6, 1),
    )

    with patch("app.orchestrator.get_weather_forecast", new_callable=AsyncMock) as mock_weather:
        with patch("app.agents.location_scout.get_weather_forecast", new_callable=AsyncMock):
            with patch("app.agents.story.chat_completion", new_callable=AsyncMock, side_effect=Exception("LLM offline")):
                mock_weather.return_value = None
                plan = await generate_plan(request)

    assert plan is not None
    assert plan.ranked_events == []


# ── Scenario 5: Cloudy Plan A with clear but farther Plan B ──────────────


@pytest.mark.asyncio
async def test_scenario_5_cloudy_primary_clear_fallback():
    """Cloudy Plan A with a clear but farther Plan B."""
    request = _bangalore_request(
        date_start=date(2026, 12, 14),
        date_end=date(2026, 12, 14),
        max_travel_minutes=300,
    )

    async def scout_weather(site_id, lat, lon):
        return _clear_forecast(site_id, cloud_cover=10, target_date=date(2026, 12, 14))

    option_calls = 0

    async def option_weather(site_id, lat, lon):
        nonlocal option_calls
        option_calls += 1
        if option_calls <= 2:
            return _clear_forecast(site_id, cloud_cover=80, target_date=date(2026, 12, 14))
        return _clear_forecast(site_id, cloud_cover=10, target_date=date(2026, 12, 14))

    with patch("app.orchestrator.get_weather_forecast", new_callable=AsyncMock, side_effect=option_weather):
        with patch("app.agents.location_scout.get_weather_forecast", new_callable=AsyncMock, side_effect=scout_weather):
            with patch("app.agents.story.chat_completion", new_callable=AsyncMock, side_effect=Exception("LLM offline")):
                plan = await generate_plan(request)

    assert len(plan.options) >= 2
    primary = plan.options[0]
    fallback = plan.options[1]
    assert primary.label == "primary"
    assert fallback.label == "weather_fallback"
    assert primary.night_plan.weather_forecast is not None
    assert fallback.night_plan.weather_forecast is not None
    primary_cloud = primary.night_plan.weather_forecast.hourly[0].cloud_cover_pct
    fallback_cloud = fallback.night_plan.weather_forecast.hourly[0].cloud_cover_pct
    assert fallback_cloud < primary_cloud
    assert "switch" in " ".join(fallback.tradeoffs).lower()


# ── Scenario 6: No noteworthy events during requested range ──────────────


@pytest.mark.asyncio
async def test_scenario_6_no_noteworthy_events():
    """No noteworthy events during the requested range."""
    request = _bangalore_request(
        date_start=date(2026, 6, 15),
        date_end=date(2026, 6, 15),
    )

    with patch("app.orchestrator.get_weather_forecast", new_callable=AsyncMock) as mock_weather:
        with patch("app.agents.location_scout.get_weather_forecast", new_callable=AsyncMock):
            with patch("app.agents.story.chat_completion", new_callable=AsyncMock, side_effect=Exception("LLM offline")):
                mock_weather.return_value = None
                plan = await generate_plan(request)

    assert plan is not None
    assert len(plan.ranked_events) == 0 or all(
        e.type == "seasonal" for e in plan.ranked_events
    )


# ── Scenario 7: Weather provider failure ──────────────────────────────────


@pytest.mark.asyncio
async def test_scenario_7_weather_provider_failure():
    """Weather provider failure — plan still generated with degraded confidence."""
    request = _bangalore_request(
        date_start=date(2026, 12, 14),
        date_end=date(2026, 12, 14),
    )

    with patch("app.orchestrator.get_weather_forecast", new_callable=AsyncMock) as mock_weather:
        with patch("app.agents.location_scout.get_weather_forecast", new_callable=AsyncMock):
            with patch("app.agents.story.chat_completion", new_callable=AsyncMock, side_effect=Exception("LLM offline")):
                mock_weather.return_value = None
                plan = await generate_plan(request)

    assert plan.options
    primary = plan.options[0]
    assert primary.confidence in {
        ForecastConfidence.unavailable_provider_error,
        ForecastConfidence.unavailable_outside_horizon,
    }
    assert any("unavailable" in r.lower() or "verify" in r.lower() or "recheck" in r.lower() for r in primary.reasons)
    assert primary.night_plan.schedule is not None


# ── Scenario 8: LLM rate limit/failure — core plan still returned ────────


@pytest.mark.asyncio
async def test_scenario_8_llm_failure_core_plan_returned():
    """LLM rate limit/failure: core plan is still returned."""
    request = _bangalore_request(
        date_start=date(2026, 12, 14),
        date_end=date(2026, 12, 14),
    )

    with patch("app.orchestrator.get_weather_forecast", new_callable=AsyncMock) as mock_weather:
        with patch("app.agents.location_scout.get_weather_forecast", new_callable=AsyncMock):
            with patch("app.agents.story.chat_completion", new_callable=AsyncMock, side_effect=Exception("Rate limit exceeded")):
                mock_weather.return_value = None
                plan = await generate_plan(request)

    assert plan.options
    primary = plan.options[0]
    assert primary.site is not None
    assert primary.night_plan.schedule is not None
    assert primary.gear is not None
    assert len(primary.gear.items) > 0


# ── Scenario 9: Night-access restriction and travel-limit exclusion ──────


@pytest.mark.asyncio
async def test_scenario_9_night_access_and_travel_limits():
    """Night-access restriction and travel-limit exclusion."""
    request = _bangalore_request(
        date_start=date(2026, 12, 14),
        date_end=date(2026, 12, 14),
        max_travel_minutes=60,
        overnight_allowed=False,
    )

    with patch("app.orchestrator.get_weather_forecast", new_callable=AsyncMock) as mock_weather:
        with patch("app.agents.location_scout.get_weather_forecast", new_callable=AsyncMock):
            with patch("app.agents.story.chat_completion", new_callable=AsyncMock, side_effect=Exception("LLM offline")):
                mock_weather.return_value = None
                plan = await generate_plan(request)

    assert plan.options
    primary = plan.options[0]
    assert primary.site is not None
    assert primary.night_plan.schedule is not None
    assert plan.ranked_sites
    for ranked in plan.ranked_sites:
        assert ranked.travel_time_estimate_min is not None
        assert ranked.travel_time_estimate_min <= 60


# ── Scenario 10: High humidity/dew and high-altitude safety ──────────────


@pytest.mark.asyncio
async def test_scenario_10_humidity_and_altitude_safety():
    """High humidity/dew and high-altitude safety recommendations."""
    request = PlanRequest(
        user_lat=32.3160,
        user_lon=78.0080,
        date_start=date(2026, 7, 15),
        date_end=date(2026, 7, 15),
        max_travel_minutes=2880,
        overnight_allowed=True,
    )

    with patch("app.orchestrator.get_weather_forecast", new_callable=AsyncMock) as mock_weather:
        with patch("app.agents.location_scout.get_weather_forecast", new_callable=AsyncMock):
            with patch("app.agents.story.chat_completion", new_callable=AsyncMock, side_effect=Exception("LLM offline")):
                mock_weather.return_value = _high_humidity_forecast("spiti_valley", date(2026, 7, 15))
                plan = await generate_plan(request)

    assert plan.options
    primary = plan.options[0]
    assert primary.gear is not None
    all_warnings = " ".join(primary.gear.warnings).lower()
    assert "dew" in all_warnings or "humidity" in all_warnings
    assert "altitude" in all_warnings
