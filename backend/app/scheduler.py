"""
Scheduler Service for Stellinerary.

Sets up background tasks, primarily checking real-time weather updates 
and triggering the Contingency Agent.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.models import ExpeditionPlan
from app.agents.weather import get_weather_forecast
from app.agents.contingency import check_contingency
from app.services.plan_store import plan_store

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def check_all_contingencies():
    """
    Background job that loops through all active plans,
    fetches fresh weather for their sites, and runs the Contingency Agent.
    """
    active_plans = plan_store.active()
    if not active_plans:
        return
        
    logger.info("Executing background contingency check for %d active plans...", len(active_plans))
    
    for plan in active_plans:
        plan_id = plan.plan_id or "unknown"
        if not plan.chosen_site or not plan.request:
            continue
            
        # Fetch fresh weather
        try:
            new_weather = await get_weather_forecast(
                site_id=plan.chosen_site.id,
                lat=plan.chosen_site.lat,
                lon=plan.chosen_site.lon,
            )
        except Exception as e:
            logger.error("Failed to fetch weather for plan %s: %s", plan_id, e)
            continue
            
        changed, updated_plan = check_contingency(plan, new_weather)
        
        if changed:
            logger.warning("Plan %s was UPDATED due to weather contingency!", plan_id)
            updated_plan.plan_id = plan.plan_id
            plan_store.save(updated_plan)


def start_scheduler():
    """Initialize and start the background scheduler."""
    # Run every 60 minutes
    scheduler.add_job(check_all_contingencies, 'interval', minutes=60, id='contingency_check_job')
    scheduler.start()
    logger.info("Background scheduler started (Contingency checks every 60m).")


def stop_scheduler():
    """Stop the background scheduler."""
    scheduler.shutdown()
    logger.info("Background scheduler stopped.")
