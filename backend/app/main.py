import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.data.loader import load_events, load_sites
from app.models import PlanRequest
from app.orchestrator import generate_plan
from app.services.plan_store import plan_store
from app.scheduler import start_scheduler, stop_scheduler

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


@app.on_event("startup")
async def start_background_services() -> None:
    if not getattr(start_scheduler, "_started", False):
        start_scheduler()
        setattr(start_scheduler, "_started", True)


@app.on_event("shutdown")
async def stop_background_services() -> None:
    if getattr(start_scheduler, "_started", False):
        stop_scheduler()
        setattr(start_scheduler, "_started", False)


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
    plan_store.save(plan)
    return plan.model_dump(mode="json")


@app.get("/plans/{plan_id}", tags=["plan"])
async def get_plan(plan_id: str):
    """Retrieve a persisted plan, including any contingency updates."""
    plan = plan_store.get(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan.model_dump(mode="json")


@app.post("/plans/{plan_id}/refresh", tags=["plan"])
async def refresh_plan(plan_id: str):
    """Regenerate a stored plan with current weather while preserving its ID."""
    existing = plan_store.get(plan_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    refreshed = await generate_plan(existing.request)
    refreshed.plan_id = plan_id
    refreshed.contingency_note = "Plan refreshed using the latest available conditions."
    plan_store.save(refreshed)
    return refreshed.model_dump(mode="json")
