"""
Time Machine.

Takes immutable point-in-time snapshots of the Liberty Digital Twin and
allows diffing between any two snapshots (or the latest snapshot vs
current live state). Never rewrites historical records -- snapshots are
append-only.
"""
from typing import Optional
from sqlalchemy.orm import Session

from app.models import orm
from app.agents.digital_twin import build_digital_twin


def take_snapshot(db: Session, case_id: str, reason: str, triggered_by_user_id: Optional[str] = None) -> orm.CaseSnapshot:
    twin = build_digital_twin(db, case_id)
    snap = orm.CaseSnapshot(
        case_id=case_id, snapshot_reason=reason, snapshot_data=twin,
        triggered_by_user_id=triggered_by_user_id,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def list_snapshots(db: Session, case_id: str):
    return db.query(orm.CaseSnapshot).filter(orm.CaseSnapshot.case_id == case_id) \
        .order_by(orm.CaseSnapshot.created_at.asc()).all()


def _flatten_for_diff(twin: dict) -> dict:
    """Produces a shallow comparable dict of counts/keys for a readable diff."""
    if not twin:
        return {}
    return {
        "custody_state": twin.get("custody_state"),
        "custody_event_count": len(twin.get("current_custody_events", [])),
        "hearing_count": len(twin.get("upcoming_tracked_events", [])),
        "order_count": len(twin.get("recent_orders", [])),
        "bail_event_count": len(twin.get("bail_events", [])),
        "release_event_count": len(twin.get("release_events", [])),
        "conflict_count": len(twin.get("conflicts", [])),
        "attention_item_count": len(twin.get("attention_items", [])),
        "missing_information": twin.get("missing_information", []),
        "pending_review_count": len(twin.get("pending_reviews", [])),
    }


def diff_snapshots(snapshot_a: dict, snapshot_b: dict) -> dict:
    a = _flatten_for_diff(snapshot_a)
    b = _flatten_for_diff(snapshot_b)
    diff = {}
    keys = set(a.keys()) | set(b.keys())
    for k in keys:
        if a.get(k) != b.get(k):
            diff[k] = {"before": a.get(k), "after": b.get(k)}
    return diff
