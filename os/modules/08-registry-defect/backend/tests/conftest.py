"""Shared pytest fixtures.

Each test gets a fresh in-memory SQLite database and a FastAPI TestClient
wired to it, so tests never share state and never touch the real
registry_defect_engine.db file.
"""
import os
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["STORAGE_ROOT"] = tempfile.mkdtemp(prefix="rde_test_storage_")


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    test_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    from app.core import database as db_module
    monkeypatch.setattr(db_module, "engine", test_engine)
    monkeypatch.setattr(db_module, "SessionLocal", TestSessionLocal)

    from app import models  # noqa: F401
    db_module.Base.metadata.create_all(bind=test_engine)

    session = TestSessionLocal()
    yield session
    session.close()


@pytest.fixture()
def client(db_session, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db_session):
    from app import models
    from app.core.ids import new_id, utcnow

    def _make(role="ADVOCATE", email=None):
        user = models.User(
            id=new_id("user"), name=f"Test {role}", email=email or f"{new_id('u')}@example.invalid",
            role=role, hashed_password="not-a-real-hash", created_at=utcnow().isoformat(), is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    return _make
