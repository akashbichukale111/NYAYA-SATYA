"""
Registry Defect Engine — FastAPI application entrypoint.

Run with:
    uvicorn app.main:app --reload --port 8000

On startup, tables are created if missing (init_db). Demo data is NOT
seeded automatically — call scripts/seed_demo.py explicitly, or POST
/api/demo/seed (guarded, see routers/demo.py) so a fresh production
deployment never silently contains synthetic cases.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import init_db
from app.core.security import AccessDenied
from app.routers import cases, documents, requirements, defects, review, demo, integration, users, analysis, evaluation

app = FastAPI(
    title="Registry Defect Engine",
    description="Find the filing defect before it becomes the case bottleneck.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.exception_handler(AccessDenied)
def handle_access_denied(request: Request, exc: AccessDenied):
    return JSONResponse(status_code=403, content={"error": "ACCESS_DENIED", "detail": exc.detail})


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception):
    # Consistent API error shape; never leaks stack traces to the client.
    return JSONResponse(status_code=500, content={"error": "INTERNAL_ERROR", "detail": str(exc)})


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "registry-defect-engine"}


app.include_router(cases.router)
app.include_router(documents.router)
app.include_router(requirements.router)
app.include_router(defects.router)
app.include_router(review.router)
app.include_router(demo.router)
app.include_router(integration.router)
app.include_router(users.router)
app.include_router(analysis.router)
app.include_router(evaluation.router)
