import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.data.loader import load_events, load_sites
from app.models import PlanRequest
from app.orchestrator import generate_plan

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Stellinerary — Night Sky Expedition Orchestrator",
    description="Multi-agent backend that plans a full stargazing outing: what's visible, where to go, when to look, what to bring.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    """Liveness check."""
    return {"status": "ok", "env": settings.env}


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Stellinerary API — see /docs for interactive API docs."}


# ── Debug endpoints (Step 2 verification) ─────────────────────────────

@app.get("/debug/sites", tags=["debug"])
async def debug_sites():
    """Return all loaded sites for verification."""
    sites = load_sites()
    return {"count": len(sites), "sites": [s.model_dump() for s in sites]}


@app.get("/debug/events", tags=["debug"])
async def debug_events():
    """Return all loaded celestial events for verification."""
    events = load_events()
    return {"count": len(events), "events": [e.model_dump() for e in events]}


# ── Main plan endpoint (Step 13) ──────────────────────────────────────

@app.post("/plan", tags=["plan"])
async def create_plan(request: PlanRequest):
    """
    Generate a complete stargazing expedition plan.

    Runs the full orchestration pipeline:
    Curator → Location Scout → Weather → Choreographer → Gear → Story

    Returns an ExpeditionPlan with ranked events, chosen site, weather
    forecast, time-ordered observation schedule, packing list, and
    narrative context for each object.
    """
    plan = await generate_plan(request)
    return plan.model_dump(mode="json")
