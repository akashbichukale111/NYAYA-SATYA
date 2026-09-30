import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# isolated sqlite file per test session, before importing database/main
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db.name}"

import pytest
from fastapi.testclient import TestClient
from database import Base, engine
import main as main_module


@pytest.fixture(scope="function", autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    return TestClient(main_module.app)
