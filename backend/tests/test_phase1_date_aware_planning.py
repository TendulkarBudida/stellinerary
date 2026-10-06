"""Regression tests for Phase 1: truthful, multi-night plan output."""

from datetime import date, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.models import ForecastConfidence, HourlyWeather, PlanRequest, SiteWeatherForecast
from app.orchestrator import _forecast_confidence_for_night, _requested_nights


def _forecast(start: datetime, hours: int = 96) -> SiteWeatherForecast:
    return SiteWeatherForecast(
        site_id="test-site",
        fetched_at=start,
        hourly=[
            HourlyWeather(
                datetime_utc=start + timedelta(hours=offset),
                cloud_cover_pct=10,
            )
            for offset in range(hours)
        ],
        forecast_start=start,
        forecast_end=start + timedelta(hours=hours - 1),
        forecast_confidence=ForecastConfidence.medium,
    )


def test_requested_nights_are_inclusive():
    request = PlanRequest(
        user_lat=12.97,
        user_lon=77.59,
        date_start=date(2026, 12, 12),
        date_end=date(2026, 12, 14),
    )

    assert _requested_nights(request) == [
        date(2026, 12, 12),
        date(2026, 12, 13),
        date(2026, 12, 14),
    ]


def test_forecast_is_not_applied_outside_its_horizon():
    forecast = _forecast(datetime(2026, 12, 12, 0, 0, tzinfo=timezone.utc), hours=72)

    assert _forecast_confidence_for_night(forecast, date(2026, 12, 12)) == ForecastConfidence.medium
    assert _forecast_confidence_for_night(forecast, date(2026, 12, 16)) == ForecastConfidence.unavailable_outside_horizon


@pytest.mark.parametrize(
    "date_start,date_end",
    [
        (date(2026, 12, 15), date(2026, 12, 14)),
        (date(2026, 12, 1), date(2026, 12, 15)),
    ],
)
def test_request_rejects_invalid_or_excessive_date_ranges(date_start, date_end):
    with pytest.raises(ValidationError):
        PlanRequest(
            user_lat=12.97,
            user_lon=77.59,
            date_start=date_start,
            date_end=date_end,
        )
