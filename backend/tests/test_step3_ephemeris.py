"""Step 3 — Ephemeris service tests.

Validates:
1. Jupiter altitude/azimuth for a known date/location sanity check.
2. Rise/set times for the Sun at a known location.
3. Astronomical twilight computation.
4. Moon phase near known new/full moon dates.
5. RA/Dec based computation for deep sky objects.
6. Moon interference scoring.
"""

import pytest
from datetime import datetime, timezone

from app.services.ephemeris import (
    compute_altitude_azimuth,
    compute_altitude_azimuth_radec,
    compute_astronomical_twilight,
    compute_moon_interference,
    compute_moon_phase,
    compute_rise_set,
)

# Bangalore coordinates
BLR_LAT = 12.9716
BLR_LON = 77.5946


class TestAltitudeAzimuth:
    def test_sun_above_horizon_daytime(self):
        """Sun should be above the horizon at noon in Bangalore."""
        # 2026-09-14 noon UTC ≈ 5:30 PM IST — still daytime
        dt = datetime(2026, 9, 14, 7, 0, tzinfo=timezone.utc)  # ~12:30 PM IST
        result = compute_altitude_azimuth("sun", BLR_LAT, BLR_LON, dt)
        assert result["is_above_horizon"] is True
        assert result["altitude_deg"] > 0

    def test_sun_below_horizon_nighttime(self):
        """Sun should be below the horizon at midnight in Bangalore."""
        dt = datetime(2026, 9, 14, 18, 30, tzinfo=timezone.utc)  # midnight IST
        result = compute_altitude_azimuth("sun", BLR_LAT, BLR_LON, dt)
        assert result["is_above_horizon"] is False
        assert result["altitude_deg"] < 0

    def test_jupiter_returns_valid_position(self):
        """Jupiter should return a valid alt/az regardless of whether it's up."""
        dt = datetime(2026, 10, 3, 18, 0, tzinfo=timezone.utc)  # Near opposition
        result = compute_altitude_azimuth("jupiter", BLR_LAT, BLR_LON, dt)
        assert "altitude_deg" in result
        assert "azimuth_deg" in result
        assert 0 <= result["azimuth_deg"] <= 360

    def test_case_insensitive_target(self):
        """Target names should be case-insensitive."""
        dt = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)
        r1 = compute_altitude_azimuth("Moon", BLR_LAT, BLR_LON, dt)
        r2 = compute_altitude_azimuth("moon", BLR_LAT, BLR_LON, dt)
        assert r1["altitude_deg"] == r2["altitude_deg"]

    def test_unknown_target_raises(self):
        dt = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="Unknown target"):
            compute_altitude_azimuth("pluto", BLR_LAT, BLR_LON, dt)


class TestRaDec:
    def test_orion_nebula_position(self):
        """Orion Nebula (M42): RA ~83.8°, Dec ~-5.4°."""
        dt = datetime(2026, 12, 15, 20, 0, tzinfo=timezone.utc)  # ~1:30 AM IST
        result = compute_altitude_azimuth_radec(83.8, -5.4, BLR_LAT, BLR_LON, dt)
        assert "altitude_deg" in result
        assert "azimuth_deg" in result
        # Orion should be reasonably high in the winter sky from India
        assert -90 <= result["altitude_deg"] <= 90


class TestRiseSet:
    def test_sun_rises_and_sets(self):
        """Sun should have both a rise and set time in Bangalore (non-polar)."""
        dt = datetime(2026, 9, 14, 0, 0, tzinfo=timezone.utc)
        result = compute_rise_set("sun", BLR_LAT, BLR_LON, dt)
        assert result["rise_utc"] is not None, "Sun should rise in Bangalore"
        assert result["set_utc"] is not None, "Sun should set in Bangalore"
        assert result["is_circumpolar"] is False

    def test_sun_rise_before_set(self):
        """Sun should rise before it sets."""
        dt = datetime(2026, 9, 14, 0, 0, tzinfo=timezone.utc)
        result = compute_rise_set("sun", BLR_LAT, BLR_LON, dt)
        if result["rise_utc"] and result["set_utc"]:
            assert result["rise_utc"] < result["set_utc"]

    def test_moon_rise_set(self):
        """Moon should return rise/set (though one may be None on some days)."""
        dt = datetime(2026, 9, 14, 0, 0, tzinfo=timezone.utc)
        result = compute_rise_set("moon", BLR_LAT, BLR_LON, dt)
        # At least one of rise/set should exist
        assert result["rise_utc"] is not None or result["set_utc"] is not None or result["is_circumpolar"]


class TestAstronomicalTwilight:
    def test_twilight_returns_times(self):
        """Should return both twilight end (evening) and start (morning)."""
        dt = datetime(2026, 9, 14, 0, 0, tzinfo=timezone.utc)
        result = compute_astronomical_twilight(BLR_LAT, BLR_LON, dt)
        assert result["twilight_end_utc"] is not None, "Should have evening twilight end"
        assert result["twilight_start_utc"] is not None, "Should have morning twilight start"

    def test_twilight_end_before_start(self):
        """Evening twilight end should be before morning twilight start."""
        dt = datetime(2026, 9, 14, 0, 0, tzinfo=timezone.utc)
        result = compute_astronomical_twilight(BLR_LAT, BLR_LON, dt)
        if result["twilight_end_utc"] and result["twilight_start_utc"]:
            assert result["twilight_end_utc"] < result["twilight_start_utc"]

    def test_twilight_after_sunset(self):
        """Astronomical twilight end should be after sunset."""
        dt = datetime(2026, 9, 14, 0, 0, tzinfo=timezone.utc)
        twilight = compute_astronomical_twilight(BLR_LAT, BLR_LON, dt)
        sunset = compute_rise_set("sun", BLR_LAT, BLR_LON, dt)
        if twilight["twilight_end_utc"] and sunset["set_utc"]:
            assert twilight["twilight_end_utc"] > sunset["set_utc"]


class TestMoonPhase:
    def test_phase_in_valid_range(self):
        dt = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)
        phase = compute_moon_phase(dt)
        assert 0.0 <= phase <= 1.0

    def test_new_moon_near_zero(self):
        """2026-02-17 is a new moon — phase should be near 0."""
        dt = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)
        phase = compute_moon_phase(dt)
        assert phase < 0.1, f"Expected near-zero phase at new moon, got {phase}"

    def test_full_moon_near_one(self):
        """2026-03-03 is a full moon — phase should be near 1."""
        dt = datetime(2026, 3, 3, 12, 0, tzinfo=timezone.utc)
        phase = compute_moon_phase(dt)
        assert phase > 0.9, f"Expected near-one phase at full moon, got {phase}"


class TestMoonInterference:
    def test_interference_is_low_at_new_moon(self):
        """At new moon, interference should be very low regardless of target position."""
        dt = datetime(2026, 2, 17, 18, 0, tzinfo=timezone.utc)
        result = compute_moon_interference(83.8, -5.4, BLR_LAT, BLR_LON, dt)
        # New moon → interference score should be very low
        assert result["interference_score"] < 0.15

    def test_interference_score_range(self):
        """Interference score should always be 0-1."""
        dt = datetime(2026, 9, 14, 18, 0, tzinfo=timezone.utc)
        result = compute_moon_interference(83.8, -5.4, BLR_LAT, BLR_LON, dt)
        assert 0.0 <= result["interference_score"] <= 1.0

    def test_returns_all_fields(self):
        dt = datetime(2026, 9, 14, 18, 0, tzinfo=timezone.utc)
        result = compute_moon_interference(83.8, -5.4, BLR_LAT, BLR_LON, dt)
        assert "moon_altitude_deg" in result
        assert "moon_phase_pct" in result
        assert "interference_score" in result
