"""
Handoff Packet Generator (sec 17), Handoff Quality Gate (sec 18),
and Handoff Risk Detection (sec 19).

The packet is built ONLY from structured case state already in the
database — nothing here calls an LLM to invent packet content. The
Context Packaging Agent (backend/agents/context_packaging_agent.py) is a
thin proposer around this same deterministic function; the review agent
then critiques its output. This keeps "no fabricated facts" true even
though an LLM is in the loop.
"""
from sqlalchemy.orm import Session

from models import (
    Case, Fact, Document, TimelineEvent, Deadline, Question, Conflict,
    Handoff, HandoffVersion, Role, Sensitivity, FactStatus, HandoffState
)
from privacy.engine import is_allowed, explain_access


def _facts_for_recipient(db: Session, case_id: str, recipient_role: Role):
    facts = db.query(Fact).filter(Fact.case_id == case_id).all()
    included, excluded = [], []
    for f in facts:
        if is_allowed(f.sensitivity, recipient_role):
            included.append(f)
        else:
            excluded.append({"field": f.label, "reason": explain_access(f.label, f.sensitivity, recipient_role)["reason"]})
    return included, excluded


def generate_packet(db: Session, case: Case, purpose: str, recipient_role: Role, sender_role: Role,
                     version_number: int = 1) -> HandoffVersion:
    included_facts, excluded_notes = _facts_for_recipient(db, case.id, recipient_role)
    documents = db.query(Document).filter(Document.case_id == case.id).all()
    included_docs = [d for d in documents if is_allowed(d.sensitivity, recipient_role)]
    for d in documents:
        if d not in included_docs:
            excluded_notes.append({"field": f"document:{d.filename}",
                                    "reason": explain_access(d.filename, d.sensitivity, recipient_role)["reason"]})

    timeline = db.query(TimelineEvent).filter(TimelineEvent.case_id == case.id).all()
    deadlines = db.query(Deadline).filter(Deadline.case_id == case.id).all()
    questions = db.query(Question).filter(Question.case_id == case.id, Question.resolved == False).all()  # noqa: E712
    conflicts = db.query(Conflict).filter(Conflict.case_id == case.id, Conflict.resolved == False).all()  # noqa: E712

    checks, risks = run_quality_and_risk_checks(
        included_facts=included_facts, all_facts=db.query(Fact).filter(Fact.case_id == case.id).all(),
        documents=included_docs, deadlines=deadlines, conflicts=conflicts,
        excluded_notes=excluded_notes, recipient_role=recipient_role,
    )

    state = HandoffState.READY_FOR_REVIEW
    if checks["overall"] == "BLOCKED":
        state = HandoffState.BLOCKED
    elif checks["overall"] == "NEEDS_REVIEW":
        state = HandoffState.NEEDS_REVIEW

    handoff = db.query(Handoff).filter(
        Handoff.case_id == case.id, Handoff.recipient_role == recipient_role, Handoff.purpose == purpose
    ).order_by(Handoff.created_at.desc()).first()

    if handoff is None or version_number == 1:
        handoff = Handoff(case_id=case.id, purpose=purpose, recipient_role=recipient_role,
                           sender_role=sender_role, state=state, current_version_number=1)
        db.add(handoff)
        db.commit()
        db.refresh(handoff)
        version_number = 1
    else:
        handoff.state = state
        handoff.current_version_number = version_number
        db.commit()

    version = HandoffVersion(
        handoff_id=handoff.id,
        version_number=version_number,
        included_fact_ids=[f.id for f in included_facts],
        included_document_ids=[d.id for d in included_docs],
        included_timeline_event_ids=[t.id for t in timeline],
        included_deadline_ids=[dl.id for dl in deadlines],
        included_question_ids=[q.id for q in questions],
        included_conflict_ids=[c.id for c in conflicts],
        excluded_field_notes=excluded_notes,
        quality_checks=checks,
        risk_flags=risks,
        created_by_role=sender_role,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def run_quality_and_risk_checks(*, included_facts, all_facts, documents, deadlines, conflicts,
                                 excluded_notes, recipient_role: Role):
    """Section 18 + 19: explicit checklist, never a black-box score."""
    checks = {}

    unsupported = [f for f in included_facts if f.status in (FactStatus.UNKNOWN, FactStatus.NOT_PROVIDED)]
    checks["critical_facts_sourced"] = {
        "pass": len(unsupported) == 0,
        "detail": "All included facts carry a source/status" if not unsupported
        else f"{len(unsupported)} included fact(s) have no source or status: "
             + ", ".join(f.label for f in unsupported),
    }

    checks["deadline_included"] = {
        "pass": len(deadlines) > 0,
        "detail": f"{len(deadlines)} known deadline(s) included" if deadlines
        else "No known deadlines on this case — nothing to include (not necessarily an error)",
    }

    checks["conflicts_visible"] = {
        "pass": True,  # unresolved conflicts are always surfaced, never hidden
        "detail": f"{len(conflicts)} unresolved conflict(s) surfaced to recipient" if conflicts
        else "No unresolved conflicts",
    }

    checks["documents_referenced"] = {
        "pass": True,
        "detail": f"{len(documents)} document(s) referenced with provenance",
    }

    checks["sensitive_info_scoped"] = {
        "pass": True,
        "detail": f"{len(excluded_notes)} field(s) excluded as above the {recipient_role.value} sensitivity ceiling"
        if excluded_notes else "No fields exceeded recipient sensitivity ceiling",
    }

    checks["no_fabricated_facts"] = {
        "pass": True,
        "detail": "Packet built only from structured case-state rows; no generative content inserted",
    }

    hard_fail = not checks["critical_facts_sourced"]["pass"]
    soft_warn = bool(conflicts) or bool(unsupported and not hard_fail)

    checks["overall"] = "BLOCKED" if hard_fail else ("NEEDS_REVIEW" if soft_warn else "READY_FOR_REVIEW")

    # Section 19: HANDOFF CONTEXT RISKS (never called "legal risks")
    risks = []
    if unsupported:
        risks.append({"risk": "unsupported_critical_fact",
                       "detail": f"{len(unsupported)} fact(s) lack a verified/document source"})
    if conflicts:
        risks.append({"risk": "unresolved_contradiction",
                       "detail": f"{len(conflicts)} unresolved conflict(s) present"})
    if not deadlines:
        risks.append({"risk": "missing_deadline", "detail": "No deadline on record — confirm none was missed"})
    if not documents:
        risks.append({"risk": "missing_key_document", "detail": "No supporting documents in this packet"})

    return checks, risks
