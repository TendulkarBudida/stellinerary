"""
Location Scout Agent.

Given user coordinates (or a city name), ranks the curated dark-sky sites by:
1. Distance (closer is better, but diminishing returns — a Bortle 1 site 500km away
   can beat a Bortle 5 site 50km away)
2. Bortle class (lower = darker = better)
3. Weather forecast (clear skies at the site)
4. Travel time estimate (affects available observation window)

Produces a ranked list of RankedSite objects with scores and reasoning.
"""

import logging
import math

from app.agents.weather import get_weather_forecast
from app.data.loader import load_sites
from app.models import RankedSite, Site, SiteWeatherForecast

logger = logging.getLogger(__name__)

# ── Scoring weights ───────────────────────────────────────────────────
# These control the relative importance of each factor.

WEIGHT_BORTLE = 0.40   # Sky darkness is the primary reason you're driving out
WEIGHT_WEATHER = 0.35  # Clear skies are non-negotiable for observing
WEIGHT_DISTANCE = 0.25 # Distance matters but less than sky quality

# Average driving speed assumed for travel time estimates (km/h)
# Conservative for Indian roads, especially hill stations at night
AVG_SPEED_KMH = 40


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in km."""
    R = 6371  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def _bortle_score(bortle: int) -> float:
    """
    Convert Bortle class (1-9) to a 0-1 score where 1 = darkest.

    Uses an exponential curve so the difference between Bortle 1 and 3
    is felt more than between Bortle 7 and 9 (the jump from urban to
    suburban sky doesn't matter much; the jump from rural to pristine does).
    """
    # Bortle 1 → 1.0, Bortle 9 → 0.0, exponential decay
    return max(0.0, min(1.0, math.exp(-0.3 * (bortle - 1))))


def _distance_score(distance_km: float) -> float:
    """
    Convert distance to a 0-1 score where 1 = closest.

    Uses a sigmoid-like decay: up to ~50 km is "close" (score ~0.9),
    ~200 km is "moderate" (score ~0.5), >500 km is "far" (score ~0.1).
    """
    # Logistic decay centered at 200 km, steepness 0.01
    return 1.0 / (1.0 + math.exp(0.015 * (distance_km - 200)))


def _weather_score_from_forecast(forecast: SiteWeatherForecast) -> float:
    """
    Convert a weather forecast into a 0-1 score.

    Focuses on the proportion of clear hours (cloud cover ≤ 30%).
    If no data is available (API failure), returns a neutral 0.5
    so weather doesn't dominate the ranking.
    """
    if not forecast.hourly:
        return 0.5  # neutral — don't penalize for unknown weather

    clear_count = sum(1 for h in forecast.hourly if h.cloud_cover_pct <= 30)
    return clear_count / len(forecast.hourly)


def _estimate_travel_time_min(distance_km: float) -> int:
    """Rough travel time estimate in minutes."""
    return round(distance_km / AVG_SPEED_KMH * 60)


async def rank_sites(
    user_lat: float,
    user_lon: float,
    max_results: int = 5,
    fetch_weather: bool = True,
) -> list[RankedSite]:
    """
    Rank all curated sites by suitability for the user's location.

    Args:
        user_lat, user_lon: User's coordinates.
        max_results: Maximum number of sites to return (top N).
        fetch_weather: If True, fetch weather for each site. Set False for
                      fast ranking without weather (e.g., for testing).

    Returns:
        List of RankedSite objects, sorted by overall_score descending.
    """
    sites = load_sites()
    ranked: list[RankedSite] = []

    for site in sites:
        distance = _haversine_km(user_lat, user_lon, site.lat, site.lon)
        travel_min = _estimate_travel_time_min(distance)

        bortle_s = _bortle_score(site.bortle_class)
        distance_s = _distance_score(distance)

        # Weather scoring
        weather_s = 0.5  # default neutral
        if fetch_weather:
            forecast = await get_weather_forecast(site.id, site.lat, site.lon)
            weather_s = _weather_score_from_forecast(forecast)

        overall = (
            WEIGHT_BORTLE * bortle_s +
            WEIGHT_WEATHER * weather_s +
            WEIGHT_DISTANCE * distance_s
        )

        # Build human-readable reason
        reason_parts = []
        if bortle_s >= 0.7:
            reason_parts.append(f"Excellent darkness (Bortle {site.bortle_class})")
        elif bortle_s >= 0.4:
            reason_parts.append(f"Good darkness (Bortle {site.bortle_class})")
        else:
            reason_parts.append(f"Moderate light pollution (Bortle {site.bortle_class})")

        reason_parts.append(f"{distance:.0f} km away (~{travel_min} min drive)")

        if weather_s >= 0.7:
            reason_parts.append("Clear skies forecast ✓")
        elif weather_s >= 0.4:
            reason_parts.append("Mixed weather — check closer to the date")
        elif weather_s == 0.5 and not fetch_weather:
            reason_parts.append("Weather not checked")
        else:
            reason_parts.append("⚠️ Cloudy forecast — consider alternatives")

        if not site.access.night_access:
            reason_parts.append("⚠️ Night access restricted")
            overall *= 0.5  # heavy penalty

        ranked.append(RankedSite(
            site=site,
            distance_km=round(distance, 1),
            travel_time_estimate_min=travel_min,
            weather_score=round(weather_s, 3),
            bortle_score=round(bortle_s, 3),
            overall_score=round(overall, 3),
            ranking_reason=". ".join(reason_parts) + ".",
        ))

    # Sort by overall score, descending
    ranked.sort(key=lambda r: r.overall_score, reverse=True)

    return ranked[:max_results]
