import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_PATH = os.environ.get("SPARK_DB_PATH", "spark_workflow_autopilot.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# check_same_thread=False is required for SQLite when used from FastAPI's
# threaded request handling; the engine itself remains a single file on disk,
# so workflow state genuinely survives process restarts.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app.models import models  # noqa: F401  (register models on Base)
    Base.metadata.create_all(bind=engine)
