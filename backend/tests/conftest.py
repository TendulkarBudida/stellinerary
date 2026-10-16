"""Shared fixtures: keep the suite hermetic (no live network).

Live site discovery is replaced with three deterministic fixture sites in
every module except those that opt in with ALLOW_LIVE_DISCOVERY = True
(currently only the discovery suite, which mocks HTTP itself).
"""

import pytest

from tests.fixtures import fixture_sites


@pytest.fixture(autouse=True)
def _offline_discovery(request, monkeypatch):
    if getattr(request.module, "ALLOW_LIVE_DISCOVERY", False):
        return
    sites = fixture_sites()

    def _stubbed(user_lat, user_lon, max_results, max_travel_minutes=None, max_distance_km=None):
        from app.agents.location_scout import _estimate_travel_time_min, _haversine_km

        kept = []
        for site in sites:
            distance = _haversine_km(user_lat, user_lon, site.lat, site.lon)
            if max_distance_km is not None and distance > max_distance_km:
                continue
            if max_travel_minutes is not None and _estimate_travel_time_min(distance) > max_travel_minutes:
                continue
            kept.append(site)
        return kept

    monkeypatch.setattr("app.agents.location_scout._discovered_sites", _stubbed)
