"""Loaders for static data files (sites, events calendar)."""

import json
from functools import lru_cache
from pathlib import Path

from app.models import CelestialEvent, Site

DATA_DIR = Path(__file__).parent

SITES_FILE = DATA_DIR / "sites.json"
EVENTS_FILE = DATA_DIR / "events_calendar.json"


@lru_cache(maxsize=1)
def load_sites() -> list[Site]:
    """Load and validate all sites from the static JSON file."""
    raw = json.loads(SITES_FILE.read_text(encoding="utf-8"))
    return [Site.model_validate(entry) for entry in raw]


@lru_cache(maxsize=1)
def load_events() -> list[CelestialEvent]:
    """Load and validate all celestial events from the static JSON file."""
    raw = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    return [CelestialEvent.model_validate(entry) for entry in raw]


def get_site_by_id(site_id: str) -> Site | None:
    """Look up a single site by ID."""
    for site in load_sites():
        if site.id == site_id:
            return site
    return None
