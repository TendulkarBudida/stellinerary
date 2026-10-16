"""Tests for dynamic site discovery (all HTTP mocked — no network)."""

import math

import pytest

from app.services import site_discovery

ALLOW_LIVE_DISCOVERY = True


class _FakeResponse:
    def __init__(self, payload=None, status=200):
        self._payload = payload or {}
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise Exception(f"HTTP {self.status}")

    def json(self):
        return self._payload


class _FakeClient:
    """Stand-in for httpx.Client serving canned GET/POST responses."""

    get_payload: dict = {}
    post_payload: dict = {}
    fail: bool = False

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, params=None, headers=None):
        if self.fail:
            raise Exception("network down")
        return _FakeResponse(self.get_payload)

    def post(self, url, content=None, headers=None):
        if self.fail:
            raise Exception("network down")
        return _FakeResponse(self.post_payload)


@pytest.fixture(autouse=True)
def _patched_client(monkeypatch):
    monkeypatch.setattr(site_discovery.httpx, "Client", _FakeClient)
    site_discovery.clear_cache()
    _FakeClient.fail = False
    yield
    site_discovery.clear_cache()


def test_discover_places_parses_and_caps():
    _FakeClient.post_payload = {"elements": [
        {"lat": 12.9, "lon": 77.3, "tags": {"name": "Camp A", "tourism": "camp_site"}},
        {"lat": 12.8, "lon": 77.4, "tags": {"tourism": "viewpoint"}},
        {"lat": None, "lon": 77.4, "tags": {"name": "No coords"}},
    ]}
    places = site_discovery.discover_places(12.97, 77.59, limit=1)
    assert len(places) == 1
    assert places[0]["name"] == "Camp A"
    assert places[0]["kind"] == "camp_site"


def test_discover_places_empty_when_endpoints_fail(monkeypatch):
    _FakeClient.fail = True
    monkeypatch.setattr(site_discovery, "RETRY_DELAY_SECONDS", 0)
    assert site_discovery.discover_places(12.97, 77.59) == []


def test_estimate_bortle_city_distance_tiers():
    far_city = [{"lat": 1.0, "lon": 77.59, "tier": "city"}]  # ~111 km
    assert site_discovery.estimate_bortle(0.0, 77.59, far_city) == 3
    near_city = [{"lat": 0.2, "lon": 77.59, "tier": "city"}]  # ~22 km
    assert site_discovery.estimate_bortle(0.0, 77.59, near_city) == 7
    near_town = [{"lat": 0.05, "lon": 77.59, "tier": "town"}]  # ~5.5 km
    assert site_discovery.estimate_bortle(0.0, 77.59, near_town) == 7


def test_estimate_bortle_unknown_and_empty(monkeypatch):
    # Provider failure (None) is neutral; a clean query ([]) is dark.
    assert site_discovery.estimate_bortle(0.0, 0.0, []) == 3
    monkeypatch.setattr(site_discovery, "nearby_populated_places", lambda *a, **k: None)
    assert site_discovery.estimate_bortle(0.0, 0.0) == 5


def test_build_horizon_profile_detects_eastern_ridge(monkeypatch):
    def fake_elevations(points):
        out = {}
        for lat, lon in points:
            # Ridge due east of the site: higher ground near lon +0.02.
            out[(lat, lon)] = 1000.0 if lon > 0.02 else 100.0
        return out

    monkeypatch.setattr(site_discovery, "fetch_elevations", fake_elevations)
    profile = site_discovery.build_horizon_profile(0.0, 0.0, site_elevation_m=100.0)
    assert profile.blocked_directions
    east = [b for b in profile.blocked_directions if b.azimuth_start <= 90 <= b.azimuth_end or (b.azimuth_start > b.azimuth_end)]
    assert east
    assert all(b.max_blocked_altitude_deg >= 5 for b in profile.blocked_directions)


def test_build_horizon_profile_open_when_flat(monkeypatch):
    monkeypatch.setattr(site_discovery, "fetch_elevations", lambda points: {p: 100.0 for p in points})
    profile = site_discovery.build_horizon_profile(0.0, 0.0, site_elevation_m=100.0)
    assert profile.blocked_directions == []


def test_place_to_site_marked_unverified(monkeypatch):
    monkeypatch.setattr(site_discovery, "fetch_elevations", lambda points: {p: 500.0 for p in points})
    monkeypatch.setattr(site_discovery, "estimate_bortle", lambda lat, lon, places=None: 4)
    monkeypatch.setattr(
        site_discovery, "build_horizon_profile",
        lambda lat, lon, alt=None: site_discovery.HorizonProfile(description="test"),
    )
    site = site_discovery.place_to_site({"name": "Test Camp", "lat": 12.9, "lon": 77.5, "kind": "camp_site"})
    assert site.source == "discovered"
    assert site.bortle_class == 4
    assert "nverified" in site.access.night_access_notes
    assert "nverified" in site.notes or "stimated" in site.notes


@pytest.mark.asyncio
async def test_rank_sites_includes_discovered(monkeypatch):
    from app.agents import location_scout
    from app.models import Site

    discovered = Site(
        id="discovered-1", name="Test Camp", state="", lat=12.95, lon=77.55,
        altitude_m=800, bortle_class=3,
        horizon_profile=site_discovery.HorizonProfile(description="open"),
        access=site_discovery.SiteAccess(road_quality="unknown", night_access=True),
        amenities=site_discovery.SiteAmenities(),
        source="discovered",
    )
    monkeypatch.setattr(
        "app.agents.location_scout._discovered_sites",
        lambda *a, **k: [discovered],
    )
    ranked = await location_scout.rank_sites(12.9716, 77.5946, max_results=6, fetch_weather=False, discover=True)
    assert any(r.site.source == "discovered" for r in ranked)
    assert any("confirm night access" in r.ranking_reason.lower() for r in ranked if r.site.source == "discovered")


@pytest.mark.asyncio
async def test_rank_sites_empty_when_disabled_or_failing(monkeypatch):
    from app.agents import location_scout

    ranked_off = await location_scout.rank_sites(12.9716, 77.5946, max_results=6, fetch_weather=False, discover=False)
    assert ranked_off == []

    def _boom(*a, **k):
        raise Exception("overpass down")

    monkeypatch.setattr(location_scout.site_discovery, "discover_places", _boom)
    ranked_fail = await location_scout.rank_sites(12.9716, 77.5946, max_results=6, fetch_weather=False, discover=True)
    assert ranked_fail == []
