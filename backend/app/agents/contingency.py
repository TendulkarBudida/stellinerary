"""
Contingency Agent — handles real-time weather changes.

Compares updated weather forecasts against the existing generated schedule.
If cloud cover crosses a problematic threshold during any actively scheduled window,
it flags the plan for rescheduling, or re-runs the Choreographer.
"""

import logging
from typing import Tuple

from app.models import ExpeditionPlan, SiteWeatherForecast
from app.agents.choreographer import generate_schedule

logger = logging.getLogger(__name__)

CLOUD_THRESHOLD = 50.0  # Percent. If > 50% during a scheduled window, we trigger a re-plan.


def check_contingency(plan: ExpeditionPlan, new_weather: SiteWeatherForecast) -> Tuple[bool, ExpeditionPlan]:
    """
    Check if the new weather invalidates the current schedule.

    Args:
        plan: The current full expedition plan.
        new_weather: The freshly fetched weather forecast.

    Returns:
        (changed_bool, new_plan)
        If changed is True, the schedule inside new_plan has been re-generated,
        and a contingency_note has been added.
    """
    if plan.schedule is None or plan.chosen_site is None:
        return False, plan  # Nothing to check against

    # We need to see if any schedule entry that is weather dependent falls in a cloudy window.
    # Convert hourly weather to a dictionary mapping hour to cloud cover
    cloud_cover_by_hour = {
        h.datetime_utc.hour: h.cloud_cover_pct
        for h in new_weather.hourly
    }

    needs_replanning = False
    
    # Very crude check: find affected hours from the schedule.
    # Since entries have local time formats like "21:30" and weather is UTC hours, 
    # we do a simple check.
    # Actual implementation might need precise datetime overlap, but for the MVP
    # we look at the hours the schedule spans.
    
    # We will build a set of hours that the schedule currently relies on being clear.
    dependent_hours = set()
    for entry in plan.schedule.entries:
        if entry.is_weather_dependent:
            # parsing time_local e.g. "21:30". This is IST.
            # IST to UTC is -5:30.
            try:
                # Naive parse just for hour mapping
                hh, mm = map(int, entry.time_local.split(":"))
                
                # convert IST hour to UTC hour roughly
                utc_hour = (hh - 5) % 24
                # if IST minutes < 30, it crosses another hour back in UTC
                if mm < 30:
                    utc_hour = (utc_hour - 1) % 24
                    
                dependent_hours.add(utc_hour)
            except ValueError:
                continue

    for hr in dependent_hours:
        if cloud_cover_by_hour.get(hr, 0) > CLOUD_THRESHOLD:
            logger.warning("Contingency alert: Cloud cover > %s%% at %s:00 UTC", CLOUD_THRESHOLD, hr)
            needs_replanning = True
            break

    if not needs_replanning:
        return False, plan

    # RE-PLANNING: Run the choreographer again with the new weather
    logger.info("Re-running Choreographer for contingency plan...")
    new_schedule = generate_schedule(
        site=plan.chosen_site,
        events=plan.ranked_events,
        weather=new_weather,
        observation_date=plan.request.date_start,  # Assuming single-night for MVP
    )

    plan.schedule = new_schedule
    plan.weather_forecast = new_weather
    plan.contingency_note = "NOTICE: Schedule has been updated due to worsening weather conditions."

    return True, plan
