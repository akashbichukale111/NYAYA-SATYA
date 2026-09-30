"""
Database engine and session management.

SQLite is used for local/demo operation. The models use only
SQLAlchemy-portable constructs (no SQLite-only types) so the same
schema can be pointed at PostgreSQL by changing DATABASE_URL alone.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "registry_defect_engine.db"),
)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # Import models so they're registered on Base.metadata before create_all.
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def reset_db():
    """Drop and recreate all tables. Used by tests and demo seeding — never
    exposed via the API."""
    from app import models  # noqa: F401
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
