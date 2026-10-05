"""
Shared pipeline state schema — the contract between all agents.

Step 7: These Pydantic models are the single source of truth for
what data flows between Curator → Location Scout → Weather →
Choreographer → Gear → Story.
"""

import math
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Ephemeris types (returned by services/ephemeris.py) ─────────────────────

class TwilightTimes(BaseModel):
    """
    Key darkness boundaries for one night. All times UTC.

    dark_start / dark_end mark when the Sun is >18° below the horizon —
    the only interval where faint objects are truly visible. (A1)
    """
    sunset: Optional[datetime] = None
    astronomical_dusk: Optional[datetime] = None   # Sun at −12°
    dark_start: Optional[datetime] = None          # Sun at −18° ↓  (A1)
    dark_end: Optional[datetime] = None            # Sun at −18° ↑  (A1)
    astronomical_dawn: Optional[datetime] = None   # Sun at −12° ↑
    sunrise: Optional[datetime] = None


class ObjectEvents(BaseModel):
    """Rise / set / transit for a single celestial object on one night."""
    name: str
    rise: Optional[datetime] = None
    set: Optional[datetime] = None
    transit: Optional[datetime] = None
    altitude_at_transit: Optional[float] = None    # degrees


class MoonInfo(BaseModel):
    """Moon state at a specific moment — used for interference scoring (A2)."""
    illumination: float          # 0.0 – 1.0
    altitude: float              # degrees  (negative = below horizon)
    azimuth: float               # degrees
    phase_name: str
    ra_hours: float = 0.0        # equatorial RA (for angular-separation calc)
    dec_degrees: float = 0.0     # equatorial Dec


# ── Pipeline state models ────────────────────────────────────────────────────

class EquipmentLevel(str, Enum):
    naked_eye = "naked_eye"
    binoculars = "binoculars"
    telescope = "telescope"


class UserInput(BaseModel):
    lat: float
    lon: float
    date_start: date
    date_end: date
    equipment_level: EquipmentLevel = EquipmentLevel.binoculars
    city_hint: Optional[str] = None          # e.g. "Bangalore"


class SiteInfo(BaseModel):
    """One dark-sky site from sites.json, enriched by Location Scout."""
    id: str
    name: str
    lat: float
    lon: float
    altitude_m: int
    bortle_class: int                        # 1 (darkest) – 9 (brightest)
    # Cardinal/intercardinal direction → degrees of horizon blocked below that altitude
    # e.g. {"SE": 15, "S": 10} means SE horizon is blocked below 15°
    horizon_blocks: dict[str, int] = Field(default_factory=dict)
    horizon_notes: str = ""
    road_access: str = ""
    night_permit: str = ""
    distance_km: Optional[float] = None
    distance_from: dict[str, float] = Field(default_factory=dict)


class WeatherWindow(BaseModel):
    """One forecasted time block at a specific site."""
    site_id: str
    start: datetime
    end: datetime
    cloud_cover_pct: float       # 0 – 100
    seeing: int                  # 1 – 8  (7Timer scale, 8 = best)
    transparency: int            # 1 – 8
    temperature_c: float
    humidity_pct: float

    @property
    def is_clear(self) -> bool:
        return self.cloud_cover_pct < 30


class RankedEvent(BaseModel):
    """
    One celestial event after the Curator has filtered and ranked it.
    Populated progressively: catalog fields first, ephemeris fields added later.
    """
    id: str
    name: str
    type: str                    # "meteor_shower" | "opposition" | "conjunction" | "deep_sky"
    peak_datetime: datetime
    priority_stars: int = 0      # 1 – 5 (assigned by Curator)
    reason: str = ""

    # Catalog fields
    zhr: Optional[int] = None           # Zenithal Hourly Rate (meteor showers)
    min_bortle_class: int = 6
    equipment: str = "binoculars"
    optimal_direction: Optional[str] = None
    best_hours: Optional[str] = None
    radiant_ra_hours: Optional[float] = None
    radiant_dec_degrees: Optional[float] = None
    target_planet: Optional[str] = None  # for oppositions/conjunctions

    # Ephemeris-computed (filled by Curator / Choreographer)
    rise: Optional[datetime] = None
    set: Optional[datetime] = None
    altitude_at_transit: Optional[float] = None
    moon_interference_score: float = 0.0   # A2: 0 = no interference, 1 = severe


class ScheduleSlot(BaseModel):
    """One entry in the Choreographer's minute-resolution schedule."""
    start: datetime
    end: datetime
    object_name: str
    direction: Optional[str] = None      # compass bearing text, e.g. "NE"
    altitude_deg: Optional[float] = None
    note: str = ""
    is_dark_adaptation: bool = False     # A5: dark-adapt / transition note


class PlanState(BaseModel):
    """
    The mutable plan object that accumulates state as it flows through the
    orchestrator pipeline. Each agent reads what it needs and writes its
    output back into this object.
    """
    user_input: UserInput

    # Populated by each agent in sequence
    site: Optional[SiteInfo] = None
    weather_windows: list[WeatherWindow] = Field(default_factory=list)
    ranked_events: list[RankedEvent] = Field(default_factory=list)
    schedule: list[ScheduleSlot] = Field(default_factory=list)
    gear_list: list[str] = Field(default_factory=list)
    story_blurbs: dict[str, str] = Field(default_factory=dict)
    dark_adaptation_notes: list[str] = Field(default_factory=list)  # A5

    # Meta
    contingency_triggered: bool = False
    pipeline_log: list[str] = Field(default_factory=list)

    def log(self, msg: str) -> None:
        """Append a step message to the pipeline log."""
        self.pipeline_log.append(msg)
