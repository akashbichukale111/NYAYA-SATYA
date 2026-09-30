import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

import app.models.db  # noqa: F401  ensure models are registered on Base (import first)
from app.database import Base, get_db
from app.main import app  # must be imported last so the name `app` binds to the FastAPI instance


@pytest.fixture()
def client():
    # In-memory sqlite shared across connections for the life of one test,
    # isolated from the real dev database and from other tests.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_ingest_creates_source_and_deadlines(client):
    resp = client.post(
        "/api/v1/ingest/text",
        json={
            "label": "Test Notice",
            "text": "The reply must be filed within 30 days of service. "
                    "The hearing is on 12 March 2026.",
            "source_type": "NOTICE",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["label"] == "Test Notice"
    assert len(body["date_candidates"]) == 2

    deadlines = client.get("/api/v1/deadlines").json()
    assert len(deadlines) == 2
    assert all(d["status"] == "PENDING_REVIEW" for d in deadlines)


def test_ingest_rejects_empty_text(client):
    resp = client.post(
        "/api/v1/ingest/text",
        json={"label": "Empty", "text": "   ", "source_type": "MANUAL_ENTRY"},
    )
    assert resp.status_code == 422


def test_review_flow_requires_human_identity(client):
    client.post(
        "/api/v1/ingest/text",
        json={
            "label": "Order",
            "text": "Compliance due by 2026-05-01.",
            "source_type": "COURT_ORDER",
        },
    )
    deadlines = client.get("/api/v1/deadlines").json()
    target = deadlines[0]

    resp = client.post(
        f"/api/v1/deadlines/{target['id']}/review",
        json={"reviewer": "akash", "approve": True},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "VERIFIED"
    assert resp.json()["reviewed_by"] == "akash"


def test_dedup_on_identical_text(client):
    payload = {"label": "Dup", "text": "Filing due 2026-06-01.", "source_type": "FILING"}
    first = client.post("/api/v1/ingest/text", json=payload).json()
    second = client.post("/api/v1/ingest/text", json=payload).json()
    assert first["id"] == second["id"]
