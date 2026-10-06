"""Constraint-aware, event-aware observing-site ranking."""

import asyncio
import math
from datetime import date, datetime, timezone

from app.agents.weather import get_weather_forecast
from app.data.loader import load_sites
from app.models import CelestialEvent, RankedSite, Site, SiteWeatherForecast
from app.services.ephemeris import compute_altitude_azimuth, compute_altitude_azimuth_radec

WEIGHT_EVENT_VISIBILITY = 0.30
WEIGHT_WEATHER = 0.25
WEIGHT_BORTLE = 0.25
WEIGHT_DISTANCE = 0.20
AVG_SPEED_KMH = 40
DEFAULT_SHORTLIST_SIZE = 5


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.asin(math.sqrt(a))


def _bortle_score(bortle: int) -> float:
    return max(0.0, min(1.0, math.exp(-0.3 * (bortle - 1))))


def _distance_score(distance_km: float) -> float:
    return 1.0 / (1.0 + math.exp(0.015 * (distance_km - 200)))


def _estimate_travel_time_min(distance_km: float) -> int:
    return round(distance_km / AVG_SPEED_KMH * 60)


def _horizon_altitude(site: Site, azimuth: float) -> float:
    azimuth %= 360
    for block in site.horizon_profile.blocked_directions:
        in_arc = block.azimuth_start <= azimuth <= block.azimuth_end if block.azimuth_start <= block.azimuth_end else azimuth >= block.azimuth_start or azimuth <= block.azimuth_end
        if in_arc:
            return float(block.max_blocked_altitude_deg)
    return 0.0


def _event_visibility_score(site: Site, events: list[CelestialEvent] | None, dates: list[date] | None) -> float:
    """Score whether priority targets clear this site's terrain on requested nights."""
    if not events or not dates:
        return 0.5
    scores: list[float] = []
    for event in events[:5]:
        best = 0.0
        for night in dates:
            for hour in (13, 16, 19, 22):  # 18:30--03:30 IST
                moment = datetime(night.year, night.month, night.day, hour, 30, tzinfo=timezone.utc)
                try:
                    if event.radiant_ra_deg is not None and event.radiant_dec_deg is not None:
                        position = compute_altitude_azimuth_radec(event.radiant_ra_deg, event.radiant_dec_deg, site.lat, site.lon, moment)
                    elif event.target_object:
                        position = compute_altitude_azimuth(event.target_object, site.lat, site.lon, moment)
                    else:
                        continue
                except ValueError:
                    continue
                altitude = position["altitude_deg"]
                if altitude > _horizon_altitude(site, position["azimuth_deg"]):
                    best = max(best, min(1.0, altitude / 75.0))
        scores.append(best)
    return round(sum(scores) / len(scores), 3) if scores else 0.5


def _weather_score_from_forecast(forecast: SiteWeatherForecast | None) -> float:
    if not forecast or not forecast.hourly:
        return 0.5
    return sum(hour.cloud_cover_pct <= 30 for hour in forecast.hourly) / len(forecast.hourly)


async def rank_sites(
    user_lat: float, user_lon: float, max_results: int = 5, fetch_weather: bool = True, *,
    events: list[CelestialEvent] | None = None, observation_dates: list[date] | None = None,
    max_travel_minutes: int | None = None, max_distance_km: float | None = None,
    overnight_allowed: bool = False, shortlist_size: int = DEFAULT_SHORTLIST_SIZE,
) -> list[RankedSite]:
    """Filter cheaply, fetch a bounded weather shortlist concurrently, then score."""
    candidates: list[tuple[Site, float, int, float, float]] = []
    for site in load_sites():
        distance = _haversine_km(user_lat, user_lon, site.lat, site.lon)
        travel_minutes = _estimate_travel_time_min(distance)
        if (max_distance_km is not None and distance > max_distance_km) or (max_travel_minutes is not None and travel_minutes > max_travel_minutes):
            continue
        if not overnight_allowed and travel_minutes > 360:
            continue
        candidates.append((site, distance, travel_minutes, _bortle_score(site.bortle_class), _distance_score(distance)))

    candidates.sort(key=lambda item: WEIGHT_BORTLE * item[3] + WEIGHT_DISTANCE * item[4], reverse=True)
    shortlist = candidates[:max(shortlist_size, max_results)]
    forecasts: dict[str, SiteWeatherForecast | None] = {}
    if fetch_weather:
        results = await asyncio.gather(*(get_weather_forecast(site.id, site.lat, site.lon) for site, *_ in shortlist), return_exceptions=True)
        for (site, *_), result in zip(shortlist, results):
            forecasts[site.id] = result if isinstance(result, SiteWeatherForecast) else None

    ranked: list[RankedSite] = []
    for site, distance, travel_minutes, bortle_s, distance_s in shortlist:
        weather_s = _weather_score_from_forecast(forecasts.get(site.id)) if fetch_weather else 0.5
        event_s = _event_visibility_score(site, events, observation_dates)
        overall = WEIGHT_EVENT_VISIBILITY * event_s + WEIGHT_WEATHER * weather_s + WEIGHT_BORTLE * bortle_s + WEIGHT_DISTANCE * distance_s
        if not site.access.night_access:
            overall *= 0.5
        reasons = [f"Bortle {site.bortle_class}", f"{distance:.0f} km away (~{travel_minutes} min drive)"]
        reasons.append("Priority targets clear the site horizon" if event_s >= 0.6 else "Some priority targets may be low or terrain-blocked")
        reasons.append("Clear-weather window available" if weather_s >= 0.7 else "Weather is mixed or unverified")
        if not site.access.night_access:
            reasons.append("Night access restricted")
        ranked.append(RankedSite(
            site=site, distance_km=round(distance, 1), travel_time_estimate_min=travel_minutes,
            weather_score=round(weather_s, 3), bortle_score=round(bortle_s, 3), event_visibility_score=event_s,
            overall_score=round(overall, 3),
            score_components={"event_visibility": event_s, "weather": round(weather_s, 3), "bortle": round(bortle_s, 3), "distance": round(distance_s, 3)},
            ranking_reason=". ".join(reasons) + ".",
        ))
    ranked.sort(key=lambda item: item.overall_score, reverse=True)
    return ranked[:max_results]
