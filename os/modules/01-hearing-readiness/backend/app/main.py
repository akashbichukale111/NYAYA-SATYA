from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db, session_scope
from app.api import (
    routes_health, routes_cases, routes_documents, routes_readiness,
    routes_blockers, routes_ops, routes_eval,
)

app = FastAPI(
    title=settings.APP_NAME,
    description="Agentic pre-hearing readiness, blocker-traceability, and "
                "verified-action workflow system. Never predicts judicial "
                "outcomes; readiness/blocker/evidence assistance only.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    from app.data.synthetic_cases import seed_all
    init_db()
    # DEMO MODE: auto-seed Cases A-G on first boot so the product is usable
    # immediately with zero setup steps. Idempotent -- no-op on later boots
    # once synthetic cases already exist (see seed_all()).
    with session_scope() as db:
        seed_all(db)


app.include_router(routes_health.router)
app.include_router(routes_cases.router)
app.include_router(routes_documents.router)
app.include_router(routes_readiness.router)
app.include_router(routes_blockers.router)
app.include_router(routes_ops.router)
app.include_router(routes_eval.router)


@app.post("/api/demo/seed")
def seed_demo_data():
    """Manual re-seed hook -- normally a no-op since startup already seeds,
    but useful after wiping var/hre.db during development."""
    from app.data.synthetic_cases import seed_all
    with session_scope() as db:
        case_ids = seed_all(db)
    return {"seeded_case_ids": case_ids, "message": "Idempotent: no-op if synthetic cases already exist."}


@app.get("/")
def root():
    return {
        "product": settings.APP_NAME,
        "tagline": "Don't waste a hearing date because nobody knew what was missing.",
        "demo_mode": settings.DEMO_MODE,
        "docs": "/docs",
    }
