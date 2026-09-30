from __future__ import annotations

from fastapi import APIRouter
from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "demo_mode": settings.DEMO_MODE,
        "env": settings.ENV,
    }
