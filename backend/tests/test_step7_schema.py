"""
Step 7 tests — Shared state schema validation.
"""

import pytest
from datetime import date, datetime, timezone
from pydantic import ValidationError

from app.models.plan_state import (
    EquipmentLevel,
    PlanState,
    RankedEvent,
    ScheduleSlot,
    SiteInfo,
    UserInput,
    WeatherWindow,
)


def _user_input() -> UserInput:
    return UserInput(
        lat=12.97,
        lon=77.59,
        date_start=date(2026, 12, 13),
        date_end=date(2026, 12, 14),
        equipment_level=EquipmentLevel.binoculars,
        city_hint="Bangalore",
    )


def test_plan_state_starts_empty():
    state = PlanState(user_input=_user_input())
    assert state.site is None
    assert state.ranked_events == []
    assert state.schedule == []
    assert state.gear_list == []
    assert not state.contingency_triggered


def test_plan_state_log():
    state = PlanState(user_input=_user_input())
    state.log("Curator: 3 events found")
    state.log("Choreographer: 4 slots scheduled")
    assert len(state.pipeline_log) == 2
    assert "Curator" in state.pipeline_log[0]


def test_site_info_bortle_range():
    site = SiteInfo(
        id="nandi_hills",
        name="Nandi Hills",
        lat=13.37,
        lon=77.68,
        altitude_m=1478,
        bortle_class=4,
        horizon_blocks={"SE": 15, "S": 10},
    )
    assert site.bortle_class == 4
    assert site.horizon_blocks["SE"] == 15


def test_weather_window_is_clear():
    clear = WeatherWindow(
        site_id="nandi_hills",
        start=datetime(2026, 12, 13, 18, 0, tzinfo=timezone.utc),
        end=datetime(2026, 12, 14, 0, 0, tzinfo=timezone.utc),
        cloud_cover_pct=15.0,
        seeing=6,
        transparency=6,
        temperature_c=11.0,
        humidity_pct=40.0,
    )
    assert clear.is_clear is True

    cloudy = clear.model_copy(update={"cloud_cover_pct": 70.0})
    assert cloudy.is_clear is False


def test_ranked_event_defaults():
    ev = RankedEvent(
        id="geminids_2026",
        name="Geminid Meteor Shower",
        type="meteor_shower",
        peak_datetime=datetime(2026, 12, 13, 20, 0, tzinfo=timezone.utc),
    )
    assert ev.priority_stars == 0
    assert ev.moon_interference_score == 0.0
    assert ev.zhr is None


def test_schedule_slot_dark_adaptation_flag():
    slot = ScheduleSlot(
        start=datetime(2026, 12, 13, 20, 0, tzinfo=timezone.utc),
        end=datetime(2026, 12, 13, 20, 20, tzinfo=timezone.utc),
        object_name="[Dark Adaptation]",
        note="Avoid all white light for the first 20 minutes.",
        is_dark_adaptation=True,
    )
    assert slot.is_dark_adaptation is True


def test_user_input_rejects_missing_fields():
    with pytest.raises(ValidationError):
        UserInput(lat=12.97, lon=77.59)  # missing date fields
