"""
Liberty Attention Engine.

Generates operational AttentionItems. Severity is an ATTENTION PRIORITY,
never a legal-seriousness score. This engine deliberately uses
PAST_TRACKED_DATE rather than any 'LEGALLY_OVERDUE' label, and never
computes a statutory deadline -- it only compares source-stated dates to
today's date.
"""
from datetime import datetime, date, timedelta, timezone
from typing import List
from sqlalchemy.orm import Session

from app.models import orm
from app.core.config import settings
from app.core.enums import AttentionCategory, SignalSeverity, SignalStatus, DateType


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).date()
    except ValueError:
        return None


def _clear_open_items_for_category(db: Session, case_id: str, category: str):
    """Recompute cleanly: close out previously-open auto-generated items in this
    category so the engine reflects current state rather than accumulating stale items."""
    items = db.query(orm.AttentionItem).filter(
        orm.AttentionItem.case_id == case_id,
        orm.AttentionItem.category == category,
        orm.AttentionItem.status == SignalStatus.OPEN.value,
    ).all()
    for item in items:
        item.status = SignalStatus.RESOLVED.value


def _create(db, case_id, category, severity, reason, source_refs, related_type=None, related_id=None,
            requires_review=False):
    item = orm.AttentionItem(
        case_id=case_id,
        category=category,
        severity=severity,
        reason=reason,
        source_refs=source_refs,
        status=SignalStatus.OPEN.value,
        requires_human_review=requires_review,
        related_entity_type=related_type,
        related_entity_id=related_id,
    )
    db.add(item)
    return item


def run_attention_engine(db: Session, case_id: str, today: date = None, commit: bool = True) -> List[orm.AttentionItem]:
    today = today or datetime.now(timezone.utc).date()
    generated = []

    for cat in AttentionCategory:
        _clear_open_items_for_category(db, case_id, cat.value)

    # --- UPCOMING_SOURCE_DATE / PAST_TRACKED_DATE from hearings ---
    hearings = db.query(orm.Hearing).filter(orm.Hearing.case_id == case_id).all()
    for h in hearings:
        d = _parse_date(h.hearing_date)
        if not d:
            continue
        delta = (d - today).days
        if 0 <= delta <= settings.UPCOMING_DATE_WINDOW_DAYS:
            generated.append(_create(
                db, case_id, AttentionCategory.UPCOMING_SOURCE_DATE.value, SignalSeverity.ATTENTION.value,
                f"A source-stated hearing date ({h.hearing_date}) is approaching.",
                [{"document_id": h.source_document_id, "entity_id": h.id}],
                "Hearing", h.id,
            ))
        elif delta < 0 and h.status not in ("HELD_RESULT_RECORDED",):
            generated.append(_create(
                db, case_id, AttentionCategory.PAST_TRACKED_DATE.value, SignalSeverity.HIGH_ATTENTION.value,
                f"A source-stated hearing date ({h.hearing_date}) has passed with no recorded result.",
                [{"document_id": h.source_document_id, "entity_id": h.id}],
                "Hearing", h.id,
            ))
            generated.append(_create(
                db, case_id, AttentionCategory.MISSING_HEARING_RESULT.value, SignalSeverity.HIGH_ATTENTION.value,
                "The system does not have sufficient verified information about this hearing's result.",
                [{"document_id": h.source_document_id, "entity_id": h.id}],
                "Hearing", h.id,
            ))

    # --- CONFLICTING_CUSTODY_INFORMATION ---
    open_conflicts = db.query(orm.Conflict).filter(
        orm.Conflict.case_id == case_id, orm.Conflict.status == "OPEN"
    ).all()
    for c in open_conflicts:
        generated.append(_create(
            db, case_id, AttentionCategory.CONFLICTING_CUSTODY_INFORMATION.value,
            SignalSeverity.REQUIRES_HUMAN_REVIEW.value,
            f"Custody information from two sources conflicts on field '{c.field_name}'.",
            [c.source_a_ref, c.source_b_ref],
            "Conflict", c.id, requires_review=True,
        ))

    # --- MISSING_CUSTODY_INFORMATION ---
    custody_events = db.query(orm.CustodyEvent).filter(orm.CustodyEvent.case_id == case_id).all()
    if not custody_events:
        generated.append(_create(
            db, case_id, AttentionCategory.MISSING_CUSTODY_INFORMATION.value, SignalSeverity.HIGH_ATTENTION.value,
            "No custody events are recorded for this case. The system does not have sufficient "
            "verified information to determine the current custody state.",
            [],
        ))
    else:
        unknown_date_events = [e for e in custody_events if e.date_type == DateType.UNKNOWN_DATE.value]
        for e in unknown_date_events:
            generated.append(_create(
                db, case_id, AttentionCategory.MISSING_CUSTODY_INFORMATION.value, SignalSeverity.ATTENTION.value,
                f"A recorded custody event ({e.event_type}) has no identifiable source-stated date.",
                [{"document_id": e.source_document_id, "entity_id": e.id}],
                "CustodyEvent", e.id,
            ))

    # --- UNVERIFIED_RELEASE_EVENT ---
    release_events = db.query(orm.ReleaseRelatedEvent).filter(orm.ReleaseRelatedEvent.case_id == case_id).all()
    for r in release_events:
        if r.current_status_confidence != "CURRENT_STATUS_VERIFIED":
            generated.append(_create(
                db, case_id, AttentionCategory.UNVERIFIED_RELEASE_EVENT.value,
                SignalSeverity.REQUIRES_HUMAN_REVIEW.value,
                "A release-related event is recorded but current status is not verified. "
                "Human legal review is required before treating this person as currently released.",
                [{"document_id": r.source_document_id, "entity_id": r.id}],
                "ReleaseRelatedEvent", r.id, requires_review=True,
            ))

    # --- UNVERIFIED_BAIL_EVENT ---
    bail_events = db.query(orm.BailEvent).filter(orm.BailEvent.case_id == case_id).all()
    for b in bail_events:
        if b.verification_status not in ("SOURCE_FACT",):
            generated.append(_create(
                db, case_id, AttentionCategory.UNVERIFIED_BAIL_EVENT.value, SignalSeverity.ATTENTION.value,
                f"A bail-related event ({b.event_type}) is recorded but not yet verified against a source.",
                [{"document_id": b.source_document_id, "entity_id": b.id}],
                "BailEvent", b.id,
            ))

    # --- MISSING_ORDER: hearing with recorded result but no linked order ---
    for h in hearings:
        if h.status == "HELD_RESULT_RECORDED":
            linked_orders = db.query(orm.Order).filter(orm.Order.related_hearing_id == h.id).count()
            if linked_orders == 0:
                generated.append(_create(
                    db, case_id, AttentionCategory.MISSING_ORDER.value, SignalSeverity.ATTENTION.value,
                    "A hearing has a recorded result but no linked order document has been ingested.",
                    [{"entity_id": h.id}], "Hearing", h.id,
                ))

    # --- STALE_CASE_STATE: no new events/documents/updates in STALE_CASE_DAYS ---
    case = db.query(orm.Case).filter(orm.Case.id == case_id).first()
    if case:
        latest_times = [case.updated_at]
        for model in (orm.CustodyEvent, orm.Hearing, orm.Order, orm.BailEvent, orm.ReleaseRelatedEvent, orm.Document):
            row = db.query(model).filter(model.case_id == case_id).order_by(model.updated_at.desc()).first()
            if row:
                latest_times.append(row.updated_at)
        latest = max(t for t in latest_times if t is not None)
        latest_aware = latest if latest.tzinfo else latest.replace(tzinfo=timezone.utc)
        if (datetime.now(timezone.utc) - latest_aware).days >= settings.STALE_CASE_DAYS:
            generated.append(_create(
                db, case_id, AttentionCategory.STALE_CASE_STATE.value, SignalSeverity.ATTENTION.value,
                f"No new case activity recorded in the last {settings.STALE_CASE_DAYS} days.",
                [],
            ))

    # --- PROVENANCE_GAP: any custody/hearing/order/bail/release record missing source_document_id ---
    for model, label in [
        (orm.CustodyEvent, "CustodyEvent"), (orm.Hearing, "Hearing"), (orm.Order, "Order"),
        (orm.BailEvent, "BailEvent"), (orm.ReleaseRelatedEvent, "ReleaseRelatedEvent"),
    ]:
        rows = db.query(model).filter(model.case_id == case_id, model.source_document_id.is_(None)).all()
        for row in rows:
            if getattr(row, "reported_by_user_id", None):
                continue  # user-reported events legitimately lack a source document
            generated.append(_create(
                db, case_id, AttentionCategory.PROVENANCE_GAP.value, SignalSeverity.ATTENTION.value,
                f"A {label} record has no linked source document or reporting user.",
                [], label, row.id,
            ))

    # --- HUMAN_REVIEW_REQUIRED: pending review tasks ---
    pending_reviews = db.query(orm.ReviewTask).filter(
        orm.ReviewTask.case_id == case_id, orm.ReviewTask.status == "PENDING"
    ).count()
    if pending_reviews:
        generated.append(_create(
            db, case_id, AttentionCategory.HUMAN_REVIEW_REQUIRED.value, SignalSeverity.REQUIRES_HUMAN_REVIEW.value,
            f"{pending_reviews} item(s) are pending human review.",
            [], requires_review=True,
        ))

    # commit=False is used when this function is called from inside
    # Simulation/Crash Test's SAVEPOINT (see app/agents/simulation.py).
    # Calling db.commit() there would commit the OUTER transaction too,
    # permanently persisting a simulated mutation and breaking the
    # guarantee that simulations never touch production data. flush() makes
    # the rows visible to subsequent queries in the same transaction
    # without ending that transaction.
    if commit:
        db.commit()
        for item in generated:
            db.refresh(item)
    else:
        db.flush()
    return generated
