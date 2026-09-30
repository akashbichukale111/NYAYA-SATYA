from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import orm, schemas
from app.core.security import get_current_user, CurrentUser, require_min_role, WRITE_MIN_ROLE, get_case_or_404
from app.core.documents import ingest_document
from app.core.enums import DocumentStatus
from app.agents.extraction import DocumentIntakeAgent
from app.agents.reconciliation import run_all_reconciliation
from app.agents.attention import run_attention_engine
from app.agents.dependency import rebuild_dependency_graph
from app.agents.time_machine import take_snapshot
from app.agents.governance import log_audit_event

router = APIRouter(prefix="/api/cases", tags=["cases"])
intake_agent = DocumentIntakeAgent()


def _recompute_case(db: Session, case_id: str):
    """
    Runs reconciliation -> attention -> dependency recomputation and commits
    the result. These three agent functions only flush internally (so they
    remain safe to call from inside a Simulation/Crash Test SAVEPOINT); this
    wrapper is the one responsible for the real, durable commit on the
    normal (non-simulated) request path.
    """
    run_all_reconciliation(db, case_id)
    run_attention_engine(db, case_id)
    rebuild_dependency_graph(db, case_id)
    db.commit()


@router.post("", response_model=schemas.CaseOut)
def create_case(payload: schemas.CaseCreate, db: Session = Depends(get_db),
                 user: CurrentUser = Depends(get_current_user)):
    require_min_role(user, WRITE_MIN_ROLE)
    case = orm.Case(
        case_reference=payload.case_reference, title=payload.title,
        jurisdiction_note=payload.jurisdiction_note, created_by_user_id=user.user_id,
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    person = orm.Person(case_id=case.id, full_name=payload.person_full_name, role_in_case="UNDERTRIAL")
    db.add(person)
    db.commit()

    log_audit_event(db, case.id, user.user_id, "CREATE", "Case", case.id, {"title": case.title})
    take_snapshot(db, case.id, "case_created", user.user_id)
    return case


@router.get("", response_model=list[schemas.CaseOut])
def list_cases(db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    return db.query(orm.Case).order_by(orm.Case.created_at.desc()).all()


@router.get("/{case_id}", response_model=schemas.CaseOut)
def get_case(case_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    case = get_case_or_404(db, case_id)
    log_audit_event(db, case_id, user.user_id, "VIEW", "Case", case_id)
    return case


@router.post("/{case_id}/documents", response_model=schemas.DocumentOut)
async def upload_document(case_id: str, file: UploadFile = File(...), db: Session = Depends(get_db),
                           user: CurrentUser = Depends(get_current_user)):
    require_min_role(user, WRITE_MIN_ROLE)
    case = get_case_or_404(db, case_id)

    file_bytes = await file.read()
    result = ingest_document(file_bytes, file.filename, file.content_type or "application/octet-stream")

    doc = orm.Document(
        case_id=case.id, filename=file.filename, safe_filename=result.safe_filename,
        mime_type=file.content_type or "application/octet-stream", size_bytes=str(result.size_bytes),
        sha256=result.sha256, status=result.status, extraction_method=result.extraction_method,
        extracted_text=result.extracted_text, uploaded_by_user_id=user.user_id,
        rejection_reason=result.rejection_reason,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    log_audit_event(db, case_id, user.user_id, "CREATE", "Document", doc.id,
                     {"status": doc.status, "sha256": doc.sha256})

    if doc.status == DocumentStatus.PARSED.value and doc.extracted_text:
        extracted = intake_agent.process(doc.id, doc.extracted_text)
        for c in extracted["custody_events"]:
            db.add(orm.CustodyEvent(
                case_id=case_id, event_type=c.fields["event_type"], event_date=c.date_iso,
                date_type=c.date_type, verification_status="SOURCE_FACT",
                source_document_id=doc.id, source_text_snippet=c.source_text_snippet,
                extraction_method=doc.extraction_method,
            ))
        for h in extracted["hearings"]:
            db.add(orm.Hearing(
                case_id=case_id, hearing_date=h.date_iso, date_type=h.date_type,
                purpose=h.fields.get("purpose"), status=h.fields.get("status"),
                verification_status="SOURCE_FACT", source_document_id=doc.id,
                source_text_snippet=h.source_text_snippet, extraction_method=doc.extraction_method,
            ))
        for o in extracted["orders"]:
            db.add(orm.Order(
                case_id=case_id, status=o.fields.get("status"), summary=o.fields.get("summary"),
                mentioned_date=o.date_iso, date_type=o.date_type, verification_status="SOURCE_FACT",
                source_document_id=doc.id, source_text_snippet=o.source_text_snippet,
                extraction_method=doc.extraction_method,
            ))
        for b in extracted["bail_events"]:
            db.add(orm.BailEvent(
                case_id=case_id, event_type=b.fields.get("event_type"), summary=b.fields.get("summary"),
                event_date=b.date_iso, date_type=b.date_type, verification_status="SOURCE_FACT",
                source_document_id=doc.id, source_text_snippet=b.source_text_snippet,
                extraction_method=doc.extraction_method,
            ))
        for r in extracted["release_events"]:
            db.add(orm.ReleaseRelatedEvent(
                case_id=case_id, event_type=r.fields.get("event_type"), summary=r.fields.get("summary"),
                event_date=r.date_iso, date_type=r.date_type,
                current_status_confidence="CURRENT_STATUS_UNVERIFIED",
                verification_status="SOURCE_FACT", source_document_id=doc.id,
                source_text_snippet=r.source_text_snippet, extraction_method=doc.extraction_method,
            ))
        db.commit()
        _recompute_case(db, case_id)
        take_snapshot(db, case_id, "document_ingested", user.user_id)

    return doc


@router.get("/{case_id}/documents", response_model=list[schemas.DocumentOut])
def list_documents(case_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    get_case_or_404(db, case_id)
    return db.query(orm.Document).filter(orm.Document.case_id == case_id).order_by(orm.Document.created_at.desc()).all()
