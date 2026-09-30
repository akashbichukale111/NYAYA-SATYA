from fastapi import FastAPI

from app.database import init_db
from app.api.routes import router

app = FastAPI(
    title="SPARK Deadline Guardian",
    description="Consequential Date Intelligence + Dependency + Verification system. "
                 "Section 1: Core Foundation.",
    version="0.1.0",
)


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(router, prefix="/api/v1")
