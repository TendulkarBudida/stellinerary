"""
Ephemeris Service — Skyfield wrapper.

Provides astronomical calculations:
  - Rise/set times for Sun, Moon, and planets
  - Altitude/azimuth of objects at a given time
  - Astronomical twilight (Sun 18° below horizon — true darkness)  [A1]
  - Moon phase (% illumination) and interference scoring           [A2]
  - Typed high-level helpers used by Choreographer and Curator

All times are UTC. The caller is responsible for timezone conversion.
"""

import logging
import math
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

from skyfield import almanac
from skyfield.api import Loader, Star, wgs84

logger = logging.getLogger(__name__)

# ── Skyfield data loading ────────────────────────────────────────────────────
# Downloads de421.bsp (~17 MB) once to app/data/sky/, then caches.

_SKY_DATA_DIR = Path(__file__).parent.parent / "data" / "sky"
_SKY_DATA_DIR.mkdir(parents=True, exist_ok=True)

_loader = Loader(str(_SKY_DATA_DIR), verbose=False)


@lru_cache(maxsize=1)
def _get_ephemeris():
    """Load the planetary ephemeris (de421.bsp — covers 1900–2050)."""
    return _loader("de421.bsp")


@lru_cache(maxsize=1)
def _get_timescale():
    return _loader.timescale()


# ── Planet name → Skyfield target mapping ────────────────────────────────────

PLANET_MAP = {
    "mercury": "mercury",
    "venus": "venus",
    "mars": "mars",
    "jupiter": "jupiter barycenter",
    "saturn": "saturn barycenter",
    "uranus": "uranus barycenter",
    "neptune": "neptune barycenter",
    "moon": "moon",
    "sun": "sun",
}


def _get_target(name: str):
    eph = _get_ephemeris()
    key = name.strip().lower()
    if key in PLANET_MAP:
        return eph[PLANET_MAP[key]]
    raise ValueError(f"Unknown target: {name}. Use RA/Dec for deep sky objects.")


# ── Person B API: dict-returning functions used by curator/agents ─────────────

def compute_altitude_azimuth(target_name: str, lat: float, lon: float, dt_utc: datetime) -> dict:
    """
    Compute altitude and azimuth of a solar system object.

    Returns:
        {"altitude_deg": float, "azimuth_deg": float, "is_above_horizon": bool}
    """
    ts = _get_timescale()
    eph = _get_ephemeris()
    t = ts.from_datetime(dt_utc.replace(tzinfo=timezone.utc) if dt_utc.tzinfo is None else dt_utc)

    observer = eph["earth"] + wgs84.latlon(lat, lon)
    target = _get_target(target_name)

    alt, az, _ = observer.at(t).observe(target).apparent().altaz()
    return {
        "altitude_deg": round(float(alt.degrees), 2),
        "azimuth_deg": round(float(az.degrees), 2),
        "is_above_horizon": bool(alt.degrees > 0),
    }


def compute_altitude_azimuth_radec(ra_deg: float, dec_deg: float, lat: float, lon: float, dt_utc: datetime) -> dict:
    """
    Compute altitude and azimuth of a fixed RA/Dec position (deep sky / radiants).
    RA is in degrees (not hours).

    Returns:
        {"altitude_deg": float, "azimuth_deg": float, "is_above_horizon": bool}
    """
    ts = _get_timescale()
    eph = _get_ephemeris()
    t = ts.from_datetime(dt_utc.replace(tzinfo=timezone.utc) if dt_utc.tzinfo is None else dt_utc)

    observer = eph["earth"] + wgs84.latlon(lat, lon)
    target = Star(ra_hours=ra_deg / 15.0, dec_degrees=dec_deg)

    alt, az, _ = observer.at(t).observe(target).apparent().altaz()
    return {
        "altitude_deg": round(float(alt.degrees), 2),
        "azimuth_deg": round(float(az.degrees), 2),
        "is_above_horizon": bool(alt.degrees > 0),
    }


def compute_rise_set(target_name: str, lat: float, lon: float, date_utc: datetime) -> dict:
    """
    Compute rise and set times for a solar system object on a given date.

    Returns:
        {"rise_utc": datetime|None, "set_utc": datetime|None, "is_circumpolar": bool}
    """
    ts = _get_timescale()
    eph = _get_ephemeris()

    d = date_utc.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    t0 = ts.from_datetime(d)
    t1 = ts.from_datetime(d + timedelta(hours=36))

    observer = wgs84.latlon(lat, lon)
    target = _get_target(target_name)

    f = almanac.risings_and_settings(eph, target, observer)
    times, events = almanac.find_discrete(t0, t1, f)

    rise_utc = None
    set_utc = None
    for t, event in zip(times, events):
        dt = t.utc_datetime()
        if event and rise_utc is None:
            rise_utc = dt
        elif not event and set_utc is None:
            set_utc = dt

    return {
        "rise_utc": rise_utc,
        "set_utc": set_utc,
        "is_circumpolar": rise_utc is None and set_utc is None,
    }


def compute_astronomical_twilight(lat: float, lon: float, date_utc: datetime) -> dict:
    """
    Compute when astronomical twilight ends (evening) and begins (morning).

    Returns:
        {"twilight_end_utc": datetime|None, "twilight_start_utc": datetime|None}
    """
    ts = _get_timescale()
    eph = _get_ephemeris()

    d = date_utc.replace(hour=12, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    t0 = ts.from_datetime(d)
    t1 = ts.from_datetime(d + timedelta(hours=24))

    observer = wgs84.latlon(lat, lon)
    f = almanac.dark_twilight_day(eph, observer)
    times, events = almanac.find_discrete(t0, t1, f)

    twilight_end = None
    twilight_start = None
    prev_event = None
    for t, event in zip(times, events):
        dt = t.utc_datetime()
        if prev_event is not None:
            if prev_event >= 1 and event == 0 and twilight_end is None:
                twilight_end = dt
            if prev_event == 0 and event >= 1 and twilight_start is None:
                twilight_start = dt
        prev_event = event

    return {"twilight_end_utc": twilight_end, "twilight_start_utc": twilight_start}


def compute_moon_phase(dt_utc: datetime) -> float:
    """Moon illumination fraction 0.0 (new) – 1.0 (full)."""
    ts = _get_timescale()
    eph = _get_ephemeris()
    t = ts.from_datetime(dt_utc.replace(tzinfo=timezone.utc) if dt_utc.tzinfo is None else dt_utc)

    from skyfield.framelib import ecliptic_frame
    e = eph["earth"].at(t)
    _, sun_lon, _ = e.observe(eph["sun"]).apparent().frame_latlon(ecliptic_frame)
    _, moon_lon, _ = e.observe(eph["moon"]).apparent().frame_latlon(ecliptic_frame)

    phase_angle = (moon_lon.degrees - sun_lon.degrees) % 360
    return round(float((1 - math.cos(math.radians(phase_angle))) / 2), 3)


def compute_moon_interference(target_ra_deg: float, target_dec_deg: float, lat: float, lon: float, dt_utc: datetime) -> dict:
    """
    Compute Moon interference for a target position.

    Returns:
        {"moon_altitude_deg", "moon_phase_pct", "angular_separation_deg", "interference_score"}
    """
    moon_pos = compute_altitude_azimuth("moon", lat, lon, dt_utc)
    moon_alt = moon_pos["altitude_deg"]
    phase_frac = compute_moon_phase(dt_utc)

    if moon_alt <= 0:
        return {"moon_altitude_deg": moon_alt, "moon_phase_pct": round(phase_frac * 100, 1),
                "angular_separation_deg": None, "interference_score": 0.0}

    ts = _get_timescale()
    eph = _get_ephemeris()
    t = ts.from_datetime(dt_utc.replace(tzinfo=timezone.utc) if dt_utc.tzinfo is None else dt_utc)

    observer = eph["earth"] + wgs84.latlon(lat, lon)
    moon_app = observer.at(t).observe(eph["moon"]).apparent()
    moon_ra, moon_dec, _ = moon_app.radec()

    tgt = Star(ra_hours=target_ra_deg / 15.0, dec_degrees=target_dec_deg)
    tgt_app = observer.at(t).observe(tgt).apparent()
    tgt_ra, tgt_dec, _ = tgt_app.radec()

    ra1, dec1 = math.radians(float(moon_ra._degrees)), math.radians(float(moon_dec.degrees))
    ra2, dec2 = math.radians(float(tgt_ra._degrees)), math.radians(float(tgt_dec.degrees))
    a = math.sin((dec2 - dec1) / 2) ** 2 + math.cos(dec1) * math.cos(dec2) * math.sin((ra2 - ra1) / 2) ** 2
    sep_deg = round(math.degrees(2 * math.asin(math.sqrt(min(a, 1.0)))), 1)

    proximity = max(0.0, 1.0 - (sep_deg / 90.0))
    interference = round(phase_frac * proximity, 3)

    return {
        "moon_altitude_deg": moon_alt,
        "moon_phase_pct": round(phase_frac * 100, 1),
        "angular_separation_deg": sep_deg,
        "interference_score": min(1.0, interference),
    }


# ── Person A API: typed Pydantic returns used by Choreographer / Curator ──────
# These import from models — keep at bottom to avoid circular imports.

def get_twilight_times(lat: float, lon: float, for_date: date):
    """
    Return typed TwilightTimes (dark_start / dark_end = A1 true-darkness window).

    Skyfield states: 4=day 3=civil 2=nautical 1=astro twilight 0=night
    """
    from app.models.plan_state import TwilightTimes

    eph = _get_ephemeris()
    ts = _get_timescale()
    location = wgs84.latlon(lat, lon)

    next_date = for_date + timedelta(days=1)
    t0 = ts.utc(for_date.year, for_date.month, for_date.day, 12)
    t1 = ts.utc(next_date.year, next_date.month, next_date.day, 13)

    f = almanac.dark_twilight_day(eph, location)
    times, events = almanac.find_discrete(t0, t1, f)

    result: dict[str, Optional[datetime]] = {
        "sunset": None, "astronomical_dusk": None,
        "dark_start": None, "dark_end": None,
        "astronomical_dawn": None, "sunrise": None,
    }
    night_found = False
    for t, ev in zip(times, events):
        ev = int(ev)
        dt = t.utc_datetime()
        if not night_found:
            if ev == 3 and not result["sunset"]:
                result["sunset"] = dt
            elif ev == 1 and not result["astronomical_dusk"]:
                result["astronomical_dusk"] = dt
            elif ev == 0:
                result["dark_start"] = dt
                night_found = True
        else:
            if ev == 1 and not result["dark_end"]:
                result["dark_end"] = dt
            elif ev == 2 and not result["astronomical_dawn"]:
                result["astronomical_dawn"] = dt
            elif ev == 4 and not result["sunrise"]:
                result["sunrise"] = dt

    logger.debug("Twilight %s: dark %s → %s", for_date, result["dark_start"], result["dark_end"])
    return TwilightTimes(**result)


def get_object_events(name: str, lat: float, lon: float, for_date: date,
                      ra_hours: Optional[float] = None, dec_degrees: Optional[float] = None):
    """
    Return typed ObjectEvents (rise / set / transit) for one object on one night.
    """
    from app.models.plan_state import ObjectEvents

    eph = _get_ephemeris()
    ts = _get_timescale()
    location = wgs84.latlon(lat, lon)
    observer = eph["earth"] + location

    planet_key = PLANET_MAP.get(name.lower())
    if planet_key:
        target = eph[planet_key]
    elif ra_hours is not None and dec_degrees is not None:
        target = Star(ra_hours=ra_hours, dec_degrees=dec_degrees)
    else:
        raise ValueError(f"Unknown object '{name}' — provide ra_hours + dec_degrees for fixed targets.")

    next_date = for_date + timedelta(days=1)
    t0 = ts.utc(for_date.year, for_date.month, for_date.day, 12)
    t1 = ts.utc(next_date.year, next_date.month, next_date.day, 13)

    f = almanac.risings_and_settings(eph, target, location)
    times, events = almanac.find_discrete(t0, t1, f)

    rise_time: Optional[datetime] = None
    set_time: Optional[datetime] = None
    for t, ev in zip(times, events):
        dt = t.utc_datetime()
        if int(ev) == 1 and rise_time is None:
            rise_time = dt
        elif int(ev) == 0 and set_time is None:
            set_time = dt

    # Transit: sample every 5 min, find peak altitude
    mins = list(range(0, 25 * 60 + 1, 5))
    t_samples = ts.utc(for_date.year, for_date.month, for_date.day, 12, mins)
    alt_arr, _, _ = observer.at(t_samples).observe(target).apparent().altaz()
    alt_deg = alt_arr.degrees

    transit_time: Optional[datetime] = None
    alt_at_transit: Optional[float] = None
    max_idx = int(alt_deg.argmax())
    if float(alt_deg[max_idx]) > 0:
        transit_time = t_samples[max_idx].utc_datetime()
        alt_at_transit = round(float(alt_deg[max_idx]), 1)

    return ObjectEvents(name=name, rise=rise_time, set=set_time,
                        transit=transit_time, altitude_at_transit=alt_at_transit)


def get_moon_info(lat: float, lon: float, at_datetime: datetime):
    """Return typed MoonInfo (phase, altitude, azimuth, RA/Dec for A2 scoring)."""
    from app.models.plan_state import MoonInfo

    eph = _get_ephemeris()
    ts = _get_timescale()
    location = wgs84.latlon(lat, lon)
    observer = eph["earth"] + location

    t = ts.from_datetime(at_datetime)
    phase_angle = almanac.moon_phase(eph, t).degrees
    illumination = (1.0 - math.cos(math.radians(phase_angle))) / 2.0

    astrometric = observer.at(t).observe(eph["moon"])
    apparent = astrometric.apparent()
    alt, az, _ = apparent.altaz()
    ra, dec, _ = apparent.radec()

    return MoonInfo(
        illumination=round(illumination, 3),
        altitude=round(float(alt.degrees), 1),
        azimuth=round(float(az.degrees), 1),
        phase_name=_phase_name(phase_angle),
        ra_hours=round(float(ra.hours), 4),
        dec_degrees=round(float(dec.degrees), 4),
    )


def score_moon_interference(target_ra_hours: float, target_dec_degrees: float, moon) -> float:
    """
    A2: Numeric 0.0 (none) – 1.0 (severe) interference score.
    Moon below horizon → 0.0. Score = illumination × (1 − sep_factor), sep_factor ramps 0→1 at 60°.
    """
    if moon.altitude < 0:
        return 0.0
    sep = _angular_sep_deg(target_ra_hours, target_dec_degrees, moon.ra_hours, moon.dec_degrees)
    sep_factor = min(sep / 60.0, 1.0)
    return round(max(0.0, min(1.0, moon.illumination * (1.0 - sep_factor))), 3)


# ── Internal helpers ─────────────────────────────────────────────────────────

def _angular_sep_deg(ra1_h: float, dec1_d: float, ra2_h: float, dec2_d: float) -> float:
    """Haversine angular separation. RA in hours, Dec in degrees."""
    r1, r2 = math.radians(ra1_h * 15.0), math.radians(ra2_h * 15.0)
    d1, d2 = math.radians(dec1_d), math.radians(dec2_d)
    a = math.sin((d2 - d1) / 2) ** 2 + math.cos(d1) * math.cos(d2) * math.sin((r2 - r1) / 2) ** 2
    return math.degrees(2 * math.asin(math.sqrt(min(a, 1.0))))


def _phase_name(angle: float) -> str:
    a = angle % 360
    if a < 22.5 or a >= 337.5: return "New Moon"
    if a < 67.5: return "Waxing Crescent"
    if a < 112.5: return "First Quarter"
    if a < 157.5: return "Waxing Gibbous"
    if a < 202.5: return "Full Moon"
    if a < 247.5: return "Waning Gibbous"
    if a < 292.5: return "Last Quarter"
    return "Waning Crescent"
