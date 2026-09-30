from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from fastapi import Depends

from app.database import init_db, get_db
from app.api.routes import router as api_router
from app.demo.demo_cases import load_all_demo_cases, DEMO_DISCLAIMER
from app.models.domain import Case


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Case Crash Test & Resilience Lab",
    description="Break the case safely before reality breaks it. "
                 "Structural dependency simulation only — never a legal outcome predictor.",
    version="0.1.0-section1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "case-crash-test", "section": 1}


@app.post("/api/demo/load")
def load_demo(db: Session = Depends(get_db)):
    """
    Loads the 4 required deterministic demo cases (idempotent-ish: re-running
    creates a fresh set each time, since demo cases are meant to be disposable).
    """
    existing_demo_titles = {c.title for c in db.query(Case).filter(Case.is_demo == True).all()}  # noqa: E712
    if existing_demo_titles:
        cases = db.query(Case).filter(Case.is_demo == True).all()  # noqa: E712
        return {
            "disclaimer": DEMO_DISCLAIMER,
            "message": "Demo cases already loaded.",
            "cases": [{"id": c.id, "title": c.title} for c in cases],
        }
    cases = load_all_demo_cases(db)
    return {
        "disclaimer": DEMO_DISCLAIMER,
        "cases": [{"id": c.id, "title": c.title} for c in cases],
    }
