"""Step 2 — Site dataset and events calendar tests.

Validates that:
1. sites.json loads, validates, and has the expected count and required fields.
2. events_calendar.json loads, validates, and has correct data types.
3. Debug endpoints return the data correctly.
"""

import pytest
from fastapi.testclient import TestClient

from app.data.loader import load_events, load_sites
from app.main import app
from app.models import CelestialEvent, Site

client = TestClient(app)

REQUIRED_SITE_FIELDS = {"id", "name", "state", "lat", "lon", "altitude_m", "bortle_class", "horizon_profile", "access", "amenities"}


class TestSitesDataset:
    def test_sites_load_successfully(self):
        sites = load_sites()
        assert len(sites) >= 8, f"Expected at least 8 sites, got {len(sites)}"

    def test_every_site_is_valid_model(self):
        sites = load_sites()
        for site in sites:
            assert isinstance(site, Site), f"Site {site.id} is not a valid Site model"

    def test_every_site_has_required_fields(self):
        sites = load_sites()
        for site in sites:
            dumped = site.model_dump()
            missing = REQUIRED_SITE_FIELDS - set(dumped.keys())
            assert not missing, f"Site '{site.id}' missing fields: {missing}"

    def test_bortle_class_in_valid_range(self):
        sites = load_sites()
        for site in sites:
            assert 1 <= site.bortle_class <= 9, f"Site '{site.id}' has invalid Bortle class: {site.bortle_class}"

    def test_coordinates_are_in_india(self):
        """Rough bounding box for India: lat 6-37, lon 68-98."""
        sites = load_sites()
        for site in sites:
            assert 6 <= site.lat <= 37, f"Site '{site.id}' latitude {site.lat} outside India bounds"
            assert 68 <= site.lon <= 98, f"Site '{site.id}' longitude {site.lon} outside India bounds"

    def test_each_site_has_unique_id(self):
        sites = load_sites()
        ids = [s.id for s in sites]
        assert len(ids) == len(set(ids)), f"Duplicate site IDs found: {[x for x in ids if ids.count(x) > 1]}"

    def test_each_site_has_city_distances(self):
        sites = load_sites()
        for site in sites:
            assert len(site.city_distances_km) > 0, f"Site '{site.id}' has no city distance anchors"


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
    def test_debug_sites_endpoint(self):
        response = client.get("/debug/sites")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert data["count"] >= 8
        assert "sites" in data
        assert len(data["sites"]) == data["count"]

    def test_debug_events_endpoint(self):
        response = client.get("/debug/events")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert data["count"] >= 10
        assert "events" in data
        assert len(data["events"]) == data["count"]
