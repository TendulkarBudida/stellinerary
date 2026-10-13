import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.data.loader import load_events, load_sites
from app.models import PlanRequest
from app.orchestrator import generate_plan
from app.services.auth import get_optional_user_id
from app.services.plan_store import plan_store
from app.services import trip_store
from app.scheduler import start_scheduler, stop_scheduler
from fastapi import Depends

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

async def _save_plan(plan, user_id: str | None):
    """Persist a plan: per-user Supabase row when logged in, else local SQLite."""
    if user_id and trip_store.is_configured():
        try:
            await trip_store.save_trip(user_id, plan)
            return
        except Exception as e:
            logger.warning("Supabase trip save failed, falling back to local store: %s", e)
    plan_store.save(plan)


async def _load_plan(plan_id: str, user_id: str | None):
    """Load a plan the caller may see: own Supabase row first, then local store."""
    if user_id and trip_store.is_configured():
        try:
            owned = await trip_store.get_trip(user_id, plan_id)
            if owned is not None:
                return owned, "supabase"
        except Exception as e:
            logger.warning("Supabase trip lookup failed, trying local store: %s", e)
    stored = plan_store.get(plan_id)
    return (stored, "local") if stored is not None else (None, "local")


@app.post("/plan", tags=["plan"])
async def create_plan(request: PlanRequest, user_id: str | None = Depends(get_optional_user_id)):
    """
    Generate a complete stargazing expedition plan.

    Runs the full orchestration pipeline:
    Curator → Location Scout → Weather → Choreographer → Gear → Story

    Returns an ExpeditionPlan with ranked events, chosen site, weather
    forecast, time-ordered observation schedule, packing list, and
    narrative context for each object.

    Logged-in users' plans are stored under their account; anonymous
    plans use the local store.
    """
    plan = await generate_plan(request)
    await _save_plan(plan, user_id)
    return plan.model_dump(mode="json")


@app.get("/plans", tags=["plan"])
async def list_plans(user_id: str | None = Depends(get_optional_user_id)):
    """List upcoming persisted plans (newest update first)."""
    if user_id and trip_store.is_configured():
        try:
            return await trip_store.list_trips(user_id)
        except Exception as e:
            logger.warning("Supabase trip list failed, falling back to local store: %s", e)
    plans = plan_store.active()
    summaries = [
        {
            "plan_id": plan.plan_id,
            "observation_end": plan.request.date_end.isoformat(),
            "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
            "site_name": plan.chosen_site.name if plan.chosen_site else None,
            "date_start": plan.request.date_start.isoformat(),
        }
        for plan in plans
    ]
    summaries.sort(key=lambda s: s["updated_at"] or "", reverse=True)
    return summaries


@app.get("/plans/{plan_id}", tags=["plan"])
async def get_plan(plan_id: str, user_id: str | None = Depends(get_optional_user_id)):
    """Retrieve a persisted plan, including any contingency updates."""
    plan, _ = await _load_plan(plan_id, user_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan.model_dump(mode="json")


@app.delete("/plans/{plan_id}", tags=["plan"])
async def delete_plan(plan_id: str, user_id: str | None = Depends(get_optional_user_id)):
    """Delete a persisted plan. Logged-in users delete their own row; anonymous deletes local."""
    if user_id and trip_store.is_configured():
        try:
            if await trip_store.delete_trip(user_id, plan_id):
                return {"deleted": plan_id}
            raise HTTPException(status_code=404, detail="Plan not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Supabase trip delete failed, trying local store: %s", e)
    if plan_store.delete(plan_id):
        return {"deleted": plan_id}
    raise HTTPException(status_code=404, detail="Plan not found")


@app.post("/plans/{plan_id}/refresh", tags=["plan"])
async def refresh_plan(plan_id: str, user_id: str | None = Depends(get_optional_user_id)):
    """Regenerate a stored plan with current weather while preserving its ID."""
    existing, _ = await _load_plan(plan_id, user_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    refreshed = await generate_plan(existing.request)
    refreshed.plan_id = plan_id
    refreshed.contingency_note = "Plan refreshed using the latest available conditions."
    await _save_plan(refreshed, user_id)
    return refreshed.model_dump(mode="json")
