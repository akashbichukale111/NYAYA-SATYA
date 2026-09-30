import io
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))


def test_mock_provider_never_fabricates_text():
    from app.core.llm_provider import MockProvider

    provider = MockProvider()
    text = "The van arrived at 9am. The manager signed the log. No damage was found."
    candidates = provider.extract_evidence_candidates(text)
    assert len(candidates) >= 1
    for c in candidates:
        assert c["source_text"] in text


def test_get_llm_provider_defaults_to_mock(monkeypatch):
    from app.core.llm_provider import get_llm_provider, MockProvider
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    provider = get_llm_provider()
    assert isinstance(provider, MockProvider)


def test_contradiction_agent_flags_negation_mismatch(client):
    case = client.post("/api/cases", json={"title": "Contradiction case"}).json()
    claim = client.post(f"/api/cases/{case['id']}/claims", json={"text": "Payment was made on time."}).json()
    ev_a = client.post(f"/api/cases/{case['id']}/evidence", json={
        "label": "Ledger A", "source_text": "The payment was made on the due date."
    }).json()
    ev_b = client.post(f"/api/cases/{case['id']}/evidence", json={
        "label": "Ledger B", "source_text": "The payment was not made on the due date."
    }).json()
    for ev in (ev_a, ev_b):
        client.post(f"/api/cases/{case['id']}/relationships", json={
            "source_type": "EVIDENCE", "source_id": ev["id"],
            "target_type": "CLAIM", "target_id": claim["id"], "relationship_type": "SUPPORTS",
        })

    from app.core.db import SessionLocal
    from app.agents import contradiction_agent

    db = SessionLocal()
    result = contradiction_agent.detect_contradictions(db, case["id"])
    db.close()

    assert result["ok"] is True
    assert len(result["conflict_ids"]) >= 1

    coverage = client.get(f"/api/cases/{case['id']}/coverage").json()
    assert coverage["conflicting_claims"] >= 1


def test_relationship_agent_upgrades_second_independent_support_to_corroborates(client):
    case = client.post("/api/cases", json={"title": "Corroboration case"}).json()
    claim = client.post(f"/api/cases/{case['id']}/claims", json={"text": "Notice was served."}).json()

    doc_a = io.BytesIO(b"notice served doc A content")
    doc_b = io.BytesIO(b"notice served doc B content")
    d1 = client.post(f"/api/cases/{case['id']}/documents", files={"file": ("a.txt", doc_a, "text/plain")}).json()
    d2 = client.post(f"/api/cases/{case['id']}/documents", files={"file": ("b.txt", doc_b, "text/plain")}).json()

    ev1 = client.post(f"/api/cases/{case['id']}/evidence", json={
        "label": "A", "source_text": "x", "document_id": d1["id"]
    }).json()
    ev2 = client.post(f"/api/cases/{case['id']}/evidence", json={
        "label": "B", "source_text": "y", "document_id": d2["id"]
    }).json()

    client.post(f"/api/cases/{case['id']}/relationships", json={
        "source_type": "EVIDENCE", "source_id": ev1["id"],
        "target_type": "CLAIM", "target_id": claim["id"], "relationship_type": "SUPPORTS",
    })
    client.post(f"/api/cases/{case['id']}/relationships", json={
        "source_type": "EVIDENCE", "source_id": ev2["id"],
        "target_type": "CLAIM", "target_id": claim["id"], "relationship_type": "SUPPORTS",
    })

    from app.core.db import SessionLocal
    from app.agents import relationship_agent

    db = SessionLocal()
    result = relationship_agent.classify_support(db, case["id"])
    db.close()

    assert len(result["upgraded_relationship_ids"]) == 1
    rels = client.get(f"/api/cases/{case['id']}/relationships").json()
    types = sorted(r["relationship_type"] for r in rels)
    assert "CORROBORATES" in types


def test_issue_mapping_agent_proposes_not_creates(client):
    case = client.post("/api/cases", json={"title": "Issue mapping case"}).json()
    claim = client.post(f"/api/cases/{case['id']}/claims", json={"text": "The deadline was met."}).json()
    issue = client.post(f"/api/cases/{case['id']}/issues", json={"question": "Was the deadline met?"}).json()

    from app.core.db import SessionLocal
    from app.agents import issue_mapping_agent

    db = SessionLocal()
    result = issue_mapping_agent.propose_mappings(db, case["id"], [claim["id"]])
    db.close()

    assert len(result["review_task_ids"]) == 1

    # Not yet an active relationship -- only a pending proposal.
    rels = client.get(f"/api/cases/{case['id']}/relationships").json()
    assert rels == []

    queue = client.get(f"/api/cases/{case['id']}/review-queue").json()
    assert any(t["id"] == result["review_task_ids"][0] for t in queue)

    resp = client.post(f"/api/reviews/{result['review_task_ids'][0]}/approve", json={"note": "ok"})
    assert resp.status_code == 200

    rels_after = client.get(f"/api/cases/{case['id']}/relationships").json()
    assert len(rels_after) == 1
    assert rels_after[0]["source_id"] == claim["id"]
    assert rels_after[0]["target_id"] == issue["id"]


def test_verification_agent_skips_claims_with_no_evidence(client):
    case = client.post("/api/cases", json={"title": "Verification skip case"}).json()
    claim = client.post(f"/api/cases/{case['id']}/claims", json={"text": "Unsupported claim."}).json()

    from app.core.db import SessionLocal
    from app.agents import verification_agent

    db = SessionLocal()
    result = verification_agent.recommend_verifications(db, case["id"])
    db.close()

    assert result["review_task_ids"] == []
    claim_after = client.get(f"/api/claims/{claim['id']}").json()
    assert claim_after["verification_status"] != "VERIFIED"
