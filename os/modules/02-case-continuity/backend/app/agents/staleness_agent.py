"""
Staleness Agent (section 12 / 25 #6).

When a new value for an existing entity (e.g. a deadline) is committed, the
OLD row is never deleted - it is marked SUPERSEDED and linked to the event
that superseded it, so the historical record remains intact and inspectable
via the Time Machine.
"""
from sqlalchemy.orm import Session

from app.models import Deadline, ItemStatus
from app.agents.base import run_agent


def supersede_open_deadlines(db: Session, *, case_id: str, except_id: str | None, superseding_event_id: str,
                              correlation_id: str) -> list[str]:
    with run_agent(db, case_id=case_id, agent_name="StalenessAgent", correlation_id=correlation_id,
                    input_summary=f"except_id={except_id}") as result:
        q = db.query(Deadline).filter(Deadline.case_id == case_id, Deadline.status == ItemStatus.OPEN.value)
        if except_id:
            q = q.filter(Deadline.id != except_id)
        superseded_ids = []
        for d in q.all():
            d.status = ItemStatus.SUPERSEDED.value
            d.superseded_by_event_id = superseding_event_id
            superseded_ids.append(d.id)
        db.commit()
        result["output_summary"] = f"superseded {len(superseded_ids)} deadline(s)"
        return superseded_ids
