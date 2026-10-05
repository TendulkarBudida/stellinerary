"""
Scheduler Service for Stellinerary.

Sets up background tasks, primarily checking real-time weather updates 
and triggering the Contingency Agent.
"""

import logging
from typing import Dict
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.models import ExpeditionPlan
from app.agents.weather import fetch_astro_weather
from app.agents.contingency import check_contingency

logger = logging.getLogger(__name__)

# In-memory store for active plans.
# In a real app, this would be a database (e.g., Postgres or Redis).
ACTIVE_PLANS: Dict[str, ExpeditionPlan] = {}

scheduler = AsyncIOScheduler()


async def check_all_contingencies():
    """
    Background job that loops through all active plans,
    fetches fresh weather for their sites, and runs the Contingency Agent.
    """
    if not ACTIVE_PLANS:
        return
        
    logger.info("Executing background contingency check for %d active plans...", len(ACTIVE_PLANS))
    
    for plan_id, plan in list(ACTIVE_PLANS.items()):
        if not plan.chosen_site or not plan.request:
            continue
            
        # Fetch fresh weather
        try:
            new_weather = await fetch_astro_weather(
                lat=plan.chosen_site.lat,
                lon=plan.chosen_site.lon, 
                date_start=plan.request.date_start,
                date_end=plan.request.date_end
            )
        except Exception as e:
            logger.error("Failed to fetch weather for plan %s: %s", plan_id, e)
            continue
            
        if not new_weather:
            continue
            
        changed, updated_plan = check_contingency(plan, new_weather)
        
        if changed:
            logger.warning("Plan %s was UPDATED due to weather contingency!", plan_id)
            # Store updated plan
            ACTIVE_PLANS[plan_id] = updated_plan
            
            # In a real app we'd dispatch a push notification or email to the user here.


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
