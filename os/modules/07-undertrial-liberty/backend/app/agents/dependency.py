"""
Dependency Agent.

Builds the case's dependency graph:
Document -> Event -> Custody State -> Hearing -> Order -> Attention Item
plus the additional relationship types listed in the spec.
Every edge carries provenance (which document/record justified the edge).
"""
from typing import List
from sqlalchemy.orm import Session

from app.models import orm
from app.core.enums import DependencyType, DependencyStatus


def _add_edge(db, case_id, dep_type, from_type, from_id, to_type, to_id, status, source_document_id=None):
    existing = db.query(orm.Dependency).filter(
        orm.Dependency.case_id == case_id,
        orm.Dependency.dependency_type == dep_type,
        orm.Dependency.from_entity_id == from_id,
        orm.Dependency.to_entity_id == to_id,
    ).first()
    if existing:
        existing.status = status
        return existing
    edge = orm.Dependency(
        case_id=case_id, dependency_type=dep_type,
        from_entity_type=from_type, from_entity_id=from_id,
        to_entity_type=to_type, to_entity_id=to_id,
        status=status, source_document_id=source_document_id,
    )
    db.add(edge)
    return edge


def rebuild_dependency_graph(db: Session, case_id: str, commit: bool = True) -> List[orm.Dependency]:
    edges = []

    documents = {d.id: d for d in db.query(orm.Document).filter(orm.Document.case_id == case_id).all()}
    custody_events = db.query(orm.CustodyEvent).filter(orm.CustodyEvent.case_id == case_id).all()
    hearings = db.query(orm.Hearing).filter(orm.Hearing.case_id == case_id).all()
    orders = db.query(orm.Order).filter(orm.Order.case_id == case_id).all()
    bail_events = db.query(orm.BailEvent).filter(orm.BailEvent.case_id == case_id).all()
    release_events = db.query(orm.ReleaseRelatedEvent).filter(orm.ReleaseRelatedEvent.case_id == case_id).all()
    conflicts = db.query(orm.Conflict).filter(orm.Conflict.case_id == case_id).all()
    attention_items = db.query(orm.AttentionItem).filter(
        orm.AttentionItem.case_id == case_id, orm.AttentionItem.status == "OPEN"
    ).all()

    # Document -> Event (custody)
    for e in custody_events:
        if e.source_document_id and e.source_document_id in documents:
            edges.append(_add_edge(db, case_id, DependencyType.DOCUMENT_TO_EVENT.value,
                                    "Document", e.source_document_id, "CustodyEvent", e.id,
                                    DependencyStatus.SATISFIED.value, e.source_document_id))
        # Event -> Custody State (conceptual node id = case_id since custody state is case-level)
        edges.append(_add_edge(db, case_id, DependencyType.EVENT_TO_CUSTODY_STATE.value,
                                "CustodyEvent", e.id, "CustodyState", case_id,
                                DependencyStatus.SATISFIED.value))

    # Custody State -> Hearing, Document -> Order, Hearing -> Order, Order -> Attention/Release
    for h in hearings:
        edges.append(_add_edge(db, case_id, DependencyType.CUSTODY_STATE_TO_HEARING.value,
                                "CustodyState", case_id, "Hearing", h.id,
                                DependencyStatus.SATISFIED.value if custody_events else DependencyStatus.UNKNOWN.value))
        if h.source_document_id and h.source_document_id in documents:
            edges.append(_add_edge(db, case_id, DependencyType.DOCUMENT_TO_EVENT.value,
                                    "Document", h.source_document_id, "Hearing", h.id,
                                    DependencyStatus.SATISFIED.value, h.source_document_id))

    for o in orders:
        status = DependencyStatus.SATISFIED.value if o.related_hearing_id else DependencyStatus.BLOCKED.value
        if o.related_hearing_id:
            edges.append(_add_edge(db, case_id, DependencyType.HEARING_TO_ORDER.value,
                                    "Hearing", o.related_hearing_id, "Order", o.id, status))
        if o.source_document_id and o.source_document_id in documents:
            edges.append(_add_edge(db, case_id, DependencyType.DOCUMENT_TO_ORDER.value,
                                    "Document", o.source_document_id, "Order", o.id,
                                    DependencyStatus.SATISFIED.value, o.source_document_id))

    for b in bail_events:
        if b.related_hearing_id:
            edges.append(_add_edge(db, case_id, DependencyType.BAIL_EVENT_TO_HEARING.value,
                                    "BailEvent", b.id, "Hearing", b.related_hearing_id,
                                    DependencyStatus.SATISFIED.value))

    for r in release_events:
        # Release events depend on an order existing; if none, mark BLOCKED
        related_orders = [o for o in orders if o.status in ("ORDER_ISSUED",) and
                           (o.summary or "").lower().find("release") != -1]
        status = DependencyStatus.SATISFIED.value if related_orders else DependencyStatus.BLOCKED.value
        if related_orders:
            edges.append(_add_edge(db, case_id, DependencyType.ORDER_TO_RELEASE_EVENT.value,
                                    "Order", related_orders[0].id, "ReleaseRelatedEvent", r.id, status))
        else:
            edges.append(_add_edge(db, case_id, DependencyType.ORDER_TO_RELEASE_EVENT.value,
                                    "Order", "UNKNOWN", "ReleaseRelatedEvent", r.id, status))

    for c in conflicts:
        doc_id = c.source_a_ref.get("document_id") if isinstance(c.source_a_ref, dict) else None
        if doc_id:
            edges.append(_add_edge(db, case_id, DependencyType.DOCUMENT_TO_CONFLICT.value,
                                    "Document", doc_id, "Conflict", c.id, DependencyStatus.BLOCKED.value, doc_id))

    for a in attention_items:
        if a.related_entity_id:
            edges.append(_add_edge(db, case_id, DependencyType.ORDER_TO_ATTENTION_ITEM.value,
                                    a.related_entity_type or "Unknown", a.related_entity_id,
                                    "AttentionItem", a.id, DependencyStatus.BLOCKED.value))

    if commit:
        db.commit()
        for e in edges:
            db.refresh(e)
    else:
        # flush, not commit -- see note in app/agents/attention.py. This keeps
        # the function safe to call from inside a Simulation/Crash Test SAVEPOINT.
        db.flush()
    return edges
