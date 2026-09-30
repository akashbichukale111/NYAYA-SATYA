"""
Deterministic offline demo data.

Three fictional demo cases as specified: strong evidence chain (A),
fragile single-point dependency (B), and conflict + supersession (C).
No real names, no real case data. Every seeded case is flagged
is_demo=True so the UI can render "DEMONSTRATION DATA -- NOT A REAL CASE".
"""
from sqlalchemy.orm import Session

from app.models.orm import Case, Document, EvidenceItem, Claim, Issue, EvidenceRelationship
from app.services.review_service import log_audit_event
from app.services.time_machine_service import snapshot_evidence, snapshot_claim


def _mk_doc(db, case_id, filename, doc_hash):
    doc = Document(
        case_id=case_id, filename=filename, mime_type="application/pdf",
        sha256_hash=doc_hash, document_type="PDF", extraction_method="DEMO_SEED",
        status="INGESTED",
    )
    db.add(doc)
    db.flush()
    return doc


def _mk_evidence(db, case_id, document_id, label, text, page=None, section=None, verification="VERIFIED", state="SUPPORTED"):
    ev = EvidenceItem(
        case_id=case_id, document_id=document_id, label=label, source_text=text,
        page_number=page, section=section,
        source_location_known=page is not None or section is not None,
        extraction_method="DEMO_SEED", verification_status=verification, state=state,
    )
    db.add(ev)
    db.flush()
    snapshot_evidence(db, ev, reason="DEMO_SEEDED")
    return ev


def _mk_claim(db, case_id, text, verification="UNVERIFIED"):
    c = Claim(case_id=case_id, text=text, source="EXTRACTED", verification_status=verification)
    db.add(c)
    db.flush()
    snapshot_claim(db, c, reason="DEMO_SEEDED")
    return c


def _mk_issue(db, case_id, question, description=""):
    i = Issue(case_id=case_id, question=question, description=description)
    db.add(i)
    db.flush()
    return i


def _rel(db, case_id, s_type, s_id, t_type, t_id, rel_type, support_kind=None, explanation=""):
    r = EvidenceRelationship(
        case_id=case_id, source_type=s_type, source_id=s_id, target_type=t_type, target_id=t_id,
        relationship_type=rel_type, support_kind=support_kind, explanation=explanation,
        verification_status="VERIFIED",
    )
    db.add(r)
    db.flush()
    return r


def seed_case_a_strong_chain(db: Session) -> Case:
    """Demo Case A -- Strong Evidence Chain: multiple independent documents
    support several claims, which together support one issue."""
    case = Case(title="Demo A -- Strong Evidence Chain", description="DEMONSTRATION DATA — NOT A REAL CASE. "
                "Fictional dispute over a delivery of goods; several independent documents support the claims.",
                is_demo=True)
    db.add(case)
    db.flush()

    doc1 = _mk_doc(db, case.id, "demo_delivery_receipt.pdf", "demo-hash-a1")
    doc2 = _mk_doc(db, case.id, "demo_courier_log.pdf", "demo-hash-a2")
    doc3 = _mk_doc(db, case.id, "demo_witness_statement.pdf", "demo-hash-a3")

    e1 = _mk_evidence(db, case.id, doc1.id, "Signed delivery receipt", "Receipt signed 'A. Fictional' dated 12 March.", page=1, section="Signature block")
    e2 = _mk_evidence(db, case.id, doc2.id, "Courier GPS log entry", "GPS log shows stop at delivery address on 12 March, 14:02.", page=3, section="Log entries")
    e3 = _mk_evidence(db, case.id, doc3.id, "Witness statement", "Neighbour states they saw the delivery van on 12 March.", page=1, section="Statement")

    claim1 = _mk_claim(db, case.id, "The goods were delivered to the respondent on 12 March.", verification="VERIFIED")
    issue1 = _mk_issue(db, case.id, "Was delivery of the goods completed?", "Fictional demo issue.")

    _rel(db, case.id, "EVIDENCE", e1.id, "CLAIM", claim1.id, "SUPPORTS", "DIRECT_SUPPORT")
    _rel(db, case.id, "EVIDENCE", e2.id, "CLAIM", claim1.id, "CORROBORATES", "CORROBORATIVE_SUPPORT")
    _rel(db, case.id, "EVIDENCE", e3.id, "CLAIM", claim1.id, "CORROBORATES", "CORROBORATIVE_SUPPORT")
    _rel(db, case.id, "CLAIM", claim1.id, "ISSUE", issue1.id, "REQUIRES")

    log_audit_event(db, case.id, actor="SYSTEM", action="DEMO_SEEDED", target_type="CASE", target_id=case.id)
    db.commit()
    db.refresh(case)
    return case


def seed_case_b_fragile(db: Session) -> Case:
    """Demo Case B -- Fragile Dependency: ONE evidence item is the sole
    support for multiple critical claims. Crash-testing it reveals impact."""
    case = Case(title="Demo B -- Fragile Dependency", description="DEMONSTRATION DATA — NOT A REAL CASE. "
                "Fictional dispute where a single document underpins several claims and issues.",
                is_demo=True)
    db.add(case)
    db.flush()

    doc1 = _mk_doc(db, case.id, "demo_master_ledger.pdf", "demo-hash-b1")
    e1 = _mk_evidence(db, case.id, doc1.id, "Master ledger page 7", "Ledger entry recording payment and notice acknowledgement.", page=7, section="Entry 44", verification="UNVERIFIED", state="USER_REPORTED")

    claim1 = _mk_claim(db, case.id, "Payment of a fictional sum was made on 1 April.")
    claim2 = _mk_claim(db, case.id, "Notice was acknowledged by the respondent.")
    issue1 = _mk_issue(db, case.id, "Was payment made?")
    issue2 = _mk_issue(db, case.id, "Was notice served and acknowledged?")

    _rel(db, case.id, "EVIDENCE", e1.id, "CLAIM", claim1.id, "SUPPORTS", "DIRECT_SUPPORT")
    _rel(db, case.id, "EVIDENCE", e1.id, "CLAIM", claim2.id, "SUPPORTS", "DIRECT_SUPPORT")
    _rel(db, case.id, "CLAIM", claim1.id, "ISSUE", issue1.id, "REQUIRES")
    _rel(db, case.id, "CLAIM", claim2.id, "ISSUE", issue2.id, "REQUIRES")

    log_audit_event(db, case.id, actor="SYSTEM", action="DEMO_SEEDED", target_type="CASE", target_id=case.id)
    db.commit()
    db.refresh(case)
    return case


def seed_case_c_conflict(db: Session) -> Case:
    """Demo Case C -- Conflict + Supersession: two documents conflict and a
    later document supersedes an earlier source."""
    case = Case(title="Demo C -- Conflict and Supersession", description="DEMONSTRATION DATA — NOT A REAL CASE. "
                "Fictional dispute with two conflicting statements and a later superseding order.",
                is_demo=True)
    db.add(case)
    db.flush()

    doc1 = _mk_doc(db, case.id, "demo_original_order.pdf", "demo-hash-c1")
    doc2 = _mk_doc(db, case.id, "demo_amended_order.pdf", "demo-hash-c2")
    doc3 = _mk_doc(db, case.id, "demo_conflicting_affidavit.pdf", "demo-hash-c3")

    e1 = _mk_evidence(db, case.id, doc1.id, "Original order", "Original order states deadline of 30 days.", page=2, section="Clause 4")
    e2 = _mk_evidence(db, case.id, doc2.id, "Amended order", "Amended order revises the deadline to 45 days.", page=1, section="Clause 2", state="SUPPORTED")
    e3 = _mk_evidence(db, case.id, doc3.id, "Conflicting affidavit", "Affidavit claims no amendment was ever served.", page=1, section="Para 6", verification="UNVERIFIED", state="CONFLICTING")

    claim1 = _mk_claim(db, case.id, "The compliance deadline was validly extended to 45 days.")
    issue1 = _mk_issue(db, case.id, "Was the deadline validly extended?")

    _rel(db, case.id, "EVIDENCE", e2.id, "CLAIM", claim1.id, "SUPPORTS", "DIRECT_SUPPORT")
    _rel(db, case.id, "EVIDENCE", e2.id, "EVIDENCE", e1.id, "SUPERSEDES", explanation="Amended order supersedes original order clause 4.")
    _rel(db, case.id, "EVIDENCE", e3.id, "CLAIM", claim1.id, "CONTRADICTS", explanation="Affidavit disputes service of the amendment.")
    _rel(db, case.id, "CLAIM", claim1.id, "ISSUE", issue1.id, "REQUIRES")

    log_audit_event(db, case.id, actor="SYSTEM", action="DEMO_SEEDED", target_type="CASE", target_id=case.id)
    db.commit()
    db.refresh(case)
    return case


DEMO_CASE_SEEDS = {
    "A": seed_case_a_strong_chain,
    "B": seed_case_b_fragile,
    "C": seed_case_c_conflict,
}


def seed_demo_case(db: Session, key: str) -> Case:
    return DEMO_CASE_SEEDS[key](db)
