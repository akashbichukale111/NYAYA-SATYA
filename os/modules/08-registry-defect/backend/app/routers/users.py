"""
Minimal user bootstrap endpoint.

This is intentionally simple: there is no password-based login flow in
this build. A "session" is just possessing a user id, sent as the
X-User-Id header (see app/core/security.py). This endpoint lets the
frontend create a real User row for a chosen role so testers can
exercise RBAC without needing a full auth provider wired up. It does
not claim to be production authentication — see docs/security.md.
"""
import bcrypt
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.core.ids import new_id, utcnow
from app.core.enums import UserRole
from app import models

router = APIRouter(tags=["users"])


class UserCreate(BaseModel):
    name: str
    email: str
    role: str = UserRole.CITIZEN.value


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True


@router.post("/api/users", response_model=UserOut)
def create_or_get_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        return existing

    role = payload.role if payload.role in [r.value for r in UserRole] else UserRole.CITIZEN.value
    user = models.User(
        id=new_id("user"), name=payload.name, email=payload.email, role=role,
        hashed_password=bcrypt.hashpw(b"dev-mode-no-real-auth", bcrypt.gensalt()).decode("utf-8"),
        created_at=utcnow().isoformat(), is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
