import uuid
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import Base, engine, get_db
import models
from models import (
    Case, Fact, Document, TimelineEvent, Deadline, Question, Conflict,
    Handoff, HandoffVersion, Acknowledgement, Clarification, Approval,
    AuditEvent, AgentRun, FactStatus, Sensitivity, Role, HandoffState
)
from schemas import (
    CaseCreate, IntakeSubmit, HandoffCreate, AcknowledgeRequest, ClarifyRequest,
    ClarifyRespond, ApprovalRequest, SimulateRequest
)
from facts.engines import recompute_conflicts, missing_information_report, intake_completeness
from privacy.engine import explain_access
from timeline.engine import build_timeline
from handoff.generator import generate_packet
from handoff.simulator import simulate_receiver_view
from handoff.crash_test import run_crash_tests
from verification.context_loss import compare_source_to_handoff, compare_versions, verify_handoff
from agents.pipeline import context_packaging_agent, handoff_review_agent, context_loss_agent
from ingestion.intake import safe_filename, extract_text, content_hash
from security.prompt_injection import scan_for_injection
from audit import log_event
from demo_data import seed_demo_cases

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Legal-Aid Handoff Engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- serialization helpers ----------

def s_case(c: Case) -> dict:
    return {
        "id": c.id, "title": c.title, "citizen_name": c.citizen_name,
        "preferred_language": c.preferred_language, "requested_help": c.requested_help,
        "citizen_narrative": c.citizen_narrative, "parties": c.parties,
        "created_at": c.created_at.isoformat(), "is_demo": c.is_demo, "demo_tag": c.demo_tag,
    }


def s_fact(f: Fact) -> dict:
    return {
        "id": f.id, "label": f.label, "statement": f.statement, "status": f.status.value,
        "sensitivity": f.sensitivity.value, "source_document_id": f.source_document_id,
        "confidence": f.confidence, "provenance_id": f.provenance_id,
        "created_at": f.created_at.isoformat(),
    }


def s_document(d: Document) -> dict:
    return {
        "id": d.id, "filename": d.filename, "source_type": d.source_type,
        "extraction_method": d.extraction_method, "ocr_status": d.ocr_status,
        "content_hash": d.content_hash, "sensitivity": d.sensitivity.value,
        "uploaded_at": d.uploaded_at.isoformat(),
        "has_extracted_text": bool(d.extracted_text),
    }


def s_deadline(d: Deadline) -> dict:
    return {"id": d.id, "description": d.description, "due_date": d.due_date, "status": d.status.value}


def s_question(q: Question) -> dict:
    return {"id": q.id, "text": q.text, "reason": q.reason, "priority": q.priority, "resolved": q.resolved}


def s_conflict(c: Conflict) -> dict:
    return {"id": c.id, "type": c.conflict_type.value, "description": c.description,
            "fact_ids": c.fact_ids, "resolved": c.resolved}


def s_handoff(h: Handoff) -> dict:
    return {
        "id": h.id, "case_id": h.case_id, "purpose": h.purpose,
        "recipient_role": h.recipient_role.value, "sender_role": h.sender_role.value,
        "state": h.state.value, "current_version_number": h.current_version_number,
        "created_at": h.created_at.isoformat(),
        "versions": [v.version_number for v in h.versions],
    }


def s_version(v: HandoffVersion) -> dict:
    return {
        "id": v.id, "handoff_id": v.handoff_id, "version_number": v.version_number,
        "included_fact_ids": v.included_fact_ids, "included_document_ids": v.included_document_ids,
        "included_timeline_event_ids": v.included_timeline_event_ids,
        "included_deadline_ids": v.included_deadline_ids,
        "included_question_ids": v.included_question_ids,
        "included_conflict_ids": v.included_conflict_ids,
        "excluded_field_notes": v.excluded_field_notes,
        "quality_checks": v.quality_checks, "risk_flags": v.risk_flags,
        "created_at": v.created_at.isoformat(),
        "created_by_role": v.created_by_role.value if v.created_by_role else None,
        "acknowledged": v.acknowledgement is not None,
    }


def _get_case_or_404(db: Session, case_id: str) -> Case:
    case = db.query(Case).get(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
    return case


def _get_handoff_or_404(db: Session, case_id: str, handoff_id: str) -> Handoff:
    h = db.query(Handoff).filter(Handoff.id == handoff_id, Handoff.case_id == case_id).first()
    if not h:
        raise HTTPException(404, f"Handoff {handoff_id} not found for case {case_id}")
    return h


# ---------- health ----------

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


# ---------- demo ----------

@app.post("/api/demo/seed")
def demo_seed(db: Session = Depends(get_db)):
    result = seed_demo_cases(db)
    log_event(db, event="demo_seed", details=result)
    return result


# ---------- command center ----------

@app.get("/api/command-center")
def command_center(db: Session = Depends(get_db)):
    cases = db.query(Case).all()
    pending_handoffs = db.query(Handoff).filter(
        Handoff.state.in_([HandoffState.READY_FOR_REVIEW, HandoffState.NEEDS_REVIEW])
    ).all()
    open_clarifications = db.query(Clarification).filter(Clarification.resolved == False).all()  # noqa: E712
    all_conflicts = db.query(Conflict).filter(Conflict.resolved == False).all()  # noqa: E712
    all_deadlines = db.query(Deadline).all()
    recent_handoffs = db.query(Handoff).order_by(Handoff.created_at.desc()).limit(5).all()
    acks = db.query(Acknowledgement).order_by(Acknowledgement.created_at.desc()).limit(5).all()

    return {
        "active_cases": len(cases),
        "pending_handoffs": len(pending_handoffs),
        "clarifications_needed": len(open_clarifications),
        "context_risks": sum(len(h.versions[-1].risk_flags or []) for h in db.query(Handoff).all() if h.versions),
        "missing_information_cases": sum(
            1 for c in cases if missing_information_report(db, c.id)
        ),
        "upcoming_deadlines": [s_deadline(d) for d in all_deadlines],
        "recent_handoffs": [s_handoff(h) for h in recent_handoffs],
        "receiver_acknowledgements": [
            {"id": a.id, "action": a.action, "created_at": a.created_at.isoformat()} for a in acks
        ],
        "unresolved_conflicts": len(all_conflicts),
    }


# ---------- cases ----------

@app.get("/api/cases")
def list_cases(db: Session = Depends(get_db)):
    return [s_case(c) for c in db.query(Case).order_by(Case.created_at.desc()).all()]


@app.post("/api/cases")
def create_case(body: CaseCreate, db: Session = Depends(get_db)):
    case = Case(title=body.title, citizen_name=body.citizen_name, preferred_language=body.preferred_language)
    db.add(case)
    db.commit()
    db.refresh(case)
    log_event(db, case_id=case.id, event="case_created", role="CITIZEN")
    return s_case(case)


@app.get("/api/cases/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db)):
    case = _get_case_or_404(db, case_id)
    return s_case(case)


@app.post("/api/cases/{case_id}/intake")
def submit_intake(case_id: str, body: IntakeSubmit, db: Session = Depends(get_db)):
    """Guided intake (sec 55): each answered step becomes structured,
    source-labeled rows — never silently upgraded past USER_REPORTED."""
    case = _get_case_or_404(db, case_id)

    if body.what_happened:
        case.citizen_narrative = (case.citizen_narrative or "") + "\n" + body.what_happened
        db.add(Fact(case_id=case.id, label="what_happened", statement=body.what_happened,
                     status=FactStatus.USER_REPORTED, confidence="medium"))

    if body.who_is_involved:
        case.parties = [{"name": p, "role": "unspecified"} for p in body.who_is_involved]

    if body.when_it_happened:
        db.add(TimelineEvent(case_id=case.id, event_date=body.when_it_happened,
                              description="what_happened: citizen-reported timing",
                              source_type="USER_REPORTED"))

    if body.what_has_happened_since:
        db.add(Fact(case_id=case.id, label="actions_since", statement=body.what_has_happened_since,
                     status=FactStatus.USER_REPORTED, confidence="medium"))

    if body.deadline_or_hearing:
        db.add(Deadline(case_id=case.id, description=body.deadline_or_hearing,
                         due_date=body.deadline_date, status=FactStatus.USER_REPORTED))

    if body.requested_help:
        case.requested_help = body.requested_help

    db.commit()
    recompute_conflicts(db, case.id)
    log_event(db, case_id=case.id, event="intake_submitted", role="CITIZEN")
    return {"status": "ok", "case": s_case(case)}


@app.get("/api/cases/{case_id}/facts")
def get_facts(case_id: str, db: Session = Depends(get_db)):
    _get_case_or_404(db, case_id)
    facts = db.query(Fact).filter(Fact.case_id == case_id).all()
    return [s_fact(f) for f in facts]


@app.get("/api/cases/{case_id}/documents")
def get_documents(case_id: str, db: Session = Depends(get_db)):
    _get_case_or_404(db, case_id)
    docs = db.query(Document).filter(Document.case_id == case_id).all()
    return [s_document(d) for d in docs]


@app.post("/api/cases/{case_id}/documents")
async def upload_document(case_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    case = _get_case_or_404(db, case_id)
    raw = await file.read()
    MAX_SIZE = 10 * 1024 * 1024
    if len(raw) > MAX_SIZE:
        raise HTTPException(413, "File exceeds 10MB demo limit")
    fname = safe_filename(file.filename or "upload")
    text, method, ocr_status = extract_text(raw, fname)

    injection_detected = bool(text and scan_for_injection(text))

    doc = Document(
        case_id=case.id, filename=fname, safe_filename=fname, source_type="upload",
        extraction_method=method, ocr_status=ocr_status, extracted_text=text,
        content_hash=content_hash(raw), sensitivity=Sensitivity.INTERNAL,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    log_event(db, case_id=case.id, event="document_uploaded", role="CITIZEN",
              details={"filename": fname, "prompt_injection_pattern_detected": injection_detected})

    return {**s_document(doc), "prompt_injection_pattern_detected": injection_detected}


@app.get("/api/cases/{case_id}/timeline")
def get_timeline(case_id: str, db: Session = Depends(get_db)):
    _get_case_or_404(db, case_id)
    return build_timeline(db, case_id)


@app.get("/api/cases/{case_id}/conflicts")
def get_conflicts(case_id: str, db: Session = Depends(get_db)):
    _get_case_or_404(db, case_id)
    conflicts = db.query(Conflict).filter(Conflict.case_id == case_id).all()
    return [s_conflict(c) for c in conflicts]


@app.post("/api/cases/{case_id}/conflicts/recompute")
def recompute(case_id: str, db: Session = Depends(get_db)):
    _get_case_or_404(db, case_id)
    created = recompute_conflicts(db, case_id)
    log_event(db, case_id=case_id, event="conflicts_recomputed", details={"count": len(created)})
    return [s_conflict(c) for c in created]


@app.get("/api/cases/{case_id}/missing-information")
def get_missing_info(case_id: str, db: Session = Depends(get_db)):
    _get_case_or_404(db, case_id)
    return missing_information_report(db, case_id)


@app.get("/api/cases/{case_id}/completeness")
def get_completeness(case_id: str, db: Session = Depends(get_db)):
    _get_case_or_404(db, case_id)
    return intake_completeness(db, case_id)


@app.get("/api/cases/{case_id}/deadlines")
def get_deadlines(case_id: str, db: Session = Depends(get_db)):
    _get_case_or_404(db, case_id)
    return [s_deadline(d) for d in db.query(Deadline).filter(Deadline.case_id == case_id).all()]


@app.get("/api/cases/{case_id}/questions")
def get_questions(case_id: str, db: Session = Depends(get_db)):
    _get_case_or_404(db, case_id)
    return [s_question(q) for q in db.query(Question).filter(Question.case_id == case_id).all()]


@app.get("/api/cases/{case_id}/privacy-explain")
def privacy_explain(case_id: str, role: str, db: Session = Depends(get_db)):
    """Section 46: 'Why is this information visible?' — one explanation
    per field, for the given recipient role."""
    _get_case_or_404(db, case_id)
    try:
        recipient_role = Role(role)
    except ValueError:
        raise HTTPException(422, "Invalid role")
    facts = db.query(Fact).filter(Fact.case_id == case_id).all()
    docs = db.query(Document).filter(Document.case_id == case_id).all()
    return {
        "facts": [explain_access(f.label, f.sensitivity, recipient_role) | {"id": f.id} for f in facts],
        "documents": [explain_access(d.filename, d.sensitivity, recipient_role) | {"id": d.id} for d in docs],
    }


# ---------- handoffs ----------

@app.get("/api/cases/{case_id}/handoffs")
def list_handoffs(case_id: str, db: Session = Depends(get_db)):
    _get_case_or_404(db, case_id)
    return [s_handoff(h) for h in db.query(Handoff).filter(Handoff.case_id == case_id).all()]


@app.post("/api/cases/{case_id}/handoffs")
def create_handoff(case_id: str, body: HandoffCreate, db: Session = Depends(get_db)):
    case = _get_case_or_404(db, case_id)
    try:
        recipient_role = Role(body.recipient_role)
        sender_role = Role(body.sender_role)
    except ValueError:
        raise HTTPException(422, "Invalid role")

    version = context_packaging_agent(db, case, body.purpose, recipient_role, sender_role, version_number=1)
    review = handoff_review_agent(db, case, version)
    log_event(db, case_id=case.id, event="handoff_generated", role=sender_role.value,
              details={"handoff_id": version.handoff_id, "version": 1, "review": review["recommendation"]})

    handoff = db.query(Handoff).get(version.handoff_id)
    return {"handoff": s_handoff(handoff), "version": s_version(version), "review": review}


@app.get("/api/cases/{case_id}/handoffs/{handoff_id}")
def get_handoff(case_id: str, handoff_id: str, db: Session = Depends(get_db)):
    h = _get_handoff_or_404(db, case_id, handoff_id)
    return {"handoff": s_handoff(h), "versions": [s_version(v) for v in h.versions]}


@app.post("/api/cases/{case_id}/handoffs/{handoff_id}/review")
def review_handoff(case_id: str, handoff_id: str, db: Session = Depends(get_db)):
    case = _get_case_or_404(db, case_id)
    h = _get_handoff_or_404(db, case_id, handoff_id)
    version = h.versions[-1]
    review = handoff_review_agent(db, case, version)
    log_event(db, case_id=case_id, event="handoff_reviewed", details=review)
    return review


@app.post("/api/cases/{case_id}/handoffs/{handoff_id}/approve")
def approve_handoff(case_id: str, handoff_id: str, body: ApprovalRequest, db: Session = Depends(get_db)):
    h = _get_handoff_or_404(db, case_id, handoff_id)
    version = h.versions[-1]
    try:
        role = Role(body.approved_by_role)
    except ValueError:
        raise HTTPException(422, "Invalid role")

    approval = Approval(handoff_version_id=version.id, approved_by_role=role,
                         decision=body.decision, note=body.note)
    db.add(approval)
    if body.decision == "APPROVE":
        h.state = HandoffState.APPROVED
    elif body.decision == "REJECT":
        h.state = HandoffState.BLOCKED
    db.commit()
    log_event(db, case_id=case_id, event="handoff_approval_decision", role=role.value,
              details={"decision": body.decision, "handoff_id": handoff_id})
    return {"status": "ok", "handoff": s_handoff(h)}


@app.post("/api/cases/{case_id}/handoffs/{handoff_id}/transfer")
def transfer_handoff(case_id: str, handoff_id: str, db: Session = Depends(get_db)):
    """Section 22: secure-transfer abstraction — marks the handoff as
    delivered to the receiver's queue. No real network transfer occurs;
    this is a demo abstraction (SIMULATION)."""
    h = _get_handoff_or_404(db, case_id, handoff_id)
    if h.state != HandoffState.APPROVED:
        raise HTTPException(409, f"Handoff must be APPROVED before transfer (current: {h.state.value})")
    h.state = HandoffState.TRANSFERRED
    db.commit()
    log_event(db, case_id=case_id, event="handoff_transferred", details={"mode": "SIMULATION"})
    return {"status": "SIMULATION", "handoff": s_handoff(h)}


@app.post("/api/cases/{case_id}/handoffs/{handoff_id}/acknowledge")
def acknowledge_handoff(case_id: str, handoff_id: str, body: AcknowledgeRequest, db: Session = Depends(get_db)):
    h = _get_handoff_or_404(db, case_id, handoff_id)
    version = h.versions[-1]
    if version.acknowledgement:
        raise HTTPException(409, "This version already has an acknowledgement")
    ack = Acknowledgement(handoff_version_id=version.id, action=body.action, note=body.note)
    db.add(ack)
    if body.action in ("ACKNOWLEDGE", "ACCEPT"):
        h.state = HandoffState.ACKNOWLEDGED
    elif body.action == "REQUEST_CLARIFICATION":
        h.state = HandoffState.CLARIFICATION_REQUESTED
    elif body.action == "RETURN_FOR_CORRECTION":
        h.state = HandoffState.RETURNED_FOR_CORRECTION
    db.commit()
    log_event(db, case_id=case_id, event="handoff_acknowledged", details={"action": body.action})

    verification = verify_handoff(db, version)
    return {"status": "ok", "handoff": s_handoff(h), "verification": verification}


@app.post("/api/cases/{case_id}/handoffs/{handoff_id}/clarify")
def request_clarification(case_id: str, handoff_id: str, body: ClarifyRequest, db: Session = Depends(get_db)):
    h = _get_handoff_or_404(db, case_id, handoff_id)
    version = h.versions[-1]
    clar = Clarification(handoff_version_id=version.id, question=body.question)
    db.add(clar)
    h.state = HandoffState.CLARIFICATION_REQUESTED
    db.commit()
    db.refresh(clar)
    log_event(db, case_id=case_id, event="clarification_requested", details={"question": body.question})
    return {"id": clar.id, "question": clar.question, "resolved": clar.resolved}


@app.post("/api/cases/{case_id}/handoffs/{handoff_id}/clarify/{clarification_id}/respond")
def respond_clarification(case_id: str, handoff_id: str, clarification_id: str,
                           body: ClarifyRespond, db: Session = Depends(get_db)):
    case = _get_case_or_404(db, case_id)
    h = _get_handoff_or_404(db, case_id, handoff_id)
    clar = db.query(Clarification).get(clarification_id)
    if not clar:
        raise HTTPException(404, "Clarification not found")
    clar.response = body.response
    clar.resolved = True
    db.commit()

    # generate a new handoff version reflecting the response
    new_version_number = h.current_version_number + 1
    version = context_packaging_agent(
        db, case, h.purpose, h.recipient_role, h.sender_role, version_number=new_version_number
    )
    review = handoff_review_agent(db, case, version)
    log_event(db, case_id=case_id, event="clarification_resolved_new_version",
              details={"version": new_version_number})
    return {"clarification": {"id": clar.id, "response": clar.response, "resolved": True},
            "new_version": s_version(version), "review": review}


@app.get("/api/cases/{case_id}/handoffs/{handoff_id}/diff")
def diff_versions(case_id: str, handoff_id: str, from_version: int, to_version: int,
                   db: Session = Depends(get_db)):
    h = _get_handoff_or_404(db, case_id, handoff_id)
    v_from = next((v for v in h.versions if v.version_number == from_version), None)
    v_to = next((v for v in h.versions if v.version_number == to_version), None)
    if not v_from or not v_to:
        raise HTTPException(404, "Version not found")
    return compare_versions(db, v_from, v_to)


@app.get("/api/cases/{case_id}/handoffs/{handoff_id}/context-loss")
def context_loss(case_id: str, handoff_id: str, version: int = None, db: Session = Depends(get_db)):
    case = _get_case_or_404(db, case_id)
    h = _get_handoff_or_404(db, case_id, handoff_id)
    v = next((x for x in h.versions if x.version_number == version), h.versions[-1]) if version else h.versions[-1]
    return context_loss_agent(db, case, v)


@app.get("/api/cases/{case_id}/handoffs/{handoff_id}/preview")
def preview_handoff(case_id: str, handoff_id: str, db: Session = Depends(get_db)):
    """Section 45/58: sender view -> handoff packet -> receiver view, side by side."""
    case = _get_case_or_404(db, case_id)
    h = _get_handoff_or_404(db, case_id, handoff_id)
    version = h.versions[-1]
    loss = compare_source_to_handoff(db, case, version)
    return {
        "handoff": s_handoff(h),
        "packet": s_version(version),
        "context_loss_preview": loss,
    }


@app.get("/api/cases/{case_id}/handoffs/{handoff_id}/verify")
def verify(case_id: str, handoff_id: str, db: Session = Depends(get_db)):
    h = _get_handoff_or_404(db, case_id, handoff_id)
    version = h.versions[-1]
    return verify_handoff(db, version)


# ---------- simulation / crash test ----------

@app.post("/api/cases/{case_id}/simulate")
def simulate(case_id: str, body: SimulateRequest, db: Session = Depends(get_db)):
    _get_case_or_404(db, case_id)
    try:
        role = Role(body.recipient_role)
    except ValueError:
        raise HTTPException(422, "Invalid role")
    result = simulate_receiver_view(
        db, case_id, role,
        exclude_fact_ids=body.exclude_fact_ids, exclude_document_ids=body.exclude_document_ids,
        exclude_deadline_ids=body.exclude_deadline_ids,
    )
    log_event(db, case_id=case_id, event="simulation_run", details={"mode": "SIMULATION"})
    return {"mode": "SIMULATION", **result}


@app.post("/api/cases/{case_id}/crash-test")
def crash_test(case_id: str, db: Session = Depends(get_db)):
    _get_case_or_404(db, case_id)
    results = run_crash_tests()
    log_event(db, case_id=case_id, event="crash_test_run",
              details={"pass": sum(1 for r in results if r["result"] == "PASS"), "total": len(results)})
    return results


# ---------- audit ----------

@app.get("/api/cases/{case_id}/audit")
def get_audit(case_id: str, db: Session = Depends(get_db)):
    _get_case_or_404(db, case_id)
    events = db.query(AuditEvent).filter(AuditEvent.case_id == case_id).order_by(AuditEvent.created_at).all()
    return [
        {"id": e.id, "actor": e.actor, "role": e.role, "event": e.event, "result": e.result,
         "correlation_id": e.correlation_id, "source": e.source, "details": e.details,
         "created_at": e.created_at.isoformat()}
        for e in events
    ]


@app.get("/api/cases/{case_id}/agent-runs")
def get_agent_runs(case_id: str, db: Session = Depends(get_db)):
    _get_case_or_404(db, case_id)
    runs = db.query(AgentRun).filter(AgentRun.case_id == case_id).order_by(AgentRun.created_at).all()
    return [
        {"id": r.id, "agent_name": r.agent_name, "input_summary": r.input_summary,
         "output_summary": r.output_summary, "provider": r.provider, "latency_ms": r.latency_ms,
         "created_at": r.created_at.isoformat()}
        for r in runs
    ]
