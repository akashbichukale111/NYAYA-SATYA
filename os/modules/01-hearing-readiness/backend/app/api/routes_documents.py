from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import case_twin, security

router = APIRouter(prefix="/api/cases", tags=["documents"])


@router.get("/{case_id}/documents")
def list_documents(case_id: str, db: Session = Depends(get_db)):
    full = case_twin.get_case_full(db, case_id)
    if not full:
        raise HTTPException(404, "Case not found")
    return full["documents"]


@router.post("/{case_id}/documents")
async def upload_document(case_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    full = case_twin.get_case_full(db, case_id)
    if not full:
        raise HTTPException(404, "Case not found")
    raw = await file.read()
    try:
        doc = case_twin.ingest_document(db, case_id, file.filename, raw)
    except security.UploadRejected as e:
        raise HTTPException(400, str(e))
    db.commit()
    return doc.to_dict()
