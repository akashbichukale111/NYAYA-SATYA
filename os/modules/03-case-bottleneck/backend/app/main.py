from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import cases, bottlenecks, actions, simulation_router

app = FastAPI(
    title="Case Bottleneck Engine",
    description="Find what is actually stopping a case from moving forward.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo scope — tighten before any real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cases.router)
app.include_router(bottlenecks.router)
app.include_router(actions.router)
app.include_router(simulation_router.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "case-bottleneck-engine"}
