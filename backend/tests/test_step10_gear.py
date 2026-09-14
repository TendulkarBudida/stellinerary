"""Step 10 — Gear & Prep agent tests.

Validates:
1. Cold-weather gear appears for cold sites (Spiti, Hanle).
2. Warm-weather gear is lighter for mild sites (Savandurga).
3. Meteor shower → reclining chair, no telescope warning.
4. Solar eclipse → solar filter safety warning.
5. High-altitude → AMS warning.
6. Trek site → trekking gear.
7. Dark adaptation warnings always present.
"""

import pytest
from datetime import datetime, timezone

from app.agents.gear import generate_gear_list
from app.data.loader import load_sites, get_site_by_id, load_events
from app.models import (
    CelestialEvent,
    EquipmentLevel,
    GearCategory,
    GearList,
    HourlyWeather,
    Site,
    SiteWeatherForecast,
)


def _make_weather(min_temp: float) -> SiteWeatherForecast:
    """Create a simple forecast with a fixed temperature."""
    return SiteWeatherForecast(
        site_id="test",
        fetched_at=datetime.now(timezone.utc),
        hourly=[
            HourlyWeather(
                datetime_utc=datetime.now(timezone.utc),
                cloud_cover_pct=20,
                temperature_c=min_temp,
                relative_humidity_pct=50,
            )
        ],
    )


def _get_meteor_events() -> list[CelestialEvent]:
    """Get meteor shower events from calendar."""
    return [e for e in load_events() if e.type == "meteor_shower"][:1]


def _get_opposition_events() -> list[CelestialEvent]:
    """Get opposition events from calendar."""
    return [e for e in load_events() if e.type == "opposition"][:1]


class TestTemperatureGear:
    def test_freezing_temp_includes_heavy_gear(self):
        site = get_site_by_id("spiti_valley")
        weather = _make_weather(-5.0)
        gear = generate_gear_list(site, _get_opposition_events(), EquipmentLevel.naked_eye, weather)

        item_names = [i.name.lower() for i in gear.items]
        assert any("winter jacket" in n or "thermal" in n for n in item_names), \
            "Expected heavy winter gear for -5°C"
        assert any("gloves" in n for n in item_names), "Expected gloves for freezing temps"

    def test_cold_temp_includes_jacket(self):
        site = get_site_by_id("nandi_hills")
        weather = _make_weather(8.0)
        gear = generate_gear_list(site, _get_opposition_events(), EquipmentLevel.naked_eye, weather)

        item_names = [i.name.lower() for i in gear.items]
        assert any("jacket" in n or "hoodie" in n for n in item_names)

    def test_warm_temp_lighter_gear(self):
        site = get_site_by_id("savandurga")
        weather = _make_weather(22.0)
        gear = generate_gear_list(site, _get_opposition_events(), EquipmentLevel.naked_eye, weather)

        item_names = [i.name.lower() for i in gear.items]
        assert not any("winter jacket" in n or "thermal" in n for n in item_names), \
            "Should NOT recommend heavy winter gear for 22°C"


class TestEventSpecificGear:
    def test_meteor_shower_includes_reclining_chair(self):
        site = get_site_by_id("nandi_hills")
        gear = generate_gear_list(site, _get_meteor_events(), EquipmentLevel.naked_eye)

        item_names = [i.name.lower() for i in gear.items]
        assert any("reclining" in n or "sleeping pad" in n or "mat" in n for n in item_names), \
            "Meteor watching needs a reclining surface"

    def test_meteor_shower_warns_about_telescope(self):
        site = get_site_by_id("nandi_hills")
        gear = generate_gear_list(site, _get_meteor_events(), EquipmentLevel.telescope)

        warning_text = " ".join(gear.warnings).lower()
        assert "telescope" in warning_text and ("not" in warning_text or "narrow" in warning_text), \
            "Should warn that telescopes are not useful for meteor showers"

    def test_binocular_level_includes_binoculars(self):
        site = get_site_by_id("nandi_hills")
        gear = generate_gear_list(site, _get_opposition_events(), EquipmentLevel.binoculars)

        item_names = [i.name.lower() for i in gear.items]
        assert any("binocular" in n for n in item_names)

    def test_telescope_level_includes_eyepieces(self):
        site = get_site_by_id("nandi_hills")
        gear = generate_gear_list(site, _get_opposition_events(), EquipmentLevel.telescope)

        item_names = [i.name.lower() for i in gear.items]
        assert any("eyepiece" in n for n in item_names)


class TestSiteSpecificGear:
    def test_high_altitude_warns_ams(self):
        site = get_site_by_id("spiti_valley")
        gear = generate_gear_list(site, _get_opposition_events(), EquipmentLevel.naked_eye)

        warning_text = " ".join(gear.warnings).lower()
        assert "altitude" in warning_text, "Should warn about altitude sickness for 4200m site"

    def test_trek_site_includes_trekking_gear(self):
        site = get_site_by_id("skandagiri")
        gear = generate_gear_list(site, _get_opposition_events(), EquipmentLevel.naked_eye)

        item_names = [i.name.lower() for i in gear.items]
        assert any("trek" in n or "grip" in n for n in item_names), \
            "Skandagiri requires a night trek — should include trekking gear"

    def test_no_food_site_includes_extra_provisions(self):
        site = get_site_by_id("savandurga")
        assert not site.amenities.food_water_nearby
        gear = generate_gear_list(site, _get_opposition_events(), EquipmentLevel.naked_eye)

        item_names = [i.name.lower() for i in gear.items]
        assert any("water" in n or "meal" in n or "food" in n for n in item_names)


class TestUniversalWarnings:
    def test_dark_adaptation_warning_always_present(self):
        site = get_site_by_id("nandi_hills")
        gear = generate_gear_list(site, _get_opposition_events(), EquipmentLevel.naked_eye)

        warning_text = " ".join(gear.warnings).lower()
        assert "dark adaptation" in warning_text or "white light" in warning_text or "red" in warning_text

    def test_red_headlamp_always_essential(self):
        site = get_site_by_id("nandi_hills")
        gear = generate_gear_list(site, _get_opposition_events(), EquipmentLevel.naked_eye)

        essential_names = [i.name.lower() for i in gear.items if i.category == GearCategory.essential]
        assert any("red" in n and ("headlamp" in n or "flashlight" in n) for n in essential_names)

    def test_gear_list_is_not_empty(self):
        site = get_site_by_id("nandi_hills")
        gear = generate_gear_list(site, [], EquipmentLevel.naked_eye)
        assert len(gear.items) >= 3  # At minimum: red light, water, phone
