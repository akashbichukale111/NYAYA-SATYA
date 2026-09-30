"""
Continuity Graph (section 8).

Builds a typed node/edge graph for a case:
  CASE -> EVENTS -> DOCUMENTS -> HEARINGS -> ORDERS -> DEADLINES
       -> OBLIGATIONS -> EVIDENCE -> ACTIONS -> STATE VERSIONS

Edges carry provenance (the source_event_id that justified the edge) whenever
one is available on the underlying row, satisfying "every important edge
should have provenance."
"""
from sqlalchemy.orm import Session

from app.models import (
    Case, Event, Document, Hearing, Order, Deadline, Obligation, Evidence,
    Action, StateVersion,
)


def build_graph(db: Session, case_id: str) -> dict:
    case = db.get(Case, case_id)
    if not case:
        raise ValueError("case not found")

    nodes = [{"id": f"case:{case.id}", "type": "CASE", "label": case.title}]
    edges = []

    def add(entity_type: str, row, label_field: str, extra_fields: list[str] | None = None):
        node_id = f"{entity_type.lower()}:{row.id if hasattr(row, 'id') else row.event_id}"
        label = getattr(row, label_field, entity_type)
        data = {"id": node_id, "type": entity_type, "label": str(label)[:80]}
        if extra_fields:
            for f in extra_fields:
                data[f] = getattr(row, f, None)
        nodes.append(data)
        return node_id

    events = db.query(Event).filter(Event.case_id == case_id).order_by(Event.timestamp).all()
    event_node_ids = {}
    for ev in events:
        nid = add("EVENT", ev, "event_type", ["timestamp", "confidence"])
        event_node_ids[ev.event_id] = nid
        edges.append({"from": f"case:{case.id}", "to": nid, "type": "HAS_EVENT"})

    for doc in db.query(Document).filter(Document.case_id == case_id).all():
        nid = add("DOCUMENT", doc, "filename", ["doc_type"])
        edges.append({"from": f"case:{case.id}", "to": nid, "type": "HAS_DOCUMENT"})

    for h in db.query(Hearing).filter(Hearing.case_id == case_id).all():
        nid = add("HEARING", h, "scheduled_date", ["status"])
        edges.append({"from": f"case:{case.id}", "to": nid, "type": "HAS_HEARING"})
        if h.source_event_id in event_node_ids:
            edges.append({"from": event_node_ids[h.source_event_id], "to": nid, "type": "GENERATES",
                          "provenance": h.source_event_id})

    for o in db.query(Order).filter(Order.case_id == case_id).all():
        nid = add("ORDER", o, "summary", ["order_date", "status"])
        edges.append({"from": f"case:{case.id}", "to": nid, "type": "HAS_ORDER"})
        if o.source_event_id in event_node_ids:
            edges.append({"from": event_node_ids[o.source_event_id], "to": nid, "type": "CREATES",
                          "provenance": o.source_event_id})

    for d in db.query(Deadline).filter(Deadline.case_id == case_id).all():
        nid = add("DEADLINE", d, "label", ["due_date", "status"])
        edges.append({"from": f"case:{case.id}", "to": nid, "type": "HAS_DEADLINE"})
        if d.source_event_id in event_node_ids:
            edges.append({"from": event_node_ids[d.source_event_id], "to": nid, "type": "MODIFIES",
                          "provenance": d.source_event_id})

    for ob in db.query(Obligation).filter(Obligation.case_id == case_id).all():
        nid = add("OBLIGATION", ob, "description", ["status"])
        edges.append({"from": f"case:{case.id}", "to": nid, "type": "HAS_OBLIGATION"})
        if ob.source_event_id in event_node_ids:
            edges.append({"from": event_node_ids[ob.source_event_id], "to": nid, "type": "CREATES",
                          "provenance": ob.source_event_id})

    for e in db.query(Evidence).filter(Evidence.case_id == case_id).all():
        nid = add("EVIDENCE", e, "label", ["status"])
        edges.append({"from": f"case:{case.id}", "to": nid, "type": "HAS_EVIDENCE"})
        if e.source_event_id in event_node_ids:
            edges.append({"from": event_node_ids[e.source_event_id], "to": nid, "type": "SUPPORTS",
                          "provenance": e.source_event_id})

    for a in db.query(Action).filter(Action.case_id == case_id).all():
        nid = add("ACTION", a, "description", ["status", "assignee"])
        edges.append({"from": f"case:{case.id}", "to": nid, "type": "HAS_ACTION"})
        if a.source_event_id in event_node_ids:
            edges.append({"from": event_node_ids[a.source_event_id], "to": nid, "type": "GENERATES",
                          "provenance": a.source_event_id})

    for v in db.query(StateVersion).filter(StateVersion.case_id == case_id).order_by(StateVersion.version_number).all():
        nid = add("STATE_VERSION", v, "label", ["version_number", "freshness"])
        edges.append({"from": f"case:{case.id}", "to": nid, "type": "HAS_STATE_VERSION"})
        if v.triggering_event_id in event_node_ids:
            edges.append({"from": event_node_ids[v.triggering_event_id], "to": nid, "type": "CREATES_NEW_STATE",
                          "provenance": v.triggering_event_id})

    return {"nodes": nodes, "edges": edges}
