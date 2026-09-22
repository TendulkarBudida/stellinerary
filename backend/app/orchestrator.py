"""
Orchestrator — the hand-rolled pipeline that calls agents in order.

This is plain, readable Python — not a framework's black-box graph executor.
Each step is a function call that enriches the shared ExpeditionPlan state.

Pipeline:
  1. Curator → ranked events
  2. Location Scout → ranked sites, pick the best
  3. Weather → forecast for the chosen site
  4. Choreographer → observation schedule
  5. Gear → packing list
  6. Story → narrative blurbs for each event

The interdependencies:
  - Location Scout uses Weather internally for ranking
  - Choreographer needs: site horizon + weather + events + ephemeris
  - Gear needs: site conditions + weather + events
  - Story needs: events list (from Curator)
"""

import logging
from datetime import datetime, timezone

from app.agents.choreographer import generate_schedule
from app.agents.curator import curate_events
from app.agents.gear import generate_gear_list
from app.agents.location_scout import rank_sites
from app.agents.story import generate_story_for_event
from app.agents.weather import get_weather_forecast
from app.models import ExpeditionPlan, PlanRequest

logger = logging.getLogger(__name__)


async def generate_plan(request: PlanRequest) -> ExpeditionPlan:
    """
    Run the full orchestration pipeline.

    Each step enriches the ExpeditionPlan state. If any step fails,
    the pipeline continues with degraded output rather than crashing.
    """
    plan = ExpeditionPlan(request=request)

    # ── Step 1: Curator — what's worth seeing? ────────────────────────
    logger.info("🌟 [1/6] Curator: finding events for %s to %s", request.date_start, request.date_end)

    plan.ranked_events = curate_events(
        date_start=request.date_start,
        date_end=request.date_end,
        lat=request.user_lat,
        lon=request.user_lon,
        bortle_class=5,  # default; will be refined after site selection
    )
    logger.info("   → %d events found", len(plan.ranked_events))

    # ── Step 2: Location Scout — where to go? ─────────────────────────
    logger.info("📍 [2/6] Location Scout: ranking sites near (%.2f, %.2f)", request.user_lat, request.user_lon)

    plan.ranked_sites = await rank_sites(
        user_lat=request.user_lat,
        user_lon=request.user_lon,
        max_results=5,
        fetch_weather=True,
    )
    logger.info("   → %d sites ranked", len(plan.ranked_sites))

    if plan.ranked_sites:
        plan.chosen_site = plan.ranked_sites[0].site
        logger.info("   → Chosen site: %s (Bortle %d, %.0f km away)",
                     plan.chosen_site.name, plan.chosen_site.bortle_class,
                     plan.ranked_sites[0].distance_km)

        # Re-run curator with the actual site's Bortle class
        if plan.chosen_site.bortle_class != 5:
            plan.ranked_events = curate_events(
                date_start=request.date_start,
                date_end=request.date_end,
                lat=plan.chosen_site.lat,
                lon=plan.chosen_site.lon,
                bortle_class=plan.chosen_site.bortle_class,
            )
            logger.info("   → Re-curated with Bortle %d: %d events",
                         plan.chosen_site.bortle_class, len(plan.ranked_events))

    # ── Step 3: Weather — what's the forecast at the chosen site? ─────
    if plan.chosen_site:
        logger.info("🌤️ [3/6] Weather: fetching forecast for %s", plan.chosen_site.name)
        plan.weather_forecast = await get_weather_forecast(
            plan.chosen_site.id,
            plan.chosen_site.lat,
            plan.chosen_site.lon,
        )
        logger.info("   → %d hourly data points, summary: %s",
                     len(plan.weather_forecast.hourly),
                     plan.weather_forecast.summary[:80])

    # ── Step 4: Choreographer — the observation schedule ──────────────
    if plan.chosen_site and plan.ranked_events:
        logger.info("⏱️ [4/6] Choreographer: building schedule")
        plan.schedule = generate_schedule(
            site=plan.chosen_site,
            events=plan.ranked_events,
            weather=plan.weather_forecast,
            observation_date=request.date_start,
        )
        logger.info("   → %d schedule entries", len(plan.schedule.entries))

    # ── Step 5: Gear — what to bring ──────────────────────────────────
    if plan.chosen_site:
        logger.info("🎒 [5/6] Gear: generating packing list")
        plan.gear = generate_gear_list(
            site=plan.chosen_site,
            events=plan.ranked_events,
            equipment_level=request.equipment_level,
            weather=plan.weather_forecast,
        )
        logger.info("   → %d items, %d warnings", len(plan.gear.items), len(plan.gear.warnings))

    # ── Step 6: Story — context and narrative ─────────────────────────
    if plan.ranked_events:
        logger.info("📖 [6/6] Story: generating narratives for top events")
        for event in plan.ranked_events[:5]:  # Top 5 events get stories
            try:
                story = await generate_story_for_event(event)
                plan.stories.append(story)
            except Exception as e:
                logger.warning("   → Story generation failed for %s: %s", event.name, e)
        logger.info("   → %d stories generated", len(plan.stories))

    plan.generated_at = datetime.now(timezone.utc)

    logger.info("✅ Plan generation complete!")
    return plan
