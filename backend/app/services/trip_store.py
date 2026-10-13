"""Per-user trip persistence in Supabase Postgres (PostgREST).

Anonymous trips keep using the local SQLite PlanStore. Authenticated users'
trips live in the `trips` table (see db/migrations/001_trips.sql),
keyed by (user_id, plan_id). The service key bypasses RLS, so every query
is explicitly scoped to the verified user id from the request token.
"""

import logging
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.models import ExpeditionPlan

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(settings.supabase_url and settings.supabase_secret_key)


def _headers() -> dict[str, str]:
    return {
        "apikey": settings.supabase_secret_key,
        "Authorization": f"Bearer {settings.supabase_secret_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }


def _base() -> str:
    return f"{settings.supabase_url.rstrip('/')}/rest/v1/trips"


async def save_trip(user_id: str, plan: ExpeditionPlan) -> ExpeditionPlan:
    plan.updated_at = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "plan_id": plan.plan_id,
        "observation_end": plan.request.date_end.isoformat(),
        "updated_at": plan.updated_at.isoformat(),
        "payload": plan.model_dump(mode="json"),
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(f"{_base()}?on_conflict=plan_id", headers=_headers(), json=payload)
        response.raise_for_status()
    return plan


async def get_trip(user_id: str, plan_id: str) -> ExpeditionPlan | None:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            _base(),
            headers=_headers(),
            params={"user_id": f"eq.{user_id}", "plan_id": f"eq.{plan_id}", "select": "payload"},
        )
        response.raise_for_status()
    rows = response.json()
    if not rows:
        return None
    return ExpeditionPlan.model_validate(rows[0]["payload"])


async def delete_trip(user_id: str, plan_id: str) -> bool:
    if await get_trip(user_id, plan_id) is None:
        return False
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.delete(
            _base(),
            headers=_headers(),
            params={"user_id": f"eq.{user_id}", "plan_id": f"eq.{plan_id}"},
        )
        response.raise_for_status()
    return True


async def list_trips(user_id: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            _base(),
            headers=_headers(),
            params={
                "user_id": f"eq.{user_id}",
                "select": "plan_id,observation_end,updated_at,payload",
                "order": "updated_at.desc",
                "limit": "30",
            },
        )
        response.raise_for_status()
    summaries = []
    for row in response.json():
        payload = row.get("payload") or {}
        chosen = (payload.get("chosen_site") or {})
        summaries.append({
            "plan_id": row["plan_id"],
            "observation_end": row.get("observation_end"),
            "updated_at": row.get("updated_at"),
            "site_name": chosen.get("name"),
            "date_start": (payload.get("request") or {}).get("date_start"),
        })
    return summaries
