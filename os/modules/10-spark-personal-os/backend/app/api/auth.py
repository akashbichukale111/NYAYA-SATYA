from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import User, UserProfile, NotificationPreference
from app.schemas.schemas import UserRegister, UserLogin, Token, UserOut
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.services.audit import log_audit

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    db.flush()
    db.add(UserProfile(user_id=user.id))
    db.add(NotificationPreference(user_id=user.id))
    db.commit()
    db.refresh(user)
    log_audit(db, actor_user_id=user.id, action="user.register", target_type="User", target_id=user.id)
    return user


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
    token = create_access_token(subject=user.id)
    log_audit(db, actor_user_id=user.id, action="user.login", target_type="User", target_id=user.id)
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
