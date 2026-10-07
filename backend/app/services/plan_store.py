"""Durable SQLite storage for generated trip plans."""

import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.models import ExpeditionPlan


def _default_path() -> Path:
    configured = settings.plan_store_path.strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / "data" / "stellinerary-plans.db"


class PlanStore:
    def __init__(self, path: Path | None = None):
        self.path = path or _default_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS plans (
                    plan_id TEXT PRIMARY KEY,
                    observation_end TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
            """)

    def save(self, plan: ExpeditionPlan) -> ExpeditionPlan:
        plan.plan_id = plan.plan_id or str(uuid4())
        plan.updated_at = datetime.now(timezone.utc)
        payload = plan.model_dump_json()
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO plans (plan_id, observation_end, updated_at, payload)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(plan_id) DO UPDATE SET
                     observation_end=excluded.observation_end,
                     updated_at=excluded.updated_at,
                     payload=excluded.payload""",
                (plan.plan_id, plan.request.date_end.isoformat(), plan.updated_at.isoformat(), payload),
            )
        return plan

    def get(self, plan_id: str) -> ExpeditionPlan | None:
        with self._connection() as connection:
            row = connection.execute("SELECT payload FROM plans WHERE plan_id = ?", (plan_id,)).fetchone()
        return ExpeditionPlan.model_validate_json(row["payload"]) if row else None

    def active(self, today: date | None = None) -> list[ExpeditionPlan]:
        today = today or date.today()
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT payload FROM plans WHERE observation_end >= ?", (today.isoformat(),)
            ).fetchall()
        return [ExpeditionPlan.model_validate_json(row["payload"]) for row in rows]


plan_store = PlanStore()
