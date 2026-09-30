"""
Agent Orchestrator (section 26).

Implements:
  OBSERVE -> EXTRACT -> COMPARE -> INVESTIGATE -> PROPOSE CHANGE -> VERIFY
  -> HUMAN REVIEW IF REQUIRED -> COMMIT NEW STATE VERSION
  -> UPDATE CONTINUITY GRAPH -> AUDIT

Never: "LLM -> direct database overwrite". Every path here either produces
a ChangeProposal awaiting human review, or - only for high-confidence,
unambiguous, non-conflicting NEW facts - commits automatically, and even
then only after the Verification Agent passes it, with a full audit trail
either way.

The Continuity Graph (app/graph.py) is not a separate persisted structure
that needs "updating" - it is derived live from the same tables this
orchestrator writes to, so it is automatically current after any commit.
"""
from sqlalchemy.orm import Session

from app.models import Document, ChangeProposal, Event, EventType
from app.agents.base import new_correlation_id
from app.agents.intake_agent import intake_document
from app.agents.event_extraction_agent import extract_events_from_document
from app.agents.change_detection_agent import detect_changes
from app.agents.contradiction_agent import check_for_contradictions
from app.agents.verification_agent import verify_proposal
from app.agents.reconciliation_agent import commit_proposal
from app.audit import log_audit


AUTO_COMMIT_CONFIDENCE_THRESHOLD = 0.75


def ingest_and_process(
    db: Session, *, case_id: str, filename: str, content: bytes, doc_type_hint: str = "",
    actor: str = "user", is_demo_data: bool = False,
) -> dict:
    """Full pipeline for one uploaded artifact. Returns a summary the API can return."""
    correlation_id = new_correlation_id()
    log_audit(db, case_id=case_id, actor=actor, event_type="ingestion", correlation_id=correlation_id,
               source=filename, result="started")

    # OBSERVE + validate/store
    document, upload_event = intake_document(
        db, case_id=case_id, filename=filename, content=content, doc_type_hint=doc_type_hint,
        correlation_id=correlation_id, actor=actor, is_demo_data=is_demo_data,
    )

    if document.prompt_injection_flagged:
        log_audit(db, case_id=case_id, actor="IntakeAgent", event_type="system_error",
                   correlation_id=correlation_id, source=document.id, result="flagged",
                   detail={"reason": "possible prompt-injection content detected; forcing human review on "
                                     "all derived proposals"})

    # EXTRACT
    extraction_event = extract_events_from_document(
        db, case_id=case_id, document=document, correlation_id=correlation_id,
    )

    # COMPARE + INVESTIGATE + PROPOSE CHANGE
    proposals = detect_changes(db, case_id=case_id, extraction_event=extraction_event, correlation_id=correlation_id)

    if document.prompt_injection_flagged:
        for p in proposals:
            p.requires_human_review = True
        db.commit()

    # look for contradictions across pending proposals
    conflicts = []
    for p in proposals:
        c = check_for_contradictions(db, case_id=case_id, new_proposal=p, correlation_id=correlation_id)
        if c:
            conflicts.append(c)

    committed_versions = []
    for p in proposals:
        db.refresh(p)
        if p.requires_human_review:
            continue  # stays PENDING - Human Review Gate (section 27)
        # VERIFY
        verification = verify_proposal(db, proposal=p, correlation_id=correlation_id)
        if verification.result != "passed":
            p.requires_human_review = True
            db.commit()
            log_audit(db, case_id=case_id, actor="VerificationAgent", event_type="verification",
                       correlation_id=correlation_id, source=p.id, result="failed",
                       detail={"failure_reasons": verification.failure_reasons})
            continue
        # COMMIT NEW STATE VERSION (auto-commit path: high confidence, unambiguous, no conflict)
        version = commit_proposal(db, proposal=p, reviewer="system:auto-commit", correlation_id=correlation_id)
        committed_versions.append(version.version_number)

    log_audit(db, case_id=case_id, actor=actor, event_type="ingestion", correlation_id=correlation_id,
               source=filename, result="completed",
               detail={"document_id": document.id, "proposal_ids": [p.id for p in proposals],
                       "committed_versions": committed_versions, "conflicts": [c.id for c in conflicts]})

    return {
        "document_id": document.id,
        "extraction_event_id": extraction_event.event_id,
        "proposals": [
            {"id": p.id, "nature": p.nature, "entity_type": p.entity_type,
             "requires_human_review": p.requires_human_review, "review_status": p.review_status,
             "confidence": p.confidence}
            for p in proposals
        ],
        "conflicts_detected": [c.id for c in conflicts],
        "committed_versions": committed_versions,
        "prompt_injection_flagged": document.prompt_injection_flagged,
        "correlation_id": correlation_id,
    }


def review_proposal(
    db: Session, *, proposal: ChangeProposal, decision: str, reviewer: str, edited_after: dict | None = None,
):
    """Human Review Gate action: APPROVE / EDIT / REJECT (section 27)."""
    correlation_id = new_correlation_id()
    if decision == "reject":
        proposal.review_status = "rejected"
        proposal.reviewer = reviewer
        db.commit()
        log_audit(db, case_id=proposal.case_id, actor=reviewer, event_type="rejection",
                   correlation_id=correlation_id, source=proposal.id, result="rejected")
        return {"status": "rejected", "proposal_id": proposal.id}

    verification = verify_proposal(db, proposal=proposal, correlation_id=correlation_id)
    if verification.result != "passed":
        log_audit(db, case_id=proposal.case_id, actor=reviewer, event_type="verification",
                   correlation_id=correlation_id, source=proposal.id, result="failed",
                   detail={"failure_reasons": verification.failure_reasons})
        return {"status": "verification_failed", "failure_reasons": verification.failure_reasons}

    version = commit_proposal(
        db, proposal=proposal, reviewer=reviewer, correlation_id=correlation_id,
        edited_after=edited_after if decision == "edit" else None,
    )
    log_audit(db, case_id=proposal.case_id, actor=reviewer, event_type="approval",
               correlation_id=correlation_id, source=proposal.id, result="committed",
               detail={"version_number": version.version_number})
    return {"status": "committed", "version_number": version.version_number}


def initialize_case_v0(db: Session, *, case_id: str, actor: str = "system"):
    """Create the CASE_CREATED event and StateVersion 0 for a brand new case."""
    from app.models import Case, StateVersion
    from app.state_twin import build_snapshot
    correlation_id = new_correlation_id()
    case = db.get(Case, case_id)
    event = Event(
        case_id=case_id, event_type=EventType.CASE_CREATED.value, source="system", actor=actor,
        description=f"Case '{case.title}' created.", structured_payload={}, confidence=1.0,
        provenance={}, correlation_id=correlation_id,
    )
    db.add(event)
    db.flush()
    snapshot = build_snapshot(db, case_id)
    version = StateVersion(
        case_id=case_id, version_number=0, label="Initial intake",
        triggering_event_id=event.event_id, snapshot=snapshot, freshness="FRESH",
    )
    db.add(version)
    case.current_version_number = 0
    db.commit()
    log_audit(db, case_id=case_id, actor=actor, event_type="ingestion", correlation_id=correlation_id,
               source="case_init", result="completed", detail={"version": 0})
    return version
