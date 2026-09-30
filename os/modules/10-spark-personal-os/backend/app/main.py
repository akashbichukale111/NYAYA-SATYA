from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import Base, engine
from app.models import models  # noqa: F401  (registers tables on Base.metadata)
from app.api import auth, cases, attention, tasks, deadlines, reviews, approvals, misc

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Spark Personal OS — the human-facing operational workspace. "
        "It is not a legal reasoning authority, not a judge, and does not "
        "make legal decisions. It surfaces and organizes attention, tasks, "
        "deadlines, reviews, and approvals sourced from upstream engines, "
        "preserving provenance for every item."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(attention.router)
app.include_router(tasks.router)
app.include_router(deadlines.router)
app.include_router(reviews.router)
app.include_router(approvals.router)
app.include_router(misc.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "demo_mode": settings.DEMO_MODE, "app": settings.APP_NAME}
