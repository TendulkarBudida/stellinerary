"""Pydantic schemas for sites, events, and shared orchestration state."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Equipment levels ──────────────────────────────────────────────────

class EquipmentLevel(str, Enum):
    naked_eye = "naked_eye"
    binoculars = "binoculars"
    telescope = "telescope"
    solar_filter = "solar_filter"


# ── Site schemas ──────────────────────────────────────────────────────

class HorizonBlock(BaseModel):
    """An arc of the horizon blocked by terrain."""
    azimuth_start: int = Field(..., ge=0, lt=360, description="Start azimuth (degrees, 0=N, 90=E)")
    azimuth_end: int = Field(..., ge=0, lt=360, description="End azimuth")
    max_blocked_altitude_deg: int = Field(..., ge=0, le=90, description="Objects below this altitude in the blocked arc are not visible")


class HorizonProfile(BaseModel):
    description: str
    blocked_directions: list[HorizonBlock] = Field(default_factory=list)


class SiteAccess(BaseModel):
    road_quality: str
    night_access: bool
    night_access_notes: str = ""
    parking: bool = True
    entry_fee: bool = False


class SiteAmenities(BaseModel):
    restrooms: bool = False
    food_water_nearby: bool = False
    camping_allowed: bool = False
    shelter_available: bool = False
    mobile_signal: str = "none"


class Site(BaseModel):
    id: str
    name: str
    state: str
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    altitude_m: int = Field(..., ge=0)
    bortle_class: int = Field(..., ge=1, le=9)
    horizon_profile: HorizonProfile
    access: SiteAccess
    amenities: SiteAmenities
    city_distances_km: dict[str, int | float] = Field(default_factory=dict)
    best_months: list[str] = Field(default_factory=list)
    notes: str = ""


# ── Celestial event schemas ───────────────────────────────────────────

class CelestialEvent(BaseModel):
    id: str
    name: str
    type: str  # meteor_shower, opposition, elongation, eclipse, seasonal
    peak_date: date
    active_start: date
    active_end: date
    description: str = ""

    # Optional fields — varies by event type
    zhr: Optional[int] = None  # Zenithal Hourly Rate (meteor showers)
    speed_km_s: Optional[int] = None
    parent_body: Optional[str] = None
    radiant_constellation: Optional[str] = None
    radiant_ra_deg: Optional[float] = None
    radiant_dec_deg: Optional[float] = None
    target_object: Optional[str] = None

    viewing_direction: Optional[str] = None
    best_hours: Optional[str] = None
    equipment: EquipmentLevel = EquipmentLevel.naked_eye
    min_bortle: int = Field(default=5, ge=1, le=9, description="Maximum Bortle class at which this event is meaningfully visible")

    # Eclipse-specific
    eclipse_start_utc: Optional[str] = None
    eclipse_end_utc: Optional[str] = None
    totality_start_utc: Optional[str] = None
    totality_end_utc: Optional[str] = None
    visibility_from_india: Optional[str] = None


# ── Weather schemas ───────────────────────────────────────────────────

class HourlyWeather(BaseModel):
    """One hour of astro weather data."""
    datetime_utc: datetime
    cloud_cover_pct: int = Field(..., ge=0, le=100)
    seeing_arcsec: Optional[float] = None  # atmospheric seeing (lower = better)
    transparency: Optional[str] = None  # e.g. "above average", "average", "below average"
    temperature_c: Optional[float] = None
    relative_humidity_pct: Optional[int] = None
    wind_speed_kmh: Optional[float] = None


class SiteWeatherForecast(BaseModel):
    """Weather forecast for a specific site."""
    site_id: str
    fetched_at: datetime
    hourly: list[HourlyWeather] = Field(default_factory=list)
    summary: str = ""  # human-readable summary


# ── Location Scout output ────────────────────────────────────────────

class RankedSite(BaseModel):
    """A site with scoring from the Location Scout."""
    site: Site
    distance_km: float
    travel_time_estimate_min: Optional[int] = None
    weather_score: float = Field(default=0.0, ge=0, le=1.0, description="0=cloudy, 1=perfectly clear")
    bortle_score: float = Field(default=0.0, ge=0, le=1.0, description="0=light-polluted, 1=pristine")
    overall_score: float = Field(default=0.0, ge=0, le=1.0)
    ranking_reason: str = ""


# ── Gear schemas ──────────────────────────────────────────────────────

class GearCategory(str, Enum):
    essential = "essential"
    recommended = "recommended"
    optional = "optional"


class GearItem(BaseModel):
    name: str
    category: GearCategory
    reason: str = ""


class GearList(BaseModel):
    items: list[GearItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list, description="e.g., 'DO NOT bring white flashlights'")


# ── Observation schedule schemas ──────────────────────────────────────

class ScheduleEntry(BaseModel):
    """One item on the observation timeline."""
    time_local: str  # e.g. "21:30"
    end_time_local: Optional[str] = None  # e.g. "22:00"
    title: str
    description: str = ""
    direction: Optional[str] = None  # e.g. "Face east"
    altitude_deg: Optional[float] = None
    event_id: Optional[str] = None  # link back to celestial event
    is_weather_dependent: bool = False
    dark_adaptation_note: Optional[str] = None


class ObservationSchedule(BaseModel):
    entries: list[ScheduleEntry] = Field(default_factory=list)
    astronomical_twilight_end: Optional[str] = None  # when true dark begins
    astronomical_twilight_start: Optional[str] = None  # when dawn begins
    moon_rise: Optional[str] = None
    moon_set: Optional[str] = None
    moon_phase_pct: Optional[float] = None


# ── Story / narrative output ──────────────────────────────────────────

class ObjectStory(BaseModel):
    """Narrative blurb for one celestial object/event."""
    event_id: str
    title: str
    story_text: str
    fun_fact: Optional[str] = None
    distance_info: Optional[str] = None
    physics_note: Optional[str] = None


# ── Full plan (shared state) ─────────────────────────────────────────

class PlanRequest(BaseModel):
    """User input for plan generation."""
    user_lat: float = Field(..., ge=-90, le=90)
    user_lon: float = Field(..., ge=-180, le=180)
    user_city: Optional[str] = None
    date_start: date
    date_end: date
    equipment_level: EquipmentLevel = EquipmentLevel.naked_eye


class ExpeditionPlan(BaseModel):
    """
    The shared state object that accumulates as it passes through the
    orchestration pipeline. Each agent enriches a different section.
    """
    request: PlanRequest

    # Filled by Curator
    ranked_events: list[CelestialEvent] = Field(default_factory=list)

    # Filled by Location Scout
    ranked_sites: list[RankedSite] = Field(default_factory=list)
    chosen_site: Optional[Site] = None

    # Filled by Weather agent
    weather_forecast: Optional[SiteWeatherForecast] = None

    # Filled by Choreographer
    schedule: Optional[ObservationSchedule] = None

    # Filled by Gear agent
    gear: Optional[GearList] = None

    # Filled by Story agent
    stories: list[ObjectStory] = Field(default_factory=list)

    # Metadata
    generated_at: Optional[datetime] = None
    contingency_note: Optional[str] = None
