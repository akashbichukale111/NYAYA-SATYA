"""
Handoff Simulator (sec 45) + Context Loss Simulator (sec 47).

Pure, read-only functions: nothing here writes to the database. They
answer "what would the receiver see if we changed X?" without mutating
production case data.
"""
from sqlalchemy.orm import Session
from models import Fact, Document, Deadline, Role
from privacy.engine import is_allowed


def simulate_receiver_view(db: Session, case_id: str, recipient_role: Role,
                            exclude_fact_ids: list[str] = None,
                            exclude_document_ids: list[str] = None,
                            exclude_deadline_ids: list[str] = None) -> dict:
    exclude_fact_ids = set(exclude_fact_ids or [])
    exclude_document_ids = set(exclude_document_ids or [])
    exclude_deadline_ids = set(exclude_deadline_ids or [])

    all_facts = db.query(Fact).filter(Fact.case_id == case_id).all()
    all_docs = db.query(Document).filter(Document.case_id == case_id).all()
    all_deadlines = db.query(Deadline).filter(Deadline.case_id == case_id).all()

    visible_facts, omitted_facts = [], []
    for f in all_facts:
        if f.id in exclude_fact_ids:
            omitted_facts.append({"id": f.id, "label": f.label, "reason": "manually excluded in simulation"})
        elif not is_allowed(f.sensitivity, recipient_role):
            omitted_facts.append({"id": f.id, "label": f.label, "reason": "above recipient sensitivity ceiling"})
        else:
            visible_facts.append({"id": f.id, "label": f.label, "status": f.status.value})

    visible_docs = [d.filename for d in all_docs
                    if d.id not in exclude_document_ids and is_allowed(d.sensitivity, recipient_role)]
    omitted_docs = [d.filename for d in all_docs
                    if d.id in exclude_document_ids or not is_allowed(d.sensitivity, recipient_role)]

    visible_deadlines = [d.description for d in all_deadlines if d.id not in exclude_deadline_ids]
    omitted_deadlines = [d.description for d in all_deadlines if d.id in exclude_deadline_ids]

    return {
        "recipient_role": recipient_role.value,
        "source_context": {"facts": len(all_facts), "documents": len(all_docs), "deadlines": len(all_deadlines)},
        "receiver_would_see": {
            "facts": visible_facts, "documents": visible_docs, "deadlines": visible_deadlines,
        },
        "receiver_would_miss": {
            "facts": omitted_facts, "documents": omitted_docs, "deadlines": omitted_deadlines,
        },
    }
