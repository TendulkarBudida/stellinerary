"""
Observation Choreographer Agent — THE core of the project.

Given: site horizon profile + weather windows + ranked events with ephemeris data,
compute a minute-by-minute observation schedule: what's viewable, when it clears
the site's horizon, when weather allows it, and in what order.

This is the piece with genuine multi-agent interdependency:
- Celestial Events Agent → what's worth seeing
- Ephemeris Service → when each object rises/sets and its altitude over time
- Site horizon profile → what altitude each object needs to clear terrain
- Weather forecast → which hours are actually clear
- All combined → an optimized, time-ordered observation plan
"""

import logging
from datetime import datetime, date, timedelta, timezone
from typing import Optional

from app.models import (
    CelestialEvent,
    HorizonBlock,
    HourlyWeather,
    ObservationSchedule,
    ScheduleEntry,
    Site,
    SiteWeatherForecast,
)
from app.services.ephemeris import (
    compute_altitude_azimuth,
    compute_altitude_azimuth_radec,
    compute_astronomical_twilight,
    compute_moon_phase,
    compute_rise_set,
)

logger = logging.getLogger(__name__)

# IST offset for display times
IST_OFFSET = timedelta(hours=5, minutes=30)


def generate_schedule(
    site: Site,
    events: list[CelestialEvent],
    weather: Optional[SiteWeatherForecast],
    observation_date: date,
) -> ObservationSchedule:
    """
    Generate the observation schedule for a night at the given site.

    The "observation night" spans from sunset on observation_date to
    sunrise on observation_date + 1.

    Args:
        site: The chosen observation site (with horizon profile).
        events: Ranked celestial events to observe.
        weather: Hourly weather forecast (may be None if API unavailable).
        observation_date: The date of the observation evening.

    Returns:
        ObservationSchedule with time-ordered entries.
    """
    entries: list[ScheduleEntry] = []

    # ── 1. Compute night boundaries ──────────────────────────────────
    obs_dt = datetime(observation_date.year, observation_date.month,
                      observation_date.day, tzinfo=timezone.utc)
    twilight = compute_astronomical_twilight(site.lat, site.lon, obs_dt)
    twilight_end = twilight.get("twilight_end_utc")    # evening — dark begins
    twilight_start = twilight.get("twilight_start_utc")  # morning — dawn begins

    sun_data = compute_rise_set("sun", site.lat, site.lon,
                                datetime(observation_date.year, observation_date.month,
                                         observation_date.day, tzinfo=timezone.utc))
    sunset_utc = sun_data.get("set_utc")

    # Moon info
    night_mid = datetime(observation_date.year, observation_date.month,
                         observation_date.day, 18, 30, tzinfo=timezone.utc)
    moon_phase = compute_moon_phase(night_mid)
    moon_data = compute_rise_set("moon", site.lat, site.lon,
                                 datetime(observation_date.year, observation_date.month,
                                          observation_date.day, tzinfo=timezone.utc))

    # ── 2. Build clear-sky mask from weather ─────────────────────────
    clear_hours = _get_clear_hours(weather)

    # ── 3. Dark adaptation entry (always first) ──────────────────────
    if twilight_end:
        adapt_time = twilight_end - timedelta(minutes=20)
        entries.append(ScheduleEntry(
            time_local=_utc_to_local_str(adapt_time),
            end_time_local=_utc_to_local_str(twilight_end),
            title="🌑 Dark Adaptation",
            description=(
                "Arrive and let your eyes dark-adapt for 20 minutes. "
                "Avoid ALL white light — phone screens, car headlights, flashlights. "
                "Use only red-filtered light from this point on."
            ),
            dark_adaptation_note="Your eyes need 20 minutes to fully adapt to darkness. One flash of white light resets the clock.",
        ))

    # ── 4. Schedule each event ───────────────────────────────────────
    for event in events[:8]:  # Cap at 8 events per night
        event_entries = _schedule_event(
            event, site, observation_date, twilight_end, twilight_start, clear_hours
        )
        entries.extend(event_entries)

    # ── 5. Sort by time ──────────────────────────────────────────────
    entries.sort(key=lambda e: e.time_local)

    return ObservationSchedule(
        entries=entries,
        astronomical_twilight_end=_utc_to_local_str(twilight_end) if twilight_end else None,
        astronomical_twilight_start=_utc_to_local_str(twilight_start) if twilight_start else None,
        moon_rise=_utc_to_local_str(moon_data["rise_utc"]) if moon_data.get("rise_utc") else None,
        moon_set=_utc_to_local_str(moon_data["set_utc"]) if moon_data.get("set_utc") else None,
        moon_phase_pct=round(moon_phase * 100, 1),
    )


def _schedule_event(
    event: CelestialEvent,
    site: Site,
    observation_date: date,
    twilight_end: Optional[datetime],
    twilight_start: Optional[datetime],
    clear_hours: set[int],
) -> list[ScheduleEntry]:
    """Generate schedule entries for a single event."""
    entries: list[ScheduleEntry] = []

    if event.type == "meteor_shower":
        entries.extend(_schedule_meteor_shower(event, site, observation_date,
                                                twilight_end, twilight_start, clear_hours))
    elif event.type in ("opposition", "elongation"):
        entries.extend(_schedule_planet(event, site, observation_date,
                                        twilight_end, twilight_start, clear_hours))
    elif event.type == "seasonal":
        entries.extend(_schedule_seasonal(event, site, observation_date,
                                          twilight_end, twilight_start, clear_hours))
    elif event.type == "eclipse":
        entries.append(ScheduleEntry(
            time_local=event.best_hours or "varies",
            title=f"🌒 {event.name}",
            description=event.description,
            event_id=event.id,
        ))
    else:
        # Generic fallback
        best_time = twilight_end or datetime(observation_date.year, observation_date.month,
                                              observation_date.day, 14, 0, tzinfo=timezone.utc)
        entries.append(ScheduleEntry(
            time_local=_utc_to_local_str(best_time),
            title=event.name,
            description=event.description,
            event_id=event.id,
        ))

    return entries


def _schedule_meteor_shower(
    event: CelestialEvent,
    site: Site,
    observation_date: date,
    twilight_end: Optional[datetime],
    twilight_start: Optional[datetime],
    clear_hours: set[int],
) -> list[ScheduleEntry]:
    """Schedule meteor shower viewing with radiant altitude awareness."""
    entries: list[ScheduleEntry] = []

    # Check radiant position throughout the night
    if event.radiant_ra_deg is None or event.radiant_dec_deg is None:
        # No radiant coords — just recommend peak hours
        start_utc = twilight_end or datetime(observation_date.year, observation_date.month,
                                              observation_date.day, 14, 0, tzinfo=timezone.utc)
        entries.append(ScheduleEntry(
            time_local=_utc_to_local_str(start_utc),
            title=f"☄️ {event.name}",
            description=f"{event.description} Best hours: {event.best_hours or 'after midnight'}.",
            direction=event.viewing_direction,
            event_id=event.id,
        ))
        return entries

    # Find when the radiant is highest and above horizon
    best_time = None
    best_alt = -90.0
    night_start = twilight_end or datetime(observation_date.year, observation_date.month,
                                            observation_date.day, 13, 0, tzinfo=timezone.utc)
    night_end = twilight_start or datetime(observation_date.year, observation_date.month,
                                            observation_date.day + 1, 0, 30, tzinfo=timezone.utc)

    # Sample every 30 minutes through the night
    t = night_start
    radiant_visible_start = None
    while t < night_end:
        pos = compute_altitude_azimuth_radec(
            event.radiant_ra_deg, event.radiant_dec_deg,
            site.lat, site.lon, t,
        )
        alt = pos["altitude_deg"]

        # Check if blocked by site horizon
        min_alt = _get_min_altitude_for_azimuth(site, pos["azimuth_deg"])

        if alt > min_alt and radiant_visible_start is None:
            radiant_visible_start = t

        if alt > best_alt and alt > min_alt:
            best_alt = alt
            best_time = t

        t += timedelta(minutes=30)

    if best_time is None:
        entries.append(ScheduleEntry(
            time_local=_utc_to_local_str(night_start),
            title=f"☄️ {event.name} (radiant may be low)",
            description=f"{event.description} Radiant stays low from this site tonight.",
            event_id=event.id,
        ))
        return entries

    # Meteor watching window: radiant above horizon to dawn
    watch_start = radiant_visible_start or best_time - timedelta(hours=1)
    is_weather_ok = _is_clear_at(watch_start, clear_hours)

    zhr_info = f"Up to {event.zhr} meteors/hour at peak. " if event.zhr else ""

    entries.append(ScheduleEntry(
        time_local=_utc_to_local_str(watch_start),
        end_time_local=_utc_to_local_str(night_end),
        title=f"☄️ {event.name}",
        description=(
            f"{zhr_info}Radiant in {event.radiant_constellation or 'the sky'} "
            f"reaches {best_alt:.0f}° altitude at {_utc_to_local_str(best_time)}. "
            f"Lie back and watch the entire sky — don't stare at just the radiant. "
            f"Each meteor: a particle at {event.speed_km_s or '?'} km/s, burning 80-120 km above you."
        ),
        direction=event.viewing_direction,
        altitude_deg=best_alt,
        event_id=event.id,
        is_weather_dependent=True,
        dark_adaptation_note="Do NOT check your phone during meteor watching — each glance costs 20 min of adaptation." if not is_weather_ok else None,
    ))

    return entries


def _schedule_planet(
    event: CelestialEvent,
    site: Site,
    observation_date: date,
    twilight_end: Optional[datetime],
    twilight_start: Optional[datetime],
    clear_hours: set[int],
) -> list[ScheduleEntry]:
    """Schedule planet/opposition viewing."""
    entries: list[ScheduleEntry] = []
    target = event.target_object

    if not target:
        return entries

    # Find when the planet is highest during the night
    night_start = twilight_end or datetime(observation_date.year, observation_date.month,
                                            observation_date.day, 13, 0, tzinfo=timezone.utc)
    night_end = twilight_start or datetime(observation_date.year, observation_date.month,
                                            observation_date.day + 1, 0, 30, tzinfo=timezone.utc)

    best_time = None
    best_alt = -90.0
    rise_time = None

    t = night_start
    while t < night_end:
        try:
            pos = compute_altitude_azimuth(target, site.lat, site.lon, t)
        except ValueError:
            break

        alt = pos["altitude_deg"]
        min_alt = _get_min_altitude_for_azimuth(site, pos["azimuth_deg"])

        if alt > min_alt and rise_time is None:
            rise_time = t

        if alt > best_alt and alt > min_alt:
            best_alt = alt
            best_time = t

        t += timedelta(minutes=30)

    if best_time is None or best_alt <= 0:
        return entries

    view_start = rise_time or best_time
    is_clear = _is_clear_at(view_start, clear_hours)

    entries.append(ScheduleEntry(
        time_local=_utc_to_local_str(view_start),
        end_time_local=_utc_to_local_str(min(best_time + timedelta(hours=2), night_end)),
        title=f"🪐 {event.name}",
        description=(
            f"{event.description} "
            f"{target.capitalize()} reaches {best_alt:.0f}° altitude at {_utc_to_local_str(best_time)}. "
            f"Best viewed when highest — atmospheric distortion is less."
        ),
        direction=event.viewing_direction,
        altitude_deg=best_alt,
        event_id=event.id,
        is_weather_dependent=True,
    ))

    return entries


def _schedule_seasonal(
    event: CelestialEvent,
    site: Site,
    observation_date: date,
    twilight_end: Optional[datetime],
    twilight_start: Optional[datetime],
    clear_hours: set[int],
) -> list[ScheduleEntry]:
    """Schedule seasonal events (e.g., Milky Way core)."""
    start = twilight_end or datetime(observation_date.year, observation_date.month,
                                     observation_date.day, 14, 0, tzinfo=timezone.utc)
    return [ScheduleEntry(
        time_local=_utc_to_local_str(start),
        title=f"🌌 {event.name}",
        description=f"{event.description} Look {event.viewing_direction or 'south'}.",
        direction=event.viewing_direction,
        event_id=event.id,
        is_weather_dependent=True,
    )]


# ── Horizon helpers ──────────────────────────────────────────────────

def _get_min_altitude_for_azimuth(site: Site, azimuth_deg: float) -> float:
    """
    Get the minimum altitude an object needs to clear the terrain at a given azimuth.

    Checks the site's blocked_directions and returns the blocking altitude
    if the azimuth falls within a blocked arc, otherwise returns 0.
    """
    for block in site.horizon_profile.blocked_directions:
        if _azimuth_in_arc(azimuth_deg, block.azimuth_start, block.azimuth_end):
            return float(block.max_blocked_altitude_deg)
    return 0.0


def _azimuth_in_arc(az: float, start: int, end: int) -> bool:
    """Check if an azimuth is within an arc (handles wrap-around at 360°)."""
    az = az % 360
    if start <= end:
        return start <= az <= end
    else:
        # Arc wraps around north (e.g., 340° to 30°)
        return az >= start or az <= end


# ── Weather helpers ──────────────────────────────────────────────────

def _get_clear_hours(weather: Optional[SiteWeatherForecast]) -> set[int]:
    """
    Extract the set of UTC hours that are forecast to be clear (cloud cover ≤ 40%).
    Returns an empty set if no weather data (treated as "assume clear").
    """
    if not weather or not weather.hourly:
        return set()  # No data — assume clear

    return {
        h.datetime_utc.hour
        for h in weather.hourly
        if h.cloud_cover_pct <= 40
    }


def _is_clear_at(dt: datetime, clear_hours: set[int]) -> bool:
    """Check if the forecast is clear at a given time."""
    if not clear_hours:
        return True  # No weather data — assume clear
    return dt.hour in clear_hours


# ── Time formatting ──────────────────────────────────────────────────

def _utc_to_local_str(dt: Optional[datetime]) -> str:
    """Convert a UTC datetime to IST time string (HH:MM)."""
    if dt is None:
        return "—"
    local = dt + IST_OFFSET
    return local.strftime("%H:%M")
