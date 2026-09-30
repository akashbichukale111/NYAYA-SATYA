import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DATABASE_URL"] = "sqlite:///./test_case_crash_test.db"

from app.database import Base, engine, SessionLocal, init_db  # noqa: E402


@pytest.fixture(scope="function", autouse=True)
def _fresh_db():
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
