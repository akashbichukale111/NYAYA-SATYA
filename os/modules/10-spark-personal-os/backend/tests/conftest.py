import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DATABASE_URL"] = "sqlite:///./test_spark.db"

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def _clean_db():
    if os.path.exists("test_spark.db"):
        os.remove("test_spark.db")
    yield
    if os.path.exists("test_spark.db"):
        os.remove("test_spark.db")


@pytest.fixture()
def client():
    from app.main import app
    return TestClient(app)


@pytest.fixture()
def registered_user(client):
    email = f"test.advocate.{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post("/api/auth/register", json={
        "email": email,
        "password": "TestPass123!",
        "full_name": "Test Advocate",
        "role": "advocate",
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    body["_email"] = email
    return body


@pytest.fixture()
def auth_headers(client, registered_user):
    resp = client.post("/api/auth/login", json={
        "email": registered_user["_email"],
        "password": "TestPass123!",
    })
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
