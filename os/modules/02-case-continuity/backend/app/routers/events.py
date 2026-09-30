from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Case, Event

router = APIRouter(prefix="/api/cases", tags=["events"])


@router.get("/{case_id}/events")
def list_events(case_id: str, db: Session = Depends(get_db)):
    if not db.get(Case, case_id):
        raise HTTPException(404, "case not found")
    events = db.query(Event).filter(Event.case_id == case_id).order_by(Event.timestamp).all()
    return [
        {
            "event_id": e.event_id, "event_type": e.event_type, "timestamp": e.timestamp.isoformat(),
            "source": e.source, "actor": e.actor, "description": e.description,
            "structured_payload": e.structured_payload, "confidence": e.confidence,
            "provenance": e.provenance, "correlation_id": e.correlation_id,
        }
        for e in events
    ]
