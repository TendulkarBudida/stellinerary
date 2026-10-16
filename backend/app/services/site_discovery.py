"""
Dynamic observing-site discovery.

Replaces the static-only site list with live candidates found near the user:
- OpenStreetMap (Overpass API) supplies camp sites, viewpoints, and peaks.
- OpenTopoData supplies terrain elevations used to derive a horizon profile.
- Darkness is estimated from nearby populated places (city/town/village
  distance tiers) since no free point darkness API exists.

Everything here degrades gracefully: any provider failure returns fewer (or
zero) discovered sites, and an empty result means no usable site was found.
Results are marked unverified so the UI can say so honestly.
"""

import logging
import math
import time

import httpx

from app.models import (
    HorizonBlock,
    HorizonProfile,
    Site,
    SiteAccess,
    SiteAmenities,
)

logger = logging.getLogger(__name__)

OVERPASS_ENDPOINTS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]
OPENTOPO_URL = "https://api.opentopodata.org/v1/srtm90m"
REQUEST_TIMEOUT_SECONDS = 20
CACHE_TTL_SECONDS = 86400  # 1 day — terrain and map data barely change

_cache: dict[str, tuple[float, object]] = {}


def _cache_get(key: str):
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < CACHE_TTL_SECONDS:
        return entry[1]
    return None


def _cache_set(key: str, value: object) -> None:
    _cache[key] = (time.time(), value)


def clear_cache() -> None:
    """Clear discovery caches (useful for testing)."""
    _cache.clear()


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.asin(math.sqrt(a))


RETRY_DELAY_SECONDS = 2


def _post_overpass(endpoint: str, query: str) -> dict:
    """POST one Overpass query with a single retry (mirrors flap)."""
    last_error: Exception | None = None
    for attempt in (1, 2):
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                response = client.post(
                    endpoint,
                    content=query.encode(),
                    headers={"User-Agent": "stellinerary/1.0", "Content-Type": "text/plain"},
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            last_error = e
            logger.warning("Overpass %s attempt %d failed: %s", endpoint, attempt, e)
            if attempt == 1:
                time.sleep(RETRY_DELAY_SECONDS)
    raise last_error or Exception("Overpass request failed")


def discover_places(lat: float, lon: float, radius_m: int = 100000, limit: int = 15) -> list[dict]:
    """Find camp sites, viewpoints, and peaks near a location via Overpass."""
    cache_key = f"places:{round(lat, 2)},{round(lon, 2)},{radius_m}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    query = (
        "[out:json][timeout:25];("
        f'node["tourism"="camp_site"](around:{radius_m},{lat},{lon});'
        f'node["tourism"="camp_pitch"](around:{radius_m},{lat},{lon});'
        f'node["tourism"="viewpoint"](around:{radius_m},{lat},{lon});'
        f'node["natural"="peak"](around:{radius_m},{lat},{lon});'
        ");out center 60;"
    )
    last_error: Exception | None = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            elements = _post_overpass(endpoint, query).get("elements", [])
            places = [
                {
                    "name": (el.get("tags") or {}).get("name", "Unnamed site"),
                    "lat": el.get("lat"),
                    "lon": el.get("lon"),
                    "kind": (el.get("tags") or {}).get("tourism") or (el.get("tags") or {}).get("natural", "site"),
                }
                for el in elements
                if el.get("lat") is not None and el.get("lon") is not None
            ][:limit]
            logger.info("Discovered %d places near (%.2f, %.2f) via %s", len(places), lat, lon, endpoint)
            _cache_set(cache_key, places)
            return places
        except Exception as e:
            logger.warning("Overpass endpoint %s failed: %s", endpoint, e)
            last_error = e
    logger.warning("All Overpass endpoints failed; no discovered sites (%s)", last_error)
    return []


def fetch_elevations(points: list[tuple[float, float]]) -> dict[tuple[float, float], float | None]:
    """Batch-fetch terrain elevations (meters) for lat/lon points."""
    results: dict[tuple[float, float], float | None] = {point: None for point in points}
    uncached = [point for point in points if _cache_get(f"elev:{round(point[0], 4)},{round(point[1], 4)}") is None]
    for point in points:
        cached = _cache_get(f"elev:{round(point[0], 4)},{round(point[1], 4)}")
        if cached is not None:
            results[point] = cached  # type: ignore[assignment]

    for offset in range(0, len(uncached), 100):
        batch = uncached[offset:offset + 100]
        locations = "|".join(f"{lat},{lon}" for lat, lon in batch)
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                response = client.get(
                    OPENTOPO_URL,
                    params={"locations": locations},
                    headers={"User-Agent": "stellinerary/1.0"},
                )
                response.raise_for_status()
                for entry, point in zip(response.json().get("results", []), batch):
                    elevation = entry.get("elevation")
                    results[point] = elevation
                    _cache_set(f"elev:{round(point[0], 4)},{round(point[1], 4)}", elevation)
        except Exception as e:
            logger.warning("OpenTopoData batch failed: %s", e)
            return results
    return results


def build_horizon_profile(site_lat: float, site_lon: float, site_elevation_m: float | None = None) -> HorizonProfile:
    """Derive horizon blockage arcs from sampled terrain elevations.

    Samples 24 azimuths at 2/5/10 km, converts the highest terrain rise at
    each azimuth into a blocking altitude, then merges adjacent azimuths
    above 5° into HorizonBlocks.
    """
    azimuths = list(range(0, 360, 15))
    distances_km = (2.0, 5.0, 10.0)
    samples: list[tuple[float, float, float]] = []  # (azimuth, distance_km, lat, lon)
    coords: list[tuple[float, float]] = []
    for azimuth in azimuths:
        bearing = math.radians(azimuth)
        for distance in distances_km:
            delta = distance / 6371.0
            lat1, lon1 = math.radians(site_lat), math.radians(site_lon)
            lat2 = math.asin(math.sin(lat1) * math.cos(delta) + math.cos(lat1) * math.sin(delta) * math.cos(bearing))
            lon2 = lon1 + math.atan2(
                math.sin(bearing) * math.sin(delta) * math.cos(lat1),
                math.cos(delta) - math.sin(lat1) * math.sin(lat2),
            )
            point = (round(math.degrees(lat2), 4), round(math.degrees(lon2), 4))
            samples.append((azimuth, distance, point[0], point[1]))
            coords.append(point)

    site_point = (round(site_lat, 4), round(site_lon, 4))
    elevations = fetch_elevations([site_point, *coords])
    if site_elevation_m is None:
        site_elevation_m = elevations.get(site_point)
    base = site_elevation_m if site_elevation_m is not None else 0.0

    blocking: dict[int, float] = {}
    for azimuth, distance, lat, lon in samples:
        elevation = elevations.get((lat, lon))
        if elevation is None:
            continue
        rise = elevation - base
        if rise <= 0:
            continue
        angle = math.degrees(math.atan2(rise, distance * 1000))
        blocking[azimuth] = max(blocking.get(azimuth, 0.0), angle)

    # Merge adjacent blocked azimuths (>= 5°) into arcs.
    blocks: list[HorizonBlock] = []
    run_start: int | None = None
    run_peak = 0.0

    def _close_run(end_azimuth: int) -> None:
        nonlocal run_start, run_peak
        if run_start is not None:
            blocks.append(HorizonBlock(
                azimuth_start=int(run_start % 360),
                azimuth_end=int(end_azimuth % 360),
                max_blocked_altitude_deg=int(round(run_peak)),
            ))
            run_start, run_peak = None, 0.0

    ordered = sorted(blocking)
    for azimuth in ordered:
        if blocking[azimuth] >= 5.0:
            run_start = azimuth if run_start is None else run_start
            run_peak = max(run_peak, blocking[azimuth])
        else:
            _close_run(azimuth - 15)
    if ordered:
        _close_run(ordered[-1])

    if not blocks:
        return HorizonProfile(description="Terrain-derived horizon: open in all directions (estimated).")
    return HorizonProfile(
        description="Terrain-derived horizon from elevation sampling (estimated).",
        blocked_directions=blocks,
    )


def estimate_bortle(site_lat: float, site_lon: float, places: list[dict] | None = None) -> int:
    """Estimate Bortle class from distance to the nearest populated place.

    Uses OSM place tiers as a light-dome proxy: cities dominate to ~80 km,
    towns to ~30 km. Unknown data (provider failure) yields a neutral 5;
    a successful query with no settlements in range yields 3.
    """
    if places is None:
        places = nearby_populated_places(site_lat, site_lon)
    if places is None:
        return 5
    if not places:
        return 3
    best = 9
    for place in places:
        tier = (place.get("tier") or "town").lower()
        distance = _haversine_km(site_lat, site_lon, place["lat"], place["lon"])
        if tier == "city":
            candidate = 3 if distance > 80 else 5 if distance > 40 else 7 if distance > 15 else 9
        else:
            candidate = 3 if distance > 30 else 5 if distance > 12 else 7
        best = min(best, candidate)
    return best


def nearby_populated_places(lat: float, lon: float, radius_m: int = 120000) -> list[dict] | None:
    """Find cities/towns near a location for darkness estimation.

    Returns None when all providers fail (unknown darkness), or a
    possibly-empty list on success.
    """
    cache_key = f"pop:{round(lat, 2)},{round(lon, 2)}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    query = (
        "[out:json][timeout:25];("
        f'node["place"="city"](around:{radius_m},{lat},{lon});'
        f'node["place"="town"](around:{radius_m},{lat},{lon});'
        ");out 60;"
    )
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            places = [
                {
                    "lat": el.get("lat"),
                    "lon": el.get("lon"),
                    "tier": (el.get("tags") or {}).get("place", "town"),
                }
                for el in _post_overpass(endpoint, query).get("elements", [])
                if el.get("lat") is not None and el.get("lon") is not None
            ]
            _cache_set(cache_key, places)
            return places
        except Exception as e:
            logger.warning("Overpass populated-places query failed on %s: %s", endpoint, e)
    return None


def place_to_site(place: dict, state: str = "") -> Site:
    """Convert a discovered place into a Site marked unverified."""
    lat, lon = place["lat"], place["lon"]
    elevations = fetch_elevations([(round(lat, 4), round(lon, 4))])
    altitude = elevations.get((round(lat, 4), round(lon, 4)))
    return Site(
        id=f"discovered-{round(lat, 4)}-{round(lon, 4)}",
        name=place.get("name") or "Unnamed site",
        state=state,
        lat=lat,
        lon=lon,
        altitude_m=int(altitude) if altitude is not None else 0,
        bortle_class=estimate_bortle(lat, lon),
        horizon_profile=build_horizon_profile(lat, lon, altitude),
        access=SiteAccess(
            road_quality="unknown",
            night_access=True,
            night_access_notes="Unverified community data — confirm night access and permissions before travelling.",
            parking=False,
            entry_fee=False,
        ),
        amenities=SiteAmenities(),
        city_distances_km={},
        best_months=[],
        notes="Discovered from OpenStreetMap; darkness and horizon are estimated, not surveyed.",
        source="discovered",
    )
