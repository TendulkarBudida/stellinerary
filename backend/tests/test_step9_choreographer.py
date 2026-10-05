"""Test for Step 9: Choreographer specific edge cases (e.g. Orion 30-min window)."""

import pytest
from datetime import date, datetime, timedelta, timezone

from app.agents.choreographer import generate_schedule
from app.models import (
    CelestialEvent,
    EquipmentLevel,
    HorizonBlock,
    HorizonProfile,
    HourlyWeather,
    Site,
    SiteAccess,
    SiteAmenities,
    SiteWeatherForecast,
)


@pytest.fixture
def orionids_event():
    return CelestialEvent(
        id="orionids_test",
        name="Orionid Meteor Shower",
        type="meteor_shower",
        peak_date=date(2026, 10, 21),
        active_start=date(2026, 10, 2),
        active_end=date(2026, 11, 7),
        radiant_ra_deg=95.0,  # ~6.3 hours
        radiant_dec_deg=16.0,
        equipment=EquipmentLevel.naked_eye,
        min_bortle=5,
    )


@pytest.fixture
def blocked_site():
    """A site where the SE horizon (where Orion rises) is blocked up to 40 degrees.
    Orionids (RA 95, Dec 16) rises in the E/SE.
    """
    return Site(
        id="blocked_site",
        name="Blocked Site",
        state="Test",
        lat=13.0,
        lon=77.0,
        altitude_m=1000,
        bortle_class=4,
        horizon_profile=HorizonProfile(
            description="High mountain blocking East/SouthEast",
            blocked_directions=[
                HorizonBlock(azimuth_start=45, azimuth_end=135, max_blocked_altitude_deg=40)
            ],
        ),
        access=SiteAccess(road_quality="good", night_access=True),
        amenities=SiteAmenities(),
        city_distances_km={},
        best_months=[],
    )


@pytest.fixture
def narrow_weather():
    """Cloudy all night except a narrow window at midnight UTC."""
    obs_dt = datetime(2026, 10, 21, tzinfo=timezone.utc)
    hourly = []
    # 12:00 UTC to 00:00 UTC next day
    for h in range(12, 24):
        dt = obs_dt.replace(hour=h)
        # Cloud cover > 40% means not clear. Only 23:00 UTC is clear.
        cloud_cover = 10 if h == 23 else 90
        hourly.append(HourlyWeather(datetime_utc=dt, cloud_cover_pct=cloud_cover))
    
    return SiteWeatherForecast(
        site_id="blocked_site",
        fetched_at=obs_dt,
        hourly=hourly,
    )


def test_orion_scenario_30_min_window(orionids_event, blocked_site, narrow_weather):
    """
    Test Step 9 scenario: SE hill blocks until later, clouds exist.
    """
    obs_date = date(2026, 10, 21)
    schedule = generate_schedule(blocked_site, [orionids_event], narrow_weather, obs_date)
    
    meteor_entries = [e for e in schedule.entries if "Orionid" in e.title]
    
    # We should have at least one entry, and the dark adaptation note
    assert len(meteor_entries) >= 1
    
    # The dark adaptation note should be at the start of the night
    assert any("Dark Adaptation" in e.title for e in schedule.entries)
