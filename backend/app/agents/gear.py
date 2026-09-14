"""
Gear & Prep Agent.

Rule-based (no LLM needed): given site conditions, forecasted temperature,
event types, and user equipment level, produces a personalized packing list
with categorized items (essential / recommended / optional) and warnings.

Key behaviors:
- Temperature-aware clothing recommendations
- Equipment matched to event type (meteor = naked eye, deep sky = telescope)
- Dark-adaptation warnings
- Site-specific notes (altitude, trek, etc.)
"""

import logging
from typing import Optional

from app.models import (
    CelestialEvent,
    EquipmentLevel,
    GearCategory,
    GearItem,
    GearList,
    Site,
    SiteWeatherForecast,
)

logger = logging.getLogger(__name__)

# Temperature thresholds (°C)
COLD_THRESHOLD = 10
VERY_COLD_THRESHOLD = 5
FREEZING_THRESHOLD = 0


def generate_gear_list(
    site: Site,
    events: list[CelestialEvent],
    equipment_level: EquipmentLevel,
    weather: Optional[SiteWeatherForecast] = None,
) -> GearList:
    """
    Generate a personalized packing list based on site, events, and conditions.

    Args:
        site: The chosen observation site.
        events: Celestial events planned for viewing.
        equipment_level: User's equipment (naked_eye, binoculars, telescope).
        weather: Weather forecast for temperature/humidity planning.

    Returns:
        GearList with categorized items and warnings.
    """
    items: list[GearItem] = []
    warnings: list[str] = []

    # ── Always essential ──────────────────────────────────────────────
    items.append(GearItem(
        name="Red headlamp / red flashlight",
        category=GearCategory.essential,
        reason="White light destroys dark adaptation for 20+ minutes. Red light preserves night vision.",
    ))
    items.append(GearItem(
        name="Water bottle (1L minimum)",
        category=GearCategory.essential,
        reason="Dehydration is common during long observation sessions.",
    ))
    items.append(GearItem(
        name="Fully charged phone (with star map app)",
        category=GearCategory.essential,
        reason="Use Stellarium Mobile or SkySafari. Enable red-screen mode to protect night vision.",
    ))

    # ── Temperature-based clothing ────────────────────────────────────
    min_temp = _get_min_temp(weather, site)

    if min_temp is not None:
        if min_temp <= FREEZING_THRESHOLD:
            items.extend([
                GearItem(name="Heavy winter jacket", category=GearCategory.essential,
                         reason=f"Expected temperature as low as {min_temp}°C."),
                GearItem(name="Thermal inner layers", category=GearCategory.essential,
                         reason="Base layer is critical — you'll be standing/sitting still in the cold."),
                GearItem(name="Insulated gloves (touchscreen-compatible)", category=GearCategory.essential,
                         reason="Fingers go numb fast when not moving. Touchscreen tips for phone use."),
                GearItem(name="Warm beanie / balaclava", category=GearCategory.essential,
                         reason="30% of body heat is lost through the head."),
                GearItem(name="Thick wool socks + insulated shoes", category=GearCategory.essential,
                         reason="Cold ground pulls heat from your feet."),
                GearItem(name="Hand warmers (chemical/reusable)", category=GearCategory.recommended,
                         reason="Cheap, lightweight, and invaluable at sub-zero temperatures."),
            ])
            warnings.append(f"⚠️ Extremely cold: expected {min_temp}°C. Dress for standing still in the cold for hours — you'll feel colder than the number suggests because you're not moving.")
        elif min_temp <= VERY_COLD_THRESHOLD:
            items.extend([
                GearItem(name="Warm jacket / fleece", category=GearCategory.essential,
                         reason=f"Expected temperature around {min_temp}°C."),
                GearItem(name="Warm hat / beanie", category=GearCategory.essential, reason="Keeps core temperature up."),
                GearItem(name="Gloves", category=GearCategory.recommended, reason="Fingers get cold when not moving."),
                GearItem(name="Warm socks", category=GearCategory.recommended, reason="Standing on cold ground."),
            ])
        elif min_temp <= COLD_THRESHOLD:
            items.extend([
                GearItem(name="Light jacket / hoodie", category=GearCategory.essential,
                         reason=f"Night temperature around {min_temp}°C — cooler than daytime."),
                GearItem(name="Long pants", category=GearCategory.recommended, reason="Shorts + cold + insects = bad time."),
            ])
        else:
            items.append(GearItem(
                name="Light layers (can get breezy at night)",
                category=GearCategory.recommended,
                reason=f"Temperature around {min_temp}°C — comfortable but layer up just in case.",
            ))

    # ── Event-specific gear ───────────────────────────────────────────
    event_types = set(e.type for e in events)
    has_meteor = "meteor_shower" in event_types
    has_deep_sky = any(e.type in ("opposition", "seasonal", "elongation") for e in events)
    has_eclipse_solar = any(e.type == "eclipse" and "solar" in e.name.lower() for e in events)

    if has_meteor:
        items.extend([
            GearItem(name="Reclining chair / sleeping pad + blanket",
                     category=GearCategory.essential,
                     reason="Meteors are best watched lying down, looking at the whole sky. Neck cramps are real."),
            GearItem(name="Sleeping bag (if overnight)", category=GearCategory.recommended,
                     reason="Meteor peaks are often post-midnight. Warmth + comfort = longer watching."),
        ])
        warnings.append("🔭 Telescopes are NOT useful for meteor showers — they narrow your field of view. Watch with naked eyes!")

    if has_deep_sky and equipment_level in (EquipmentLevel.binoculars, EquipmentLevel.telescope):
        if equipment_level == EquipmentLevel.binoculars:
            items.append(GearItem(
                name="Binoculars (7x50 or 10x50 ideal)",
                category=GearCategory.essential,
                reason="Wide field of view, gathers more light than your eyes. Great for star clusters, nebulae, and Jupiter's moons.",
            ))
            items.append(GearItem(
                name="Binocular tripod adapter",
                category=GearCategory.recommended,
                reason="Arms tire quickly holding binoculars up. A tripod eliminates shake.",
            ))
        elif equipment_level == EquipmentLevel.telescope:
            items.extend([
                GearItem(name="Telescope + mount (fully assembled + tested before trip)",
                         category=GearCategory.essential,
                         reason="Don't try to learn your telescope in the dark at the site."),
                GearItem(name="Multiple eyepieces (low + high magnification)",
                         category=GearCategory.essential,
                         reason="Low power for finding targets, high power for detail on planets."),
                GearItem(name="Dew shield / lens warmer",
                         category=GearCategory.recommended,
                         reason="Dew on optics ruins observations. Prevention is easier than cure."),
            ])

    if has_eclipse_solar:
        items.append(GearItem(
            name="ISO 12312-2 certified solar eclipse glasses",
            category=GearCategory.essential,
            reason="NEVER look at the Sun without certified solar filters. Regular sunglasses are NOT safe.",
        ))
        warnings.append("☀️ SAFETY CRITICAL: Never look at the Sun without proper ISO 12312-2 certified solar filters. Permanent eye damage occurs in seconds.")

    # ── Comfort & utility ─────────────────────────────────────────────
    items.extend([
        GearItem(name="Snacks (energy bars, nuts, dried fruit)",
                 category=GearCategory.recommended,
                 reason="Long nights need fuel. Avoid strong-smelling food that attracts animals."),
        GearItem(name="Hot drinks in thermos",
                 category=GearCategory.recommended,
                 reason="Warm drinks are morale boosters on cold, long observation nights."),
        GearItem(name="Insect repellent",
                 category=GearCategory.recommended,
                 reason="Mosquitoes are active at night, especially near water or vegetation."),
    ])

    # ── Site-specific additions ───────────────────────────────────────
    if site.altitude_m >= 3000:
        items.append(GearItem(
            name="Altitude sickness medication (Acetazolamide / Diamox)",
            category=GearCategory.essential,
            reason=f"Site is at {site.altitude_m}m — AMS risk is real. Consult a doctor before the trip.",
        ))
        warnings.append(f"🏔️ Altitude warning: {site.name} is at {site.altitude_m}m. Spend 1-2 days acclimatizing before the observation night. Watch for headache, nausea, and dizziness.")

    if not site.amenities.food_water_nearby:
        items.append(GearItem(
            name="Extra water + packed meal",
            category=GearCategory.essential,
            reason="No food/water available near the site. Carry everything you'll need.",
        ))

    if not site.amenities.restrooms:
        items.append(GearItem(
            name="Toilet supplies (tissues, hand sanitizer, plastic bag)",
            category=GearCategory.essential,
            reason="No restroom facilities at the site.",
        ))

    if "trek" in site.access.night_access_notes.lower():
        items.extend([
            GearItem(name="Trekking shoes with good grip",
                     category=GearCategory.essential,
                     reason="Night trek to the observation point. Loose shoes + dark trails = danger."),
            GearItem(name="Trekking poles",
                     category=GearCategory.recommended,
                     reason="Stability on uneven terrain at night."),
        ])
        warnings.append("🥾 Night trek required. Pack light — every gram matters after 2 hours of climbing.")

    # ── Humidity / dew warnings ───────────────────────────────────────
    if weather and weather.hourly:
        max_rh = max(
            (h.relative_humidity_pct for h in weather.hourly if h.relative_humidity_pct is not None),
            default=0,
        )
        if max_rh > 85:
            warnings.append("💧 High humidity forecast — dew likely on optics. Bring dew shields and a 12V hairdryer if using a telescope.")

    # ── Universal warnings ────────────────────────────────────────────
    warnings.extend([
        "🔴 No white light after dark. Use ONLY red-filtered light. One flash of white light ruins everyone's dark adaptation for 20 minutes.",
        "📱 Set your phone to red-screen mode or minimum brightness. Better yet, put it away during peak observation.",
    ])

    return GearList(items=items, warnings=warnings)


def _get_min_temp(weather: Optional[SiteWeatherForecast], site: Site) -> Optional[float]:
    """Get the expected minimum temperature, from weather or altitude estimate."""
    if weather and weather.hourly:
        temps = [h.temperature_c for h in weather.hourly if h.temperature_c is not None]
        if temps:
            return min(temps)

    # Rough estimate from altitude: -6.5°C per 1000m (lapse rate) from 25°C sea level baseline
    if site.altitude_m > 500:
        estimated = 25 - (site.altitude_m / 1000) * 6.5
        return round(estimated, 1)

    return None
