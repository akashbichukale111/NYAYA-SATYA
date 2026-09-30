from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db import Source, Deadline, AuditLogEntry
from app.models.enums import DeadlineStatus, ProvenanceState
from app.schemas import (
    IngestTextRequest, SourceOut, DeadlineOut, ReviewDeadlineRequest,
)
from app.services.ingestion import ingest_text, IngestionError

router = APIRouter()


@router.post("/ingest/text", response_model=SourceOut, status_code=201)
def ingest_text_endpoint(payload: IngestTextRequest, db: Session = Depends(get_db)):
    try:
        source = ingest_text(db, payload.label, payload.text, payload.source_type)
    except IngestionError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return source


@router.get("/sources/{source_id}", response_model=SourceOut)
def get_source(source_id: str, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.get("/deadlines", response_model=List[DeadlineOut])
def list_deadlines(
    status: Optional[DeadlineStatus] = Query(None),
    provenance_state: Optional[ProvenanceState] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Deadline)
    if status:
        q = q.filter(Deadline.status == status)
    if provenance_state:
        q = q.filter(Deadline.provenance_state == provenance_state)
    return q.order_by(Deadline.due_date.is_(None), Deadline.due_date.asc()).all()


@router.get("/deadlines/{deadline_id}", response_model=DeadlineOut)
def get_deadline(deadline_id: str, db: Session = Depends(get_db)):
    deadline = db.get(Deadline, deadline_id)
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
    return deadline


@router.post("/deadlines/{deadline_id}/review", response_model=DeadlineOut)
def review_deadline(deadline_id: str, payload: ReviewDeadlineRequest, db: Session = Depends(get_db)):
    """
    The ONLY way a deadline moves out of PENDING_REVIEW.

    This is a human-in-the-loop checkpoint, not an autonomous approval —
    the caller must supply a reviewer identity. Nothing here lets the
    system self-verify a date.
    """
    deadline = db.get(Deadline, deadline_id)
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    if payload.corrected_due_date:
        deadline.due_date = payload.corrected_due_date
        deadline.provenance_state = ProvenanceState.USER_ENTERED

    if payload.approve:
        deadline.status = DeadlineStatus.VERIFIED
    else:
        # Rejected, not deleted: it stays visible in the review queue rather
        # than silently disappearing.
        deadline.status = DeadlineStatus.PENDING_REVIEW

    deadline.reviewed_by = payload.reviewer
    deadline.reviewed_at = datetime.utcnow()

    db.add(
        AuditLogEntry(
            entity_type="deadline",
            entity_id=deadline.id,
            action="reviewed",
            actor=payload.reviewer,
            detail=f"approve={payload.approve} note={payload.note!r}",
        )
    )
    db.commit()
    db.refresh(deadline)
    return deadline


@router.get("/health")
def health():
    return {"status": "ok", "service": "spark-deadline-guardian", "section": 1}
