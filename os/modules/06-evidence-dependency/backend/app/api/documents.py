from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.rbac import Actor, get_actor
from app.core.case_access import require_case_with_access
from app.models.orm import Document
from app.services.document_service import validate_and_store, DocumentValidationError
from app.services.review_service import log_audit_event

router = APIRouter()


def _doc_out(d: Document) -> dict:
    return {
        "id": d.id, "case_id": d.case_id, "filename": d.filename,
        "mime_type": d.mime_type, "file_size_bytes": d.file_size_bytes,
        "sha256_hash": d.sha256_hash, "document_type": d.document_type,
        "status": d.status, "created_at": d.created_at.isoformat(),
    }


@router.post("/cases/{case_id}/documents")
async def upload_document(case_id: str, file: UploadFile = File(...), db: Session = Depends(get_db),
                           actor: Actor = Depends(get_actor)):
    require_case_with_access(db, case_id, actor)
    content = await file.read()
    try:
        doc = validate_and_store(db, case_id, file.filename, content, file.content_type)
    except DocumentValidationError as e:
        raise HTTPException(status_code=415, detail=f"Document rejected and quarantined: {e.reason}")
    return _doc_out(doc)


@router.get("/cases/{case_id}/documents")
def list_documents(case_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    require_case_with_access(db, case_id, actor)
    docs = db.query(Document).filter(Document.case_id == case_id).all()
    return [_doc_out(d) for d in docs]


@router.get("/documents/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    require_case_with_access(db, doc.case_id, actor)
    return _doc_out(doc)


@router.post("/documents/{document_id}/process")
def process_document(document_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    """
    Runs the Evidence -> Claim -> Issue extraction pipeline (see
    app/agents/pipeline.py) over an already-ingested document. Never
    fabricates content: every EvidenceItem created is a verbatim excerpt
    of the real parsed document text.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    require_case_with_access(db, doc.case_id, actor)
    if doc.status != "INGESTED":
        raise HTTPException(status_code=400, detail=f"Document is not in an ingested state (status={doc.status}).")

    from app.agents.pipeline import run_pipeline
    try:
        summary = run_pipeline(db, doc.case_id, doc.id, actor_id=actor.user_id)
    except DocumentValidationError as e:
        doc.status = "PARSE_FAILED"
        log_audit_event(db, doc.case_id, actor="ExtractionAgent", actor_type="AGENT",
                         action="DOCUMENT_PARSE_FAILED", target_type="DOCUMENT", target_id=doc.id,
                         detail={"reason": e.reason})
        db.commit()
        raise HTTPException(status_code=422, detail=f"Document could not be parsed: {e.reason}")
    return summary
