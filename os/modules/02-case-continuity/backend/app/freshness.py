"""
State Freshness model (section 17).

Explicitly an INFORMATION-STATE QUALITY SIGNAL, not a claim about legal
truth or case merits. Computed from: age of the latest verified event,
count of pending human reviews, and count of unresolved conflicts.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Event, ChangeProposal, Conflict


def compute_freshness(db: Session, case_id: str) -> dict:
    last_event = (
        db.query(Event)
        .filter(Event.case_id == case_id)
        .order_by(Event.timestamp.desc())
        .first()
    )
    pending_reviews = (
        db.query(ChangeProposal)
        .filter(ChangeProposal.case_id == case_id, ChangeProposal.review_status == "pending")
        .count()
    )
    unresolved_conflicts = (
        db.query(Conflict)
        .filter(Conflict.case_id == case_id, Conflict.human_review_status == "pending")
        .count()
    )

    if last_event is None:
        return {"level": "UNKNOWN", "reasons": ["No events recorded for this case yet."]}

    ts = last_event.timestamp
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - ts).total_seconds() / 86400.0

    reasons = [f"Last verified event was {age_days:.1f} day(s) ago."]
    if pending_reviews:
        reasons.append(f"{pending_reviews} change proposal(s) awaiting human review.")
    if unresolved_conflicts:
        reasons.append(f"{unresolved_conflicts} unresolved conflict(s).")

    if unresolved_conflicts > 0 or pending_reviews > 2:
        level = "STALE"
    elif pending_reviews > 0 or age_days > 30:
        level = "AGING"
    elif age_days <= 7:
        level = "FRESH"
    else:
        level = "AGING"

    return {"level": level, "reasons": reasons, "age_days": round(age_days, 2),
            "pending_reviews": pending_reviews, "unresolved_conflicts": unresolved_conflicts}
