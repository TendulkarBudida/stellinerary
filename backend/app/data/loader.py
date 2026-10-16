"""Loader for the static celestial events calendar.

Observing sites are discovered live (see app.services.site_discovery);
no static site list exists.
"""

import json
from functools import lru_cache
from pathlib import Path

from app.models import CelestialEvent

DATA_DIR = Path(__file__).parent

EVENTS_FILE = DATA_DIR / "events_calendar.json"


@lru_cache(maxsize=1)
def load_events() -> list[CelestialEvent]:
    """Load and validate all celestial events from the static JSON file."""
    raw = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    return [CelestialEvent.model_validate(entry) for entry in raw]
