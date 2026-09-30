import os
import sys
import tempfile

import pytest
from sqlmodel import Session, SQLModel, create_engine

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import models  # noqa: F401  (register tables on SQLModel.metadata)


@pytest.fixture()
def engine():
    """A fresh, isolated SQLite file per test — never touches the dev/demo db."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    eng = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(eng)
    yield eng
    os.remove(path)


@pytest.fixture()
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture()
def client(engine, monkeypatch):
    """A FastAPI TestClient wired to the isolated test engine instead of the
    module-level dev engine, so API tests never touch demo data."""
    from fastapi.testclient import TestClient
    from app import database
    monkeypatch.setattr(database, "engine", engine)

    def get_session_override():
        with Session(engine, expire_on_commit=False) as s:
            yield s

    from app.main import app
    app.dependency_overrides[database.get_session] = get_session_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
