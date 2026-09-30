"""
Database engine/session setup.

SQLite is used for demo/local development. The models use only
standard SQLAlchemy types and patterns so migrating to PostgreSQL
later requires no schema rewrite (see docs/architecture.md).
"""
import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "sqlite:///./evidence_dependency_engine.db"
)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    # Import models so they register on Base.metadata before create_all.
    from app.models import orm  # noqa: F401
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
