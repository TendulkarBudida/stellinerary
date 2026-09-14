"""
Weather Intelligence Agent.

Given a site (lat/lon) and date range, returns an astro-specific weather
forecast: hourly cloud cover, seeing, transparency, temperature, humidity.

Key behaviors:
- Uses 7Timer ASTRO API (free, no key, designed for astronomers)
- Caches responses for 1 hour (weather doesn't change minute-to-minute)
- Degrades gracefully if the API is unavailable (returns "weather unknown" status)
- Generates a human-readable summary alongside the raw hourly data
"""

import logging
from datetime import datetime, timezone

from app.models import HourlyWeather, SiteWeatherForecast
from app.services.weather_client import fetch_astro_weather, parse_astro_forecast

logger = logging.getLogger(__name__)


async def get_weather_forecast(
    site_id: str,
    lat: float,
    lon: float,
) -> SiteWeatherForecast:
    """
    Fetch and parse weather forecast for a site.

    Returns a SiteWeatherForecast with hourly data and a human-readable summary.
    If the API is unavailable, returns a forecast with empty hourly data and
    a "weather unverified" summary — the pipeline continues without crashing.
    """
    raw = await fetch_astro_weather(lat, lon)

    if raw is None:
        logger.warning("Weather API unavailable for site %s — returning unverified forecast", site_id)
        return SiteWeatherForecast(
            site_id=site_id,
            fetched_at=datetime.now(timezone.utc),
            hourly=[],
            summary="⚠️ Weather data unavailable. Plan generated without weather verification — check local forecasts before heading out.",
        )

    parsed = parse_astro_forecast(raw)

    hourly = []
    for point in parsed:
        hourly.append(HourlyWeather(
            datetime_utc=datetime.fromisoformat(point["datetime_utc"]),
            cloud_cover_pct=point["cloud_cover_pct"],
            seeing_arcsec=point.get("seeing_arcsec"),
            transparency=point.get("transparency"),
            temperature_c=point.get("temperature_c"),
            relative_humidity_pct=point.get("relative_humidity_pct"),
            wind_speed_kmh=point.get("wind_speed_kmh"),
        ))

    summary = _generate_summary(hourly)

    return SiteWeatherForecast(
        site_id=site_id,
        fetched_at=datetime.now(timezone.utc),
        hourly=hourly,
        summary=summary,
    )


def _generate_summary(hourly: list[HourlyWeather]) -> str:
    """Generate a human-readable weather summary from hourly data."""
    if not hourly:
        return "No weather data available."

    # Find the night-time hours (roughly 18:00 – 06:00 local, but we work in UTC
    # and 7Timer gives us ~72 hours, so we summarize all available data)
    clear_hours = [h for h in hourly if h.cloud_cover_pct <= 30]
    partly_cloudy = [h for h in hourly if 30 < h.cloud_cover_pct <= 60]
    cloudy_hours = [h for h in hourly if h.cloud_cover_pct > 60]

    total = len(hourly)
    clear_pct = round(len(clear_hours) / total * 100)

    temps = [h.temperature_c for h in hourly if h.temperature_c is not None]
    min_temp = min(temps) if temps else None
    max_temp = max(temps) if temps else None

    seeing_vals = [h.seeing_arcsec for h in hourly if h.seeing_arcsec is not None]
    avg_seeing = round(sum(seeing_vals) / len(seeing_vals), 1) if seeing_vals else None

    parts = []

    # Cloud summary
    if clear_pct >= 70:
        parts.append(f"Mostly clear skies ({clear_pct}% of forecast hours clear)")
    elif clear_pct >= 40:
        parts.append(f"Mixed conditions — {clear_pct}% clear, {len(partly_cloudy)} partly cloudy hours")
    else:
        parts.append(f"Mostly cloudy — only {clear_pct}% of hours clear")

    # Temperature
    if min_temp is not None and max_temp is not None:
        parts.append(f"Temperature: {min_temp}°C to {max_temp}°C")

    # Seeing
    if avg_seeing is not None:
        if avg_seeing <= 1.0:
            parts.append(f"Seeing: excellent ({avg_seeing}\")")
        elif avg_seeing <= 1.5:
            parts.append(f"Seeing: good ({avg_seeing}\")")
        elif avg_seeing <= 2.0:
            parts.append(f"Seeing: average ({avg_seeing}\")")
        else:
            parts.append(f"Seeing: poor ({avg_seeing}\")")

    # Dew risk
    humidities = [h.relative_humidity_pct for h in hourly if h.relative_humidity_pct is not None]
    if humidities and max(humidities) > 85:
        parts.append("⚠️ High humidity — dew risk on optics. Bring dew shields or a hairdryer.")

    return ". ".join(parts) + "."


def find_clear_windows(
    hourly: list[HourlyWeather],
    max_cloud_pct: int = 30,
    min_window_hours: int = 2,
) -> list[tuple[datetime, datetime]]:
    """
    Find contiguous clear-sky windows in the forecast.

    Returns list of (start, end) tuples where cloud cover stays
    at or below max_cloud_pct for at least min_window_hours.
    """
    windows: list[tuple[datetime, datetime]] = []
    current_start: datetime | None = None
    prev_dt: datetime | None = None

    for h in hourly:
        if h.cloud_cover_pct <= max_cloud_pct:
            if current_start is None:
                current_start = h.datetime_utc
            prev_dt = h.datetime_utc
        else:
            if current_start is not None and prev_dt is not None:
                duration = (prev_dt - current_start).total_seconds() / 3600
                if duration >= min_window_hours:
                    windows.append((current_start, prev_dt))
            current_start = None
            prev_dt = None

    # Close any trailing window
    if current_start is not None and prev_dt is not None:
        duration = (prev_dt - current_start).total_seconds() / 3600
        if duration >= min_window_hours:
            windows.append((current_start, prev_dt))

    return windows
