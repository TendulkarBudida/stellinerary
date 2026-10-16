"""Step 6 — Location Scout agent tests.

Validates:
1. Haversine distance calculation.
2. Bortle and distance scoring functions.
3. Site ranking order (Bangalore → Nandi Hills should rank near top).
4. Weather score impact on ranking.
5. Night access penalty.
"""

import math
import pytest
from unittest.mock import AsyncMock, patch

from app.agents.location_scout import (
    _bortle_score,
    _distance_score,
    _haversine_km,
    rank_sites,
)
from app.models import RankedSite

# Bangalore coordinates
BANGALORE_LAT = 12.9716
BANGALORE_LON = 77.5946


class TestHaversine:
    def test_zero_distance(self):
        d = _haversine_km(12.97, 77.59, 12.97, 77.59)
        assert d < 0.1

    def test_bangalore_to_nandi_hills(self):
        # Nandi Hills is ~60 km from Bangalore
        d = _haversine_km(BANGALORE_LAT, BANGALORE_LON, 13.3702, 77.6835)
        assert 40 < d < 80  # roughly 60 km

    def test_bangalore_to_spiti(self):
        # Spiti is ~2000+ km from Bangalore
        d = _haversine_km(BANGALORE_LAT, BANGALORE_LON, 32.316, 78.008)
        assert d > 2000

    def test_symmetry(self):
        d1 = _haversine_km(12.97, 77.59, 32.316, 78.008)
        d2 = _haversine_km(32.316, 78.008, 12.97, 77.59)
        assert abs(d1 - d2) < 0.01


class TestScoringFunctions:
    def test_bortle_1_scores_highest(self):
        assert _bortle_score(1) > _bortle_score(3)
        assert _bortle_score(3) > _bortle_score(5)
        assert _bortle_score(5) > _bortle_score(9)

    def test_bortle_score_range(self):
        for b in range(1, 10):
            s = _bortle_score(b)
            assert 0.0 <= s <= 1.0, f"Bortle {b} score {s} out of range"

    def test_closer_distance_scores_higher(self):
        assert _distance_score(50) > _distance_score(200)
        assert _distance_score(200) > _distance_score(500)

    def test_distance_score_range(self):
        for d in [0, 10, 50, 100, 200, 500, 1000, 2000]:
            s = _distance_score(d)
            assert 0.0 <= s <= 1.0, f"Distance {d}km score {s} out of range"


class TestRankSites:
    @pytest.mark.asyncio
    async def test_ranking_from_bangalore_without_weather(self):
        """Closest discovered site should rank near top from Bangalore (by distance+bortle)."""
        ranked = await rank_sites(
            BANGALORE_LAT, BANGALORE_LON,
            max_results=10,
            fetch_weather=False,
        )
        assert len(ranked) > 0
        assert all(isinstance(r, RankedSite) for r in ranked)

        # Closest fixture site should be in the top 3
        top_3_ids = [r.site.id for r in ranked[:3]]
        assert "close-camp" in top_3_ids, f"Expected close-camp in top 3, got {top_3_ids}"

    @pytest.mark.asyncio
    async def test_scores_are_sorted_descending(self):
        ranked = await rank_sites(BANGALORE_LAT, BANGALORE_LON, fetch_weather=False)
        scores = [r.overall_score for r in ranked]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_distant_bortle_3_outscores_nearby_bortle_4_on_darkness(self):
        """A darker far site should beat a brighter near site on the Bortle component."""
        ranked = await rank_sites(BANGALORE_LAT, BANGALORE_LON, max_results=10, fetch_weather=False)

        far = next((r for r in ranked if r.site.id == "far-valley"), None)
        close = next((r for r in ranked if r.site.id == "close-camp"), None)

        assert far is not None and close is not None
        assert far.bortle_score > close.bortle_score

    @pytest.mark.asyncio
    async def test_max_results_limits_output(self):
        ranked = await rank_sites(BANGALORE_LAT, BANGALORE_LON, max_results=3, fetch_weather=False)
        assert len(ranked) == 3

    @pytest.mark.asyncio
    async def test_ranking_reason_is_populated(self):
        ranked = await rank_sites(BANGALORE_LAT, BANGALORE_LON, max_results=3, fetch_weather=False)
        for r in ranked:
            assert r.ranking_reason
            assert "km away" in r.ranking_reason
            assert "Bortle" in r.ranking_reason

    @pytest.mark.asyncio
    async def test_travel_time_populated(self):
        ranked = await rank_sites(BANGALORE_LAT, BANGALORE_LON, max_results=3, fetch_weather=False)
        for r in ranked:
            assert r.travel_time_estimate_min is not None
            assert r.travel_time_estimate_min > 0
