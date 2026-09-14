"""Step 5 — Weather Intelligence agent tests.

Tests:
1. Parsing of 7Timer response format into our HourlyWeather models.
2. Summary generation for different conditions.
3. Clear window detection.
4. Cache behavior.
5. Graceful degradation when API is unavailable.
6. Live API sanity check (if network available).
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from app.agents.weather import get_weather_forecast, find_clear_windows
from app.models import HourlyWeather, SiteWeatherForecast
from app.services.weather_client import parse_astro_forecast, clear_cache


# ── Mock 7Timer response ──────────────────────────────────────────────

MOCK_7TIMER_RESPONSE = {
    "product": "astro",
    "init": "2026091406",
    "dataseries": [
        {"timepoint": 3, "cloudcover": 1, "seeing": 2, "transparency": 2,
         "temp2m": 12, "rh2m": 45, "wind10m": {"direction": "N", "speed": 2}},
        {"timepoint": 6, "cloudcover": 1, "seeing": 3, "transparency": 2,
         "temp2m": 10, "rh2m": 50, "wind10m": {"direction": "N", "speed": 2}},
        {"timepoint": 9, "cloudcover": 2, "seeing": 3, "transparency": 3,
         "temp2m": 8, "rh2m": 55, "wind10m": {"direction": "NE", "speed": 3}},
        {"timepoint": 12, "cloudcover": 7, "seeing": 5, "transparency": 5,
         "temp2m": 9, "rh2m": 70, "wind10m": {"direction": "E", "speed": 4}},
        {"timepoint": 15, "cloudcover": 8, "seeing": 6, "transparency": 6,
         "temp2m": 11, "rh2m": 60, "wind10m": {"direction": "E", "speed": 3}},
        {"timepoint": 18, "cloudcover": 3, "seeing": 3, "transparency": 3,
         "temp2m": 13, "rh2m": 48, "wind10m": {"direction": "SE", "speed": 2}},
        {"timepoint": 21, "cloudcover": 2, "seeing": 2, "transparency": 2,
         "temp2m": 11, "rh2m": 52, "wind10m": {"direction": "S", "speed": 2}},
        {"timepoint": 24, "cloudcover": 1, "seeing": 2, "transparency": 1,
         "temp2m": 9, "rh2m": 58, "wind10m": {"direction": "S", "speed": 1}},
    ],
}


class TestParseAstroForecast:
    def test_parses_correct_number_of_points(self):
        result = parse_astro_forecast(MOCK_7TIMER_RESPONSE)
        assert len(result) == 8

    def test_cloud_cover_converted_to_percentage(self):
        result = parse_astro_forecast(MOCK_7TIMER_RESPONSE)
        # cloudcover=1 → 6%, cloudcover=7 → 81%
        assert result[0]["cloud_cover_pct"] == 6
        assert result[3]["cloud_cover_pct"] == 81

    def test_seeing_converted_to_arcseconds(self):
        result = parse_astro_forecast(MOCK_7TIMER_RESPONSE)
        assert result[0]["seeing_arcsec"] == 0.75  # seeing=2
        assert result[3]["seeing_arcsec"] == 1.5    # seeing=5

    def test_transparency_converted_to_label(self):
        result = parse_astro_forecast(MOCK_7TIMER_RESPONSE)
        assert result[0]["transparency"] == "above_average"  # transparency=2
        assert result[3]["transparency"] == "poor"           # transparency=5

    def test_datetime_calculated_from_init(self):
        result = parse_astro_forecast(MOCK_7TIMER_RESPONSE)
        # init=2026091406, first timepoint=3 → 2026-09-14 09:00 UTC
        dt = datetime.fromisoformat(result[0]["datetime_utc"])
        assert dt.hour == 9
        assert dt.day == 14

    def test_temperature_passed_through(self):
        result = parse_astro_forecast(MOCK_7TIMER_RESPONSE)
        assert result[0]["temperature_c"] == 12
        assert result[2]["temperature_c"] == 8


class TestFindClearWindows:
    def _make_hourly(self, cloud_values: list[int]) -> list[HourlyWeather]:
        base = datetime(2026, 9, 14, 18, 0, tzinfo=timezone.utc)
        return [
            HourlyWeather(
                datetime_utc=base + timedelta(hours=i * 3),
                cloud_cover_pct=c,
            )
            for i, c in enumerate(cloud_values)
        ]

    def test_finds_contiguous_clear_window(self):
        # 6 hours clear, then cloudy
        hourly = self._make_hourly([10, 20, 15, 80, 90, 70])
        windows = find_clear_windows(hourly, max_cloud_pct=30, min_window_hours=2)
        assert len(windows) == 1
        # First 3 points = 0h, 3h, 6h → window is 6 hours
        assert windows[0][0].hour == 18
        assert windows[0][1].hour == 0  # midnight next day

    def test_ignores_short_windows(self):
        # Only 1 clear point (0 hours duration)
        hourly = self._make_hourly([80, 20, 80, 80])
        windows = find_clear_windows(hourly, max_cloud_pct=30, min_window_hours=2)
        assert len(windows) == 0

    def test_finds_multiple_windows(self):
        hourly = self._make_hourly([10, 10, 10, 80, 80, 10, 10, 10])
        windows = find_clear_windows(hourly, max_cloud_pct=30, min_window_hours=2)
        assert len(windows) == 2

    def test_all_clear_is_one_window(self):
        hourly = self._make_hourly([10, 20, 15, 10, 5, 20])
        windows = find_clear_windows(hourly, max_cloud_pct=30, min_window_hours=2)
        assert len(windows) == 1


class TestWeatherAgent:
    @pytest.mark.asyncio
    async def test_graceful_degradation_on_api_failure(self):
        """When 7Timer is down, agent returns an unverified forecast, not a crash."""
        with patch("app.agents.weather.fetch_astro_weather", new_callable=AsyncMock, return_value=None):
            result = await get_weather_forecast("test_site", 13.37, 77.68)
            assert isinstance(result, SiteWeatherForecast)
            assert len(result.hourly) == 0
            assert "unavailable" in result.summary.lower() or "unverified" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_successful_forecast_returns_hourly_data(self):
        """When API returns data, agent parses it into HourlyWeather objects."""
        with patch("app.agents.weather.fetch_astro_weather", new_callable=AsyncMock, return_value=MOCK_7TIMER_RESPONSE):
            result = await get_weather_forecast("nandi_hills", 13.37, 77.68)
            assert isinstance(result, SiteWeatherForecast)
            assert result.site_id == "nandi_hills"
            assert len(result.hourly) == 8
            assert all(isinstance(h, HourlyWeather) for h in result.hourly)
            assert result.summary  # non-empty summary

    @pytest.mark.asyncio
    async def test_summary_mentions_temperature(self):
        with patch("app.agents.weather.fetch_astro_weather", new_callable=AsyncMock, return_value=MOCK_7TIMER_RESPONSE):
            result = await get_weather_forecast("nandi_hills", 13.37, 77.68)
            assert "°C" in result.summary


class TestLiveAPI:
    """Sanity check against the real 7Timer API. Skipped if no network."""

    @pytest.mark.asyncio
    async def test_live_fetch_nandi_hills(self):
        clear_cache()
        try:
            from app.services.weather_client import fetch_astro_weather
            raw = await fetch_astro_weather(13.37, 77.68)
        except Exception:
            pytest.skip("Network unavailable")

        if raw is None:
            pytest.skip("7Timer API unavailable")

        assert "dataseries" in raw
        assert len(raw["dataseries"]) > 0

        parsed = parse_astro_forecast(raw)
        assert len(parsed) > 0
        assert all("cloud_cover_pct" in p for p in parsed)
        assert all(0 <= p["cloud_cover_pct"] <= 100 for p in parsed)
