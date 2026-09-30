"""
Database configuration.

DEMO NOTE: SQLite is used for zero-config local/demo running. The schema is
written in plain SQLAlchemy so swapping DATABASE_URL to a Postgres DSN works
without code changes (see PrivacyPolicy / index notes in models.py).
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./legal_aid_handoff.db")

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
