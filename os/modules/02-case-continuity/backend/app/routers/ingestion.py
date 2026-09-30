from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Case
from app.security import FileValidationError
from app.agents.orchestrator import ingest_and_process

router = APIRouter(prefix="/api/cases", tags=["ingestion"])


@router.post("/{case_id}/ingest")
async def ingest_document(
    case_id: str,
    file: UploadFile = File(...),
    doc_type_hint: str = Form(""),
    actor: str = Form("user"),
    db: Session = Depends(get_db),
):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "case not found")
    content = await file.read()
    try:
        result = ingest_and_process(
            db, case_id=case_id, filename=file.filename, content=content,
            doc_type_hint=doc_type_hint, actor=actor,
        )
    except FileValidationError as exc:
        raise HTTPException(400, str(exc)) from exc
    return result
