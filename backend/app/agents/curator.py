"""
Celestial Events Curator Agent.

Given a date range and observer location, filters the events calendar to what's
actually visible and worth seeing, then ranks them by impressiveness and
accessibility.

Key behaviors:
- Loads events from the static calendar
- Filters out events outside the date range
- Uses the Ephemeris service to check:
  - Is the object/radiant above the horizon during the night?
  - Is the Moon interfering (phase + angular proximity)?
  - Is the site dark enough (Bortle class vs. min_bortle)?
- Ranks events by a composite score: ZHR, moon interference (inverted),
  equipment accessibility, and event rarity.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from app.data.loader import load_events
from app.models import CelestialEvent
from app.services.ephemeris import (
    compute_altitude_azimuth,
    compute_altitude_azimuth_radec,
    compute_moon_interference,
    compute_moon_phase,
)

logger = logging.getLogger(__name__)


def curate_events(
    date_start: date,
    date_end: date,
    lat: float,
    lon: float,
    bortle_class: int = 5,
) -> list[CelestialEvent]:
    """
    Filter and rank celestial events for a date range and location.

    Args:
        date_start, date_end: Date window to search.
        lat, lon: Observer coordinates.
        bortle_class: Bortle class of the observation site (lower = darker).

    Returns:
        List of CelestialEvent objects, ranked by impressiveness (best first).
    """
    all_events = load_events()

    # Phase 1: Filter to events active in the date range
    active_events = [
        e for e in all_events
        if _overlaps(e.active_start, e.active_end, date_start, date_end)
    ]

    if not active_events:
        logger.info("No events active in date range %s to %s", date_start, date_end)
        return []

    # Phase 2: Filter by site darkness (Bortle class)
    visible_events = [
        e for e in active_events
        if bortle_class <= e.min_bortle
    ]

    logger.info(
        "Curator: %d events in date range, %d visible from Bortle %d site",
        len(active_events), len(visible_events), bortle_class,
    )

    # Phase 3: Score and rank
    scored: list[tuple[float, CelestialEvent]] = []
    for event in visible_events:
        score = _compute_event_score(event, date_start, date_end, lat, lon)
        scored.append((score, event))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    return [event for _, event in scored]


def _overlaps(
    event_start: date,
    event_end: date,
    range_start: date,
    range_end: date,
) -> bool:
    """Check if the event's active window overlaps with the date range."""
    return event_start <= range_end and event_end >= range_start


def _compute_event_score(
    event: CelestialEvent,
    date_start: date,
    date_end: date,
    lat: float,
    lon: float,
) -> float:
    """
    Compute a composite score for an event.

    Components:
    - Impressiveness: ZHR for meteors, type bonus for rare events
    - Moon interference penalty: bright moon near the target = bad
    - Peak proximity: events closer to peak date score higher
    - Equipment accessibility: naked-eye events score higher
    """
    score = 0.0

    # 1. Base impressiveness by type
    if event.type == "meteor_shower":
        # ZHR-based score, normalized (150 ZHR Geminids = 1.0)
        zhr = event.zhr or 10
        score += min(1.0, zhr / 150) * 40
    elif event.type == "opposition":
        score += 30  # Oppositions are always impressive
    elif event.type == "eclipse":
        score += 45  # Eclipses are rare and spectacular
    elif event.type == "elongation":
        score += 20  # Notable but less dramatic
    elif event.type == "seasonal":
        score += 25  # Milky Way is always good

    # 2. Moon interference penalty
    # Check moon interference at the event's peak date, midnight local
    peak = event.peak_date
    if date_start <= peak <= date_end:
        check_date = peak
    else:
        # Use the midpoint of the overlap
        overlap_start = max(event.active_start, date_start)
        overlap_end = min(event.active_end, date_end)
        mid = overlap_start + (overlap_end - overlap_start) / 2
        check_date = mid

    check_dt = datetime(check_date.year, check_date.month, check_date.day,
                        18, 30, tzinfo=timezone.utc)  # roughly midnight IST

    moon_phase = compute_moon_phase(check_dt)

    # If we have RA/Dec for the target, compute angular separation
    if event.radiant_ra_deg is not None and event.radiant_dec_deg is not None:
        interference = compute_moon_interference(
            event.radiant_ra_deg, event.radiant_dec_deg,
            lat, lon, check_dt,
        )
        moon_penalty = interference["interference_score"] * 20
    else:
        # No specific position — use phase alone as a rough penalty
        moon_penalty = moon_phase * 15

    score -= moon_penalty

    # 3. Peak proximity bonus
    if date_start <= peak <= date_end:
        score += 10  # Peak falls within requested range — great timing

    # 4. Equipment accessibility bonus
    if event.equipment.value == "naked_eye":
        score += 5  # Most accessible
    elif event.equipment.value == "binoculars":
        score += 3
    # telescope/solar_filter = 0 bonus

    return max(0.0, score)
