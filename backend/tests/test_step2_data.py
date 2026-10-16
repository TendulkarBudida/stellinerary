"""Step 2 — Events calendar and live site discovery tests.

Validates that:
1. events_calendar.json loads, validates, and has correct data types.
2. The debug endpoints return data correctly (sites come from live discovery).
"""

import pytest
from fastapi.testclient import TestClient

from app.data.loader import load_events
from app.main import app
from app.models import CelestialEvent

client = TestClient(app)


class TestEventsCalendar:
    def test_events_load_successfully(self):
        events = load_events()
        assert len(events) >= 10, f"Expected at least 10 events, got {len(events)}"

    def test_every_event_is_valid_model(self):
        events = load_events()
        for event in events:
            assert isinstance(event, CelestialEvent), f"Event {event.id} is not a valid CelestialEvent model"

    def test_each_event_has_unique_id(self):
        events = load_events()
        ids = [e.id for e in events]
        assert len(ids) == len(set(ids)), f"Duplicate event IDs: {[x for x in ids if ids.count(x) > 1]}"

    def test_peak_date_within_active_range(self):
        events = load_events()
        for event in events:
            assert event.active_start <= event.peak_date <= event.active_end, (
                f"Event '{event.id}': peak_date {event.peak_date} is outside active range "
                f"[{event.active_start}, {event.active_end}]"
            )

    def test_meteor_showers_have_zhr(self):
        events = load_events()
        meteors = [e for e in events if e.type == "meteor_shower"]
        assert len(meteors) >= 5, "Expected at least 5 meteor showers"
        for m in meteors:
            assert m.zhr is not None and m.zhr > 0, f"Meteor shower '{m.id}' missing ZHR"

    def test_min_bortle_in_valid_range(self):
        events = load_events()
        for event in events:
            assert 1 <= event.min_bortle <= 9, f"Event '{event.id}' has invalid min_bortle: {event.min_bortle}"


class TestDebugEndpoints:
    def test_debug_sites_endpoint(self, monkeypatch):
        from tests.fixtures import fixture_places
        monkeypatch.setattr(
            "app.services.site_discovery.discover_places",
            lambda *args, **kwargs: fixture_places(),
        )
        response = client.get("/debug/sites")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert data["count"] == len(fixture_places())
        assert "places" in data
        assert len(data["places"]) == data["count"]

    def test_debug_events_endpoint(self):
        response = client.get("/debug/events")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert data["count"] >= 10
        assert "events" in data
        assert len(data["events"]) == data["count"]
