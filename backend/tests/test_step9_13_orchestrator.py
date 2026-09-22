"""Steps 8, 9, 13 — Orchestrator, Choreographer, and /plan endpoint tests.

Validates:
1. Choreographer generates schedule entries for known events.
2. Dark adaptation entry is always included.
3. Schedule entries are time-sorted.
4. Horizon blocking is respected.
5. Orchestrator pipeline returns a complete plan.
6. /plan endpoint returns 200 with expected structure.
"""

import pytest
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

from app.agents.choreographer import (
    generate_schedule,
    _get_min_altitude_for_azimuth,
    _azimuth_in_arc,
)
from app.data.loader import load_events, get_site_by_id
from app.models import PlanRequest, Site


# ── Choreographer tests ──────────────────────────────────────────────

class TestHorizonHelpers:
    def test_azimuth_in_arc_normal(self):
        assert _azimuth_in_arc(45, 30, 60) is True
        assert _azimuth_in_arc(20, 30, 60) is False
        assert _azimuth_in_arc(70, 30, 60) is False

    def test_azimuth_in_arc_wraparound(self):
        """Arc that wraps around north (e.g., 340° to 30°)."""
        assert _azimuth_in_arc(350, 340, 30) is True
        assert _azimuth_in_arc(10, 340, 30) is True
        assert _azimuth_in_arc(180, 340, 30) is False

    def test_min_altitude_clear_horizon(self):
        """Site with no blocked directions → 0° minimum altitude."""
        site = get_site_by_id("rann_of_kutch")  # Flat terrain, 360° horizon
        alt = _get_min_altitude_for_azimuth(site, 90)
        assert alt == 0.0

    def test_min_altitude_blocked_direction(self):
        """Site with blocked directions returns the blocked altitude."""
        site = get_site_by_id("nandi_hills")
        # Nandi Hills has blocked directions — check one
        if site.horizon_profile.blocked_directions:
            block = site.horizon_profile.blocked_directions[0]
            mid_az = (block.azimuth_start + block.azimuth_end) / 2
            alt = _get_min_altitude_for_azimuth(site, mid_az)
            assert alt > 0


class TestChoreographer:
    def test_schedule_includes_dark_adaptation(self):
        site = get_site_by_id("nandi_hills")
        events = [e for e in load_events() if e.type == "meteor_shower"][:2]
        schedule = generate_schedule(site, events, None, date(2026, 12, 14))
        
        titles = [e.title for e in schedule.entries]
        assert any("Dark Adaptation" in t for t in titles), \
            f"Dark adaptation entry missing. Got: {titles}"

    def test_schedule_entries_are_time_sorted(self):
        site = get_site_by_id("nandi_hills")
        events = [e for e in load_events() if e.type == "meteor_shower"][:2]
        schedule = generate_schedule(site, events, None, date(2026, 12, 14))
        
        times = [e.time_local for e in schedule.entries]
        assert times == sorted(times), f"Entries not time-sorted: {times}"

    def test_schedule_has_twilight_info(self):
        site = get_site_by_id("nandi_hills")
        events = [e for e in load_events() if e.type == "opposition"][:1]
        schedule = generate_schedule(site, events, None, date(2026, 10, 3))
        
        assert schedule.astronomical_twilight_end is not None
        assert schedule.astronomical_twilight_start is not None

    def test_schedule_has_moon_info(self):
        site = get_site_by_id("nandi_hills")
        events = [e for e in load_events() if e.type == "opposition"][:1]
        schedule = generate_schedule(site, events, None, date(2026, 10, 3))
        
        assert schedule.moon_phase_pct is not None
        assert 0 <= schedule.moon_phase_pct <= 100

    def test_meteor_shower_schedule_has_direction(self):
        site = get_site_by_id("coorg_madikeri")
        geminids = [e for e in load_events() if e.id == "geminids_2026"]
        if geminids:
            schedule = generate_schedule(site, geminids, None, date(2026, 12, 14))
            meteor_entries = [e for e in schedule.entries if "Geminid" in e.title]
            if meteor_entries:
                assert meteor_entries[0].event_id == "geminids_2026"


# ── /plan endpoint test ──────────────────────────────────────────────

class TestPlanEndpoint:
    @pytest.mark.asyncio
    async def test_plan_endpoint_returns_valid_structure(self):
        """The /plan endpoint should return a complete plan structure."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)

        # Mock the weather and story agents to avoid external API calls
        with patch("app.agents.weather.fetch_astro_weather", new_callable=AsyncMock, return_value=None):
            with patch("app.agents.story.chat_completion", new_callable=AsyncMock, side_effect=Exception("no LLM")):
                response = client.post("/plan", json={
                    "user_lat": 12.9716,
                    "user_lon": 77.5946,
                    "user_city": "Bangalore",
                    "date_start": "2026-12-12",
                    "date_end": "2026-12-15",
                    "equipment_level": "naked_eye",
                })

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Core structure checks
        assert "request" in data
        assert "ranked_events" in data
        assert "ranked_sites" in data
        assert "chosen_site" in data
        assert "schedule" in data
        assert "gear" in data
        assert "stories" in data
        assert "generated_at" in data

        # Should have events (Geminids active in Dec)
        assert len(data["ranked_events"]) > 0

        # Should have ranked sites
        assert len(data["ranked_sites"]) > 0

        # Should have chosen a site
        assert data["chosen_site"] is not None
        assert "name" in data["chosen_site"]

        # Schedule should have entries
        if data["schedule"]:
            assert len(data["schedule"]["entries"]) > 0
