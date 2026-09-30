from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import orm
from app.core.security import get_current_user, CurrentUser, get_case_or_404
from app.agents.digital_twin import build_digital_twin

router = APIRouter(prefix="/api/cases", tags=["twin"])


def _ser(row, fields):
    return {f: getattr(row, f, None) for f in fields}


@router.get("/{case_id}/custody")
def get_custody(case_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    get_case_or_404(db, case_id)
    events = db.query(orm.CustodyEvent).filter(orm.CustodyEvent.case_id == case_id) \
        .order_by(orm.CustodyEvent.event_date.asc().nullslast()).all()
    fields = ["id", "case_id", "event_type", "event_date", "date_type", "verification_status",
              "source_document_id", "source_text_snippet", "notes", "created_at"]
    return {"custody_events": [_ser(e, fields) for e in events]}


@router.get("/{case_id}/timeline")
def get_timeline(case_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    get_case_or_404(db, case_id)
    items = []
    for e in db.query(orm.CustodyEvent).filter(orm.CustodyEvent.case_id == case_id).all():
        items.append({"kind": "custody_event", "id": e.id, "date": e.event_date, "date_type": e.date_type,
                      "label": e.event_type, "verification_status": e.verification_status,
                      "source_document_id": e.source_document_id})
    for h in db.query(orm.Hearing).filter(orm.Hearing.case_id == case_id).all():
        items.append({"kind": "hearing", "id": h.id, "date": h.hearing_date, "date_type": h.date_type,
                      "label": h.purpose or "Hearing", "status": h.status,
                      "verification_status": h.verification_status, "source_document_id": h.source_document_id})
    for o in db.query(orm.Order).filter(orm.Order.case_id == case_id).all():
        items.append({"kind": "order", "id": o.id, "date": o.mentioned_date, "date_type": o.date_type,
                      "label": o.summary or "Order", "status": o.status,
                      "verification_status": o.verification_status, "source_document_id": o.source_document_id})
    for b in db.query(orm.BailEvent).filter(orm.BailEvent.case_id == case_id).all():
        items.append({"kind": "bail_event", "id": b.id, "date": b.event_date, "date_type": b.date_type,
                      "label": b.event_type, "verification_status": b.verification_status,
                      "source_document_id": b.source_document_id})
    for r in db.query(orm.ReleaseRelatedEvent).filter(orm.ReleaseRelatedEvent.case_id == case_id).all():
        items.append({"kind": "release_event", "id": r.id, "date": r.event_date, "date_type": r.date_type,
                      "label": r.event_type, "current_status_confidence": r.current_status_confidence,
                      "verification_status": r.verification_status, "source_document_id": r.source_document_id})

    dated = [i for i in items if i["date"]]
    undated = [i for i in items if not i["date"]]
    dated.sort(key=lambda i: i["date"])
    return {"timeline": dated + undated, "undated_count": len(undated)}


@router.get("/{case_id}/hearings")
def get_hearings(case_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    get_case_or_404(db, case_id)
    fields = ["id", "case_id", "hearing_date", "date_type", "purpose", "status", "result_summary",
              "verification_status", "source_document_id", "source_text_snippet"]
    rows = db.query(orm.Hearing).filter(orm.Hearing.case_id == case_id).all()
    return {"hearings": [_ser(r, fields) for r in rows]}


@router.get("/{case_id}/orders")
def get_orders(case_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    get_case_or_404(db, case_id)
    fields = ["id", "case_id", "related_hearing_id", "status", "mentioned_date", "date_type", "summary",
              "verification_status", "source_document_id", "source_text_snippet", "superseded_by_order_id"]
    rows = db.query(orm.Order).filter(orm.Order.case_id == case_id).all()
    return {"orders": [_ser(r, fields) for r in rows]}


@router.get("/{case_id}/bail-events")
def get_bail_events(case_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    get_case_or_404(db, case_id)
    fields = ["id", "case_id", "event_type", "event_date", "date_type", "summary",
              "verification_status", "source_document_id", "source_text_snippet"]
    rows = db.query(orm.BailEvent).filter(orm.BailEvent.case_id == case_id).all()
    return {"bail_events": [_ser(r, fields) for r in rows]}


@router.get("/{case_id}/release-events")
def get_release_events(case_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    get_case_or_404(db, case_id)
    fields = ["id", "case_id", "event_type", "event_date", "date_type", "current_status_confidence",
              "summary", "verification_status", "source_document_id", "source_text_snippet"]
    rows = db.query(orm.ReleaseRelatedEvent).filter(orm.ReleaseRelatedEvent.case_id == case_id).all()
    return {"release_events": [_ser(r, fields) for r in rows]}


@router.get("/{case_id}/digital-twin")
def get_digital_twin(case_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    get_case_or_404(db, case_id)
    return build_digital_twin(db, case_id)
