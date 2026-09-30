from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.db.session import init_db
from app.core.config import settings
from app.api import cases, twin, governance_routes, analysis, manual_events


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Undertrial Liberty Sentinel API",
    description="Procedural liberty-event visibility, source traceability, and human-review workflow. "
                "Not a legal advice, bail-decision, or judicial-prediction system.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local/demo; restrict in production deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def consistent_http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "code": exc.status_code, "path": str(request.url.path)},
    )


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "demo_mode": settings.DEMO_MODE, "llm_provider": settings.LLM_PROVIDER}


app.include_router(cases.router)
app.include_router(twin.router)
app.include_router(governance_routes.router)
app.include_router(analysis.router)
app.include_router(manual_events.router)
