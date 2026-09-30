import os
import sys
import tempfile
import shutil
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import Base  # noqa: E402
# Import all models once so they register on Base.metadata.
from app.models import (  # noqa: E402,F401
    case, document, evidence, hearing, requirement, blocker,
    dependency, action, approval, verification, version,
    audit, simulation, crash_test, agent_run,
)


@pytest.fixture()
def db_session():
    """Fresh, isolated SQLite file per test -- no shared state, no order
    dependence, and no reliance on the app's global engine/session."""
    tmp_dir = tempfile.mkdtemp(prefix="hre_test_")
    db_path = os.path.join(tmp_dir, "test.db")
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        shutil.rmtree(tmp_dir, ignore_errors=True)
