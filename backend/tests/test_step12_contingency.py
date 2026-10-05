"""Test for Step 12: Contingency Logic"""

import pytest
from datetime import date, datetime, timedelta, timezone

from app.models import (
    ExpeditionPlan,
    PlanRequest,
    Site,
    HorizonProfile,
    SiteAccess,
    SiteAmenities,
    SiteWeatherForecast,
    HourlyWeather,
    ObservationSchedule,
    ScheduleEntry,
    EquipmentLevel,
    CelestialEvent
)
from app.agents.contingency import check_contingency, CLOUD_THRESHOLD

@pytest.fixture
def mock_site():
    return Site(
        id="mock_site",
        name="Mock Site",
        state="Test",
        lat=13.0,
        lon=77.0,
        altitude_m=1000,
        bortle_class=4,
        horizon_profile=HorizonProfile(description="Clear", blocked_directions=[]),
        access=SiteAccess(road_quality="good", night_access=True),
        amenities=SiteAmenities(),
        city_distances_km={},
        best_months=[]
    )

@pytest.fixture
def base_plan(mock_site):
    """A baseline ExpeditionPlan with a clear weather schedule."""
    obs_dt = datetime(2026, 12, 14, tzinfo=timezone.utc)
    
    # Let's say the original schedule planned an event at 21:30 local time dependent on weather.
    # 21:30 IST is 16:00 UTC.
    schedule = ObservationSchedule(
        entries=[
            ScheduleEntry(
                time_local="21:30",
                title="Observe Geminids",
                is_weather_dependent=True
            )
        ]
    )
    
    event = CelestialEvent(
        id="geminids",
        name="Geminids",
        type="meteor_shower",
        peak_date=date(2026, 12, 14),
        active_start=date(2026, 12, 1),
        active_end=date(2026, 12, 20)
    )
    
    plan = ExpeditionPlan(
        request=PlanRequest(
            user_lat=13.0,
            user_lon=77.0,
            date_start=date(2026, 12, 14),
            date_end=date(2026, 12, 15),
            equipment_level=EquipmentLevel.naked_eye
        ),
        chosen_site=mock_site,
        ranked_events=[event],
        schedule=schedule
    )
    return plan


def test_contingency_no_change_when_weather_good(base_plan):
    """If new weather is below cloud threshold, plan is unchanged."""
    obs_dt = datetime(2026, 12, 14, tzinfo=timezone.utc)
    hourly = [
        HourlyWeather(datetime_utc=obs_dt.replace(hour=h), cloud_cover_pct=20) 
        for h in range(12, 24)
    ]
    good_weather = SiteWeatherForecast(
        site_id="mock_site", fetched_at=obs_dt, hourly=hourly
    )

    changed, new_plan = check_contingency(base_plan, good_weather)
    assert not changed
    assert new_plan.contingency_note is None


def test_contingency_triggers_when_clouds_over_threshold(base_plan):
    """If new weather exceeds cloud threshold during a scheduled window, we re-plan."""
    # The event is scheduled at 21:30 local -> ~16:00 UTC
    obs_dt = datetime(2026, 12, 14, tzinfo=timezone.utc)
    hourly = []
    for h in range(12, 24):
        # Spike clouds to 80% specifically at 16:00 UTC
        cc = 80 if h == 16 else 10
        hourly.append(HourlyWeather(datetime_utc=obs_dt.replace(hour=h), cloud_cover_pct=cc))
        
    bad_weather = SiteWeatherForecast(
        site_id="mock_site", fetched_at=obs_dt, hourly=hourly
    )

    changed, new_plan = check_contingency(base_plan, bad_weather)
    
    assert changed is True
    assert new_plan.contingency_note == "NOTICE: Schedule has been updated due to worsening weather conditions."
    assert new_plan.weather_forecast == bad_weather
    # verify schedule was regenerated 
    assert new_plan.schedule is not None
