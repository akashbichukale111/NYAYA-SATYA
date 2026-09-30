import os
import sys
import tempfile

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, os.path.abspath(BACKEND_DIR))


@pytest.fixture()
def client():
    # Fresh isolated sqlite file per test so tests never leak state.
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["DATABASE_URL"] = f"sqlite:///{path}"

    # Ensure a clean import of app modules bound to this DB url.
    for mod in list(sys.modules):
        if mod == "app" or mod.startswith("app."):
            del sys.modules[mod]

    from app.main import app
    from app.core.db import init_db
    init_db()

    with TestClient(app) as c:
        yield c

    os.remove(path)
