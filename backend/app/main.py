import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

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
