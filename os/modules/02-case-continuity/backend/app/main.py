import logging

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.config import settings
from app.database import init_db, get_db
from app.demo_data import seed_demo_cases
from app.llm_provider import get_provider

from app.routers import (
    cases, ingestion, events, state, diff, timeline, graph, changes,
    conflicts, approvals, handoff, simulate, audit, health, evaluation,
)

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("case_continuity_engine")

app = FastAPI(
    title="Case Continuity Engine",
    description="Never lose the state of a case. An agentic case-state continuity system.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (cases, ingestion, events, state, diff, timeline, graph, changes,
               conflicts, approvals, handoff, simulate, audit, health, evaluation):
    app.include_router(router.router)


@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("Database initialized. LLM provider: %s", get_provider().name)


@app.get("/api/healthz")
def healthz():
    return {"status": "ok", "llm_provider": get_provider().name, "app_env": settings.app_env}


@app.post("/api/demo/seed")
def seed_demo(db: Session = Depends(get_db)):
    created = seed_demo_cases(db)
    return {"created_case_ids": created, "note": "Idempotent - already-seeded demo cases are left untouched."}


# Serve the static frontend (vanilla HTML/JS/CSS) if present, so the whole
# product can run as a single process in DEMO MODE.
try:
    app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
except RuntimeError:
    logger.warning("Frontend directory not found; API-only mode.")
