"""Phase 3 regression tests for primary and fallback plan options."""

import pytest
from unittest.mock import AsyncMock, patch

from app.models import PlanRequest
from app.orchestrator import generate_plan


@pytest.mark.asyncio
async def test_plan_contains_primary_and_fallback_options():
    request = PlanRequest(
        user_lat=12.9716,
        user_lon=77.5946,
        date_start="2026-12-12",
        date_end="2026-12-14",
        max_travel_minutes=300,
    )
    with patch("app.agents.weather.fetch_astro_weather", new_callable=AsyncMock, return_value=None):
        with patch("app.agents.story.chat_completion", new_callable=AsyncMock, side_effect=Exception("offline")):
            plan = await generate_plan(request)

    assert plan.options
    assert plan.options[0].label == "primary"
    assert plan.options[0].site == plan.chosen_site
    assert plan.options[0].gear == plan.gear
    assert plan.options[0].night_plan.schedule is not None
    assert all(option.reasons for option in plan.options)
    assert all(option.gear.items for option in plan.options)


@pytest.mark.asyncio
async def test_options_are_not_duplicated_when_no_distinct_local_site_exists():
    request = PlanRequest(
        user_lat=12.9716,
        user_lon=77.5946,
        date_start="2026-12-12",
        date_end="2026-12-12",
        max_travel_minutes=120,
    )
    with patch("app.agents.weather.fetch_astro_weather", new_callable=AsyncMock, return_value=None):
        plan = await generate_plan(request)

    site_ids = [option.site.id for option in plan.options]
    assert len(site_ids) == len(set(site_ids))
