"""
Reconciliation Agent.

Detects disagreements between records of the same type in the same case
(e.g. two custody events of the same event_type with different event_date
values from different source documents). When a conflict is found, a
Conflict record is created with status OPEN and BOTH values preserved, and
a ReviewTask is opened requiring human resolution -- conflict resolution is
one of the actions the master spec lists as requiring the Human Review Gate
(see app/agents/governance.py::ACTIONS_REQUIRING_REVIEW). The system never
auto-resolves a conflict.
"""
from itertools import combinations
from typing import List
from sqlalchemy.orm import Session

from app.models import orm
from app.core.enums import ConflictStatus, ReviewTaskType, ReviewTaskStatus


def detect_custody_event_conflicts(db: Session, case_id: str, commit: bool = True) -> List[orm.Conflict]:
    events = db.query(orm.CustodyEvent).filter(orm.CustodyEvent.case_id == case_id).all()
    new_conflicts = []

    # Group by event_type; if two events of the same type have different,
    # both-known event_dates from different source documents, flag a conflict.
    by_type = {}
    for e in events:
        by_type.setdefault(e.event_type, []).append(e)

    for event_type, group in by_type.items():
        for a, b in combinations(group, 2):
            if not a.event_date or not b.event_date:
                continue
            if a.source_document_id == b.source_document_id:
                continue
            if a.event_date != b.event_date:
                # Avoid duplicate conflict records
                existing = db.query(orm.Conflict).filter(
                    orm.Conflict.case_id == case_id,
                    orm.Conflict.entity_type == "CustodyEvent",
                    orm.Conflict.field_name == "event_date",
                ).all()
                already_flagged = any(
                    {c.value_a, c.value_b} == {a.event_date, b.event_date} for c in existing
                )
                if already_flagged:
                    continue
                conflict = orm.Conflict(
                    case_id=case_id,
                    entity_type="CustodyEvent",
                    field_name="event_date",
                    source_a_ref={"document_id": a.source_document_id, "entity_id": a.id,
                                  "snippet": a.source_text_snippet},
                    source_b_ref={"document_id": b.source_document_id, "entity_id": b.id,
                                  "snippet": b.source_text_snippet},
                    value_a=a.event_date,
                    value_b=b.event_date,
                    status=ConflictStatus.OPEN.value,
                )
                db.add(conflict)
                db.flush()  # need conflict.id before creating the linked review task
                new_conflicts.append(conflict)
                # Mark both events CONFLICTING
                a.verification_status = "CONFLICTING"
                b.verification_status = "CONFLICTING"

                db.add(orm.ReviewTask(
                    case_id=case_id,
                    task_type=ReviewTaskType.CONFLICT_RESOLUTION.value,
                    description=(
                        f"Two sources disagree on custody event date "
                        f"('{a.event_date}' vs '{b.event_date}'). Human legal review is "
                        f"required to determine which record is authoritative."
                    ),
                    related_entity_type="Conflict",
                    related_entity_id=conflict.id,
                    status=ReviewTaskStatus.PENDING.value,
                ))

    if commit:
        db.commit()
        for c in new_conflicts:
            db.refresh(c)
    else:
        # flush, not commit -- see note in app/agents/attention.py. This keeps
        # the function safe to call from inside a Simulation/Crash Test SAVEPOINT.
        db.flush()
    return new_conflicts


def run_all_reconciliation(db: Session, case_id: str, commit: bool = True) -> List[orm.Conflict]:
    conflicts = []
    conflicts.extend(detect_custody_event_conflicts(db, case_id, commit=commit))
    return conflicts
