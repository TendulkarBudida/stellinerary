"""
Weather client — wraps the 7Timer ASTRO API.

Endpoint: https://www.7timer.info/bin/api.pl?product=astro&lon=X&lat=Y&output=json
Returns: 3-hourly forecasts for ~72 hours with cloud cover, seeing, transparency,
         temperature, humidity, wind.

Includes response caching (1-hour TTL) and graceful degradation if the API is down.
"""

import logging
import time
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

SEVEN_TIMER_BASE = "https://www.7timer.info/bin/api.pl"
CACHE_TTL_SECONDS = 3600  # 1 hour — weather doesn't change minute-to-minute
REQUEST_TIMEOUT_SECONDS = 15

# Simple in-memory cache: key = "lat,lon" → (timestamp, data)
_cache: dict[str, tuple[float, dict]] = {}


# ── 7Timer response decoding tables ──────────────────────────────────

# 7Timer uses numeric codes for seeing and transparency
SEEING_MAP = {
    1: 0.5,   # < 0.5 arcsec (superb)
    2: 0.75,  # 0.5–0.75
    3: 1.0,   # 0.75–1
    4: 1.25,  # 1–1.25
    5: 1.5,   # 1.25–1.5
    6: 2.0,   # 1.5–2
    7: 2.5,   # 2–2.5
    8: 3.5,   # > 2.5 (poor)
}

TRANSPARENCY_MAP = {
    1: "excellent",     # < 0.3 mag extinction
    2: "above_average", # 0.3–0.4
    3: "average",       # 0.4–0.5
    4: "below_average", # 0.5–0.6
    5: "poor",          # 0.6–0.7
    6: "very_poor",     # 0.7–0.8
    7: "terrible",      # > 0.8
    8: "unobservable",  # > 0.9
}

# Cloud cover: 7Timer gives 1-9 scale, we convert to percentage
CLOUD_COVER_MAP = {
    1: 6,    # 0–6%
    2: 19,   # 6–19%
    3: 31,   # 19–31%
    4: 44,   # 31–44%
    5: 56,   # 44–56%
    6: 69,   # 56–69%
    7: 81,   # 69–81%
    8: 94,   # 81–94%
    9: 100,  # 94–100%
}

# Temperature: 7Timer returns in Celsius, wind in km/h via a scale
WIND_SPEED_MAP = {
    1: 0.5,   # below 0.3 m/s → ~1 km/h
    2: 2.5,   # 0.3–3.4 m/s
    3: 9.0,   # 3.4–5.5 m/s
    4: 16.0,  # 5.5–8.0 m/s
    5: 25.0,  # 8.0–10.8 m/s
    6: 35.0,  # 10.8–13.9 m/s
    7: 45.0,  # 13.9–17.2 m/s
    8: 58.0,  # 17.2–20.8 m/s
}


def _cache_key(lat: float, lon: float) -> str:
    """Round to 2 decimal places so nearby queries share cache."""
    return f"{round(lat, 2)},{round(lon, 2)}"


def _is_cache_valid(key: str) -> bool:
    if key not in _cache:
        return False
    ts, _ = _cache[key]
    return (time.time() - ts) < CACHE_TTL_SECONDS


async def fetch_astro_weather(lat: float, lon: float) -> dict | None:
    """
    Fetch 7Timer ASTRO forecast for a location.

    Returns the raw JSON response dict, or None if the API is unavailable.
    Results are cached for 1 hour.
    """
    key = _cache_key(lat, lon)

    if _is_cache_valid(key):
        logger.debug("Weather cache hit for %s", key)
        return _cache[key][1]

    params = {
        "product": "astro",
        "lat": round(lat, 2),
        "lon": round(lon, 2),
        "output": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(SEVEN_TIMER_BASE, params=params)
            response.raise_for_status()
            data = response.json()

        _cache[key] = (time.time(), data)
        logger.info("Weather fetched for %s — %d data points", key, len(data.get("dataseries", [])))
        return data

    except httpx.TimeoutException:
        logger.warning("7Timer API timeout for %s", key)
        return None
    except httpx.HTTPStatusError as e:
        logger.warning("7Timer API error %d for %s", e.response.status_code, key)
        return None
    except Exception as e:
        logger.warning("7Timer API unexpected error for %s: %s", key, e)
        return None


def parse_astro_forecast(raw: dict, init_time: datetime | None = None) -> list[dict]:
    """
    Parse a 7Timer ASTRO response into a list of hourly weather dicts.

    Args:
        raw: The raw 7Timer JSON response.
        init_time: The init timestamp; if None, parsed from the response.

    Returns:
        List of dicts with keys: datetime_utc, cloud_cover_pct, seeing_arcsec,
        transparency, temperature_c, relative_humidity_pct, wind_speed_kmh.
    """
    init_str = raw.get("init", "")
    if init_time is None and init_str:
        # Format: "2026091406" → 2026-09-14 06:00 UTC
        try:
            init_time = datetime.strptime(init_str, "%Y%m%d%H").replace(tzinfo=timezone.utc)
        except ValueError:
            logger.warning("Could not parse 7Timer init time: %s", init_str)
            init_time = datetime.now(timezone.utc)

    if init_time is None:
        init_time = datetime.now(timezone.utc)

    results = []
    for point in raw.get("dataseries", []):
        timepoint_hours = point.get("timepoint", 0)
        from datetime import timedelta
        dt = init_time + timedelta(hours=timepoint_hours)

        cloud_raw = point.get("cloudcover", 5)
        seeing_raw = point.get("seeing", 4)
        transparency_raw = point.get("transparency", 3)
        temp_raw = point.get("temp2m", None)
        rh_raw = point.get("rh2m", None)
        wind_raw = point.get("wind10m", {})
        wind_speed_raw = wind_raw.get("speed", 3) if isinstance(wind_raw, dict) else 3

        results.append({
            "datetime_utc": dt.isoformat(),
            "cloud_cover_pct": CLOUD_COVER_MAP.get(cloud_raw, 50),
            "seeing_arcsec": SEEING_MAP.get(seeing_raw, 1.5),
            "transparency": TRANSPARENCY_MAP.get(transparency_raw, "average"),
            "temperature_c": temp_raw,
            "relative_humidity_pct": rh_raw,
            "wind_speed_kmh": WIND_SPEED_MAP.get(wind_speed_raw, 10.0),
        })

    return results


def clear_cache():
    """Clear the weather cache (useful for testing)."""
    _cache.clear()
