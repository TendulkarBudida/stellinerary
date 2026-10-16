"""Shared test fixtures: deterministic observing sites (no network, no static files).

These stand in for live-discovered OSM sites. Distances from Bangalore
(12.9716, 77.5946):
- Close Camp: ~30 km (~45 min) — inside a 60-minute limit.
- Mid Ridge: ~45 km (~68 min) — inside a 120-minute limit.
- Far Valley: ~116 km (~174 min) — needs a generous limit.
"""

from app.models import (
    HorizonBlock,
    HorizonProfile,
    Site,
    SiteAccess,
    SiteAmenities,
)


def make_site(
    id: str,
    name: str,
    lat: float,
    lon: float,
    altitude_m: int = 1000,
    bortle_class: int = 4,
    blocked: list[tuple[int, int, int]] | None = None,
    trek: bool = False,
    food_water: bool = False,
    night_access: bool = True,
) -> Site:
    return Site(
        id=id,
        name=name,
        state="Testland",
        lat=lat,
        lon=lon,
        altitude_m=altitude_m,
        bortle_class=bortle_class,
        horizon_profile=HorizonProfile(
            description="test horizon",
            blocked_directions=[
                HorizonBlock(azimuth_start=s, azimuth_end=e, max_blocked_altitude_deg=a)
                for s, e, a in (blocked or [])
            ],
        ),
        access=SiteAccess(
            road_quality="good",
            night_access=night_access,
            night_access_notes="Night trek to the point." if trek else "Open access.",
        ),
        amenities=SiteAmenities(food_water_nearby=food_water),
        source="discovered",
    )


def close_camp() -> Site:
    return make_site("close-camp", "Close Camp", 12.8964, 77.3270, altitude_m=751, bortle_class=4)


def mid_ridge() -> Site:
    return make_site(
        "mid-ridge", "Mid Ridge", 13.3702, 77.6835, altitude_m=1478, bortle_class=4,
        blocked=[(120, 170, 10)],
    )


def far_valley() -> Site:
    return make_site("far-valley", "Far Valley", 13.6604, 78.3977, altitude_m=1290, bortle_class=3)


def high_peak() -> Site:
    return make_site("high-peak", "High Peak", 32.3160, 78.0080, altitude_m=4200, bortle_class=1)


def trek_point() -> Site:
    return make_site("trek-point", "Trek Point", 13.4246, 77.6891, altitude_m=1450, bortle_class=4, trek=True)


def flat_plain() -> Site:
    return make_site("flat-plain", "Flat Plain", 23.7337, 69.8597, altitude_m=20, bortle_class=2)


def savandurga_like() -> Site:
    return make_site(
        "savandurga-like", "Savandurga-like Base", 12.9192, 77.2929, altitude_m=795, bortle_class=5,
        blocked=[(50, 120, 25)],
    )


def fixture_sites() -> list[Site]:
    return [close_camp(), mid_ridge(), far_valley(), high_peak()]


def fixture_places() -> list[dict]:
    return [
        {"name": s.name, "lat": s.lat, "lon": s.lon, "kind": "camp_site"}
        for s in fixture_sites()
    ]
