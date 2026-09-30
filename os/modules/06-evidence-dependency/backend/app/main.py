from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.db import init_db
from app.api import (
    cases, evidence, claims, issues, relationships, graph, impact, crash_test,
    reviews, audit, evaluation, integration, documents, time_machine,
)

app = FastAPI(
    title="Evidence Dependency Engine",
    description="Evidence -> Claim -> Issue dependency and impact analysis system. "
                 "Not a judge, lawyer, or outcome predictor.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "evidence-dependency-engine"}


app.include_router(cases.router, prefix="/api/cases", tags=["cases"])
app.include_router(evidence.router, prefix="/api", tags=["evidence"])
app.include_router(claims.router, prefix="/api", tags=["claims"])
app.include_router(issues.router, prefix="/api", tags=["issues"])
app.include_router(relationships.router, prefix="/api", tags=["relationships"])
app.include_router(graph.router, prefix="/api", tags=["graph"])
app.include_router(impact.router, prefix="/api", tags=["impact"])
app.include_router(crash_test.router, prefix="/api", tags=["crash-test"])
app.include_router(reviews.router, prefix="/api", tags=["reviews"])
app.include_router(audit.router, prefix="/api", tags=["audit"])
app.include_router(evaluation.router, prefix="/api", tags=["evaluation"])
app.include_router(integration.router, prefix="/api", tags=["integration"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(time_machine.router, prefix="/api", tags=["time-machine"])
