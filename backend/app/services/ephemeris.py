"""
Ephemeris Service — Skyfield wrapper.

Provides astronomical calculations:
  - Rise/set times for Sun, Moon, and planets
  - Altitude/azimuth of objects at a given time
  - Astronomical twilight (Sun 18° below horizon — true darkness)
  - Moon phase (% illumination)
  - Angular separation between two sky positions (for moon interference)

All times are UTC. The caller is responsible for timezone conversion.
"""

import logging
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional

from skyfield import almanac
from skyfield.api import Loader, Star, Topos, wgs84
from skyfield.timelib import Time

logger = logging.getLogger(__name__)

# ── Skyfield data loading (cached, downloads once) ────────────────────

_loader = Loader("~/.skyfield-data", verbose=False)


@lru_cache(maxsize=1)
def _get_ephemeris():
    """Load the planetary ephemeris (de421.bsp — small, covers 1900–2050)."""
    return _loader("de421.bsp")


@lru_cache(maxsize=1)
def _get_timescale():
    """Load the timescale (needs finals2000A.all for precise UT1)."""
    return _loader.timescale()


# ── Planet name → Skyfield target mapping ─────────────────────────────

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
    """Resolve an object name to a Skyfield target."""
    eph = _get_ephemeris()
    key = name.strip().lower()
    if key in PLANET_MAP:
        return eph[PLANET_MAP[key]]
    # If it has RA/Dec, the caller should use compute_altitude_azimuth_radec
    raise ValueError(f"Unknown target: {name}. Use RA/Dec for deep sky objects.")


# ── Core computations ─────────────────────────────────────────────────

def compute_altitude_azimuth(
    target_name: str,
    lat: float,
    lon: float,
    dt_utc: datetime,
) -> dict:
    """
    Compute altitude and azimuth of a solar system object.

    Args:
        target_name: Planet/Moon/Sun name (case-insensitive).
        lat, lon: Observer coordinates.
        dt_utc: Observation time (UTC).

    Returns:
        {"altitude_deg": float, "azimuth_deg": float, "is_above_horizon": bool}
    """
    ts = _get_timescale()
    eph = _get_ephemeris()
    t = ts.from_datetime(dt_utc.replace(tzinfo=timezone.utc) if dt_utc.tzinfo is None else dt_utc)

    earth = eph["earth"]
    observer = earth + wgs84.latlon(lat, lon)
    target = _get_target(target_name)

    astrometric = observer.at(t).observe(target)
    apparent = astrometric.apparent()
    alt, az, _ = apparent.altaz()

    return {
        "altitude_deg": round(float(alt.degrees), 2),
        "azimuth_deg": round(float(az.degrees), 2),
        "is_above_horizon": bool(alt.degrees > 0),
    }


def compute_altitude_azimuth_radec(
    ra_deg: float,
    dec_deg: float,
    lat: float,
    lon: float,
    dt_utc: datetime,
) -> dict:
    """
    Compute altitude and azimuth of a fixed RA/Dec position (deep sky objects, radiants).

    Args:
        ra_deg, dec_deg: Right ascension and declination in degrees.
        lat, lon: Observer coordinates.
        dt_utc: Observation time (UTC).

    Returns:
        {"altitude_deg": float, "azimuth_deg": float, "is_above_horizon": bool}
    """
    ts = _get_timescale()
    eph = _get_ephemeris()
    t = ts.from_datetime(dt_utc.replace(tzinfo=timezone.utc) if dt_utc.tzinfo is None else dt_utc)

    earth = eph["earth"]
    observer = earth + wgs84.latlon(lat, lon)

    # Convert RA from degrees to hours for Skyfield
    ra_hours = ra_deg / 15.0
    target = Star(ra_hours=ra_hours, dec_degrees=dec_deg)

    astrometric = observer.at(t).observe(target)
    apparent = astrometric.apparent()
    alt, az, _ = apparent.altaz()

    return {
        "altitude_deg": round(float(alt.degrees), 2),
        "azimuth_deg": round(float(az.degrees), 2),
        "is_above_horizon": bool(alt.degrees > 0),
    }


def compute_rise_set(
    target_name: str,
    lat: float,
    lon: float,
    date_utc: datetime,
) -> dict:
    """
    Compute rise and set times for a solar system object on a given date.

    Args:
        target_name: Planet/Moon/Sun name.
        lat, lon: Observer coordinates.
        date_utc: The date (UTC) to compute for.

    Returns:
        {"rise_utc": datetime|None, "set_utc": datetime|None, "is_circumpolar": bool}
    """
    ts = _get_timescale()
    eph = _get_ephemeris()

    # Search window: the given date ± 12 hours
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
        if event:  # rise
            if rise_utc is None:
                rise_utc = dt
        else:  # set
            if set_utc is None:
                set_utc = dt

    return {
        "rise_utc": rise_utc,
        "set_utc": set_utc,
        "is_circumpolar": rise_utc is None and set_utc is None,
    }


def compute_astronomical_twilight(
    lat: float,
    lon: float,
    date_utc: datetime,
) -> dict:
    """
    Compute when astronomical twilight ends (evening) and begins (morning).

    Astronomical twilight = Sun 18° below horizon. After this, the sky is
    truly dark for deep sky observation.

    Returns:
        {"twilight_end_utc": datetime|None, "twilight_start_utc": datetime|None}
        twilight_end = evening (darkness begins)
        twilight_start = morning (dawn begins)
    """
    ts = _get_timescale()
    eph = _get_ephemeris()

    d = date_utc.replace(hour=12, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    t0 = ts.from_datetime(d)
    t1 = ts.from_datetime(d + timedelta(hours=24))

    observer = wgs84.latlon(lat, lon)

    f = almanac.dark_twilight_day(eph, observer)
    times, events = almanac.find_discrete(t0, t1, f)

    twilight_end = None    # evening: transition to dark (event goes to 0)
    twilight_start = None  # morning: transition from dark (event leaves 0)

    # Events: 0=dark, 1=astro twilight, 2=nautical, 3=civil, 4=day
    prev_event = None
    for t, event in zip(times, events):
        dt = t.utc_datetime()
        if prev_event is not None:
            # Entering darkness: previous was 1 (astro twilight), now 0 (dark)
            if prev_event >= 1 and event == 0 and twilight_end is None:
                twilight_end = dt
            # Leaving darkness: previous was 0 (dark), now >= 1
            if prev_event == 0 and event >= 1 and twilight_start is None:
                twilight_start = dt
        prev_event = event

    return {
        "twilight_end_utc": twilight_end,
        "twilight_start_utc": twilight_start,
    }


def compute_moon_phase(dt_utc: datetime) -> float:
    """
    Compute the Moon's illumination fraction at a given time.

    Returns: float between 0.0 (new moon) and 1.0 (full moon).
    """
    ts = _get_timescale()
    eph = _get_ephemeris()
    t = ts.from_datetime(dt_utc.replace(tzinfo=timezone.utc) if dt_utc.tzinfo is None else dt_utc)

    # Use Skyfield's built-in fraction_illuminated for the Moon
    earth = eph["earth"]
    sun = eph["sun"]
    moon = eph["moon"]

    e = earth.at(t)
    s = e.observe(sun).apparent()
    m = e.observe(moon).apparent()

    # The elongation between sun and moon gives the phase
    # fraction_illuminated computes it correctly
    from skyfield.framelib import ecliptic_frame
    _, sun_lon, _ = s.frame_latlon(ecliptic_frame)
    _, moon_lon, _ = m.frame_latlon(ecliptic_frame)

    import math
    phase_angle = (moon_lon.degrees - sun_lon.degrees) % 360
    # Illumination fraction: (1 - cos(phase_angle)) / 2
    illumination = (1 - math.cos(math.radians(phase_angle))) / 2
    return round(float(illumination), 3)


def compute_moon_interference(
    target_ra_deg: float,
    target_dec_deg: float,
    lat: float,
    lon: float,
    dt_utc: datetime,
) -> dict:
    """
    Compute how much the Moon interferes with observing a target.

    Returns:
        {
            "moon_altitude_deg": float,
            "moon_phase_pct": float (0-100),
            "angular_separation_deg": float,
            "interference_score": float (0=none, 1=severe)
        }

    Interference logic:
    - Moon below horizon → 0 interference regardless of phase
    - Moon above horizon → interference = phase × (1 / angular_separation)
    - Target 20° from 90% moon → severe interference
    - Target 120° from 40% moon → negligible interference
    """
    import math

    # Get Moon position
    moon_pos = compute_altitude_azimuth("moon", lat, lon, dt_utc)
    moon_alt = moon_pos["altitude_deg"]

    # Moon phase
    phase_frac = compute_moon_phase(dt_utc)
    phase_pct = round(phase_frac * 100, 1)

    # If Moon is below horizon, no interference
    if moon_alt <= 0:
        return {
            "moon_altitude_deg": moon_alt,
            "moon_phase_pct": phase_pct,
            "angular_separation_deg": None,
            "interference_score": 0.0,
        }

    # Compute angular separation between target and Moon
    ts = _get_timescale()
    eph = _get_ephemeris()
    t = ts.from_datetime(dt_utc.replace(tzinfo=timezone.utc) if dt_utc.tzinfo is None else dt_utc)

    earth = eph["earth"]
    observer = earth + wgs84.latlon(lat, lon)

    # Moon apparent position
    moon_app = observer.at(t).observe(eph["moon"]).apparent()
    moon_ra, moon_dec, _ = moon_app.radec()

    # Target position
    target_ra_hours = target_ra_deg / 15.0
    target_star = Star(ra_hours=target_ra_hours, dec_degrees=target_dec_deg)
    target_app = observer.at(t).observe(target_star).apparent()
    target_ra, target_dec, _ = target_app.radec()

    # Angular separation using the haversine formula on the celestial sphere
    ra1, dec1 = math.radians(moon_ra._degrees), math.radians(moon_dec.degrees)
    ra2, dec2 = math.radians(target_ra._degrees), math.radians(target_dec.degrees)

    dra = ra2 - ra1
    ddec = dec2 - dec1
    a = math.sin(ddec / 2) ** 2 + math.cos(dec1) * math.cos(dec2) * math.sin(dra / 2) ** 2
    sep_deg = round(math.degrees(2 * math.asin(math.sqrt(a))), 1)

    # Interference score: phase × proximity factor
    # Proximity factor: 1.0 at 0°, drops off with distance
    # At 30° separation → factor ~0.5, at 90° → ~0.1
    proximity = max(0.0, 1.0 - (sep_deg / 90.0))
    interference = round(phase_frac * proximity, 3)

    return {
        "moon_altitude_deg": moon_alt,
        "moon_phase_pct": phase_pct,
        "angular_separation_deg": sep_deg,
        "interference_score": min(1.0, interference),
    }
