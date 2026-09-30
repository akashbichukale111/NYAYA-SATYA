from sqlalchemy.orm import Session
from models import TimelineEvent


def build_timeline(db: Session, case_id: str) -> list[dict]:
    events = (
        db.query(TimelineEvent)
        .filter(TimelineEvent.case_id == case_id)
        .all()
    )
    # Sort: dated events chronologically, undated events last (never silently dropped)
    dated = sorted([e for e in events if e.event_date], key=lambda e: e.event_date)
    undated = [e for e in events if not e.event_date]
    out = []
    for e in dated + undated:
        out.append({
            "id": e.id,
            "date": e.event_date or "NOT_PROVIDED",
            "description": e.description,
            "source_type": e.source_type,
            "source_document_id": e.source_document_id,
        })
    return out
