import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# PostgreSQL-ready: swap DATABASE_URL to a postgres:// DSN and this still works,
# since we avoid SQLite-only features anywhere in the models/queries.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./case_crash_test.db")

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
    # Import models so they're registered on Base.metadata before create_all
    from app.models import domain, simulation  # noqa: F401
    Base.metadata.create_all(bind=engine)
