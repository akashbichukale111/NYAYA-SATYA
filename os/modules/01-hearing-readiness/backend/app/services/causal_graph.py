"""
Blocker Causal Graph (section 8):
HEARING -> REQUIREMENT -> EVIDENCE -> DEPENDENCY -> BLOCKER ->
RESPONSIBLE ACTOR -> SAFE ACTION -> VERIFICATION -> UPDATED CASE STATE

Dependency rows are (re)synced from current DB state every time the
readiness audit runs, so the graph always reflects reality rather than
being maintained by hand. Every edge carries a `reason`.
"""
from __future__ import annotations

from app.models.blocker import Blocker, Dependency
from app.models.requirement import Requirement
from app.models.hearing import Hearing
from app.models.action import Action


def sync_dependencies(db, case_id: str) -> None:
    # Clear and rebuild -- dependencies are derived, not hand-authored.
    db.query(Dependency).filter(Dependency.case_id == case_id).delete()

    hearing = db.query(Hearing).filter(Hearing.case_id == case_id, Hearing.is_next == "true").first()
    blockers = db.query(Blocker).filter(Blocker.case_id == case_id, Blocker.status == "OPEN").all()

    for b in blockers:
        req = db.query(Requirement).filter(Requirement.id == b.requirement_id).first()
        if hearing and req:
            db.add(Dependency(
                case_id=case_id, from_node_type="HEARING", from_node_id=hearing.id,
                to_node_type="REQUIREMENT", to_node_id=req.id,
                reason=f"Hearing readiness depends on category '{req.category}'.",
            ))
        if req:
            for eid in (req.evidence_refs or []):
                db.add(Dependency(
                    case_id=case_id, from_node_type="REQUIREMENT", from_node_id=req.id,
                    to_node_type="EVIDENCE", to_node_id=eid,
                    reason="Requirement status is derived from this evidence item.",
                ))
            db.add(Dependency(
                case_id=case_id, from_node_type="REQUIREMENT", from_node_id=req.id,
                to_node_type="BLOCKER", to_node_id=b.id,
                reason=f"Requirement is unresolved: {req.reason}",
            ))
        if b.responsible_actor:
            db.add(Dependency(
                case_id=case_id, from_node_type="BLOCKER", from_node_id=b.id,
                to_node_type="ACTOR", to_node_id=b.responsible_actor,
                reason="Actor is responsible for resolving this blocker.",
            ))
        actions = db.query(Action).filter(Action.blocker_id == b.id).all()
        for a in actions:
            db.add(Dependency(
                case_id=case_id, from_node_type="BLOCKER", from_node_id=b.id,
                to_node_type="ACTION", to_node_id=a.id,
                reason="Safe action proposed to help resolve this blocker.",
            ))
            if a.verification:
                db.add(Dependency(
                    case_id=case_id, from_node_type="ACTION", from_node_id=a.id,
                    to_node_type="VERIFICATION", to_node_id=a.verification.id,
                    reason="Action outcome must be verified before trusted.",
                ))


def get_graph(db, case_id: str) -> dict:
    deps = db.query(Dependency).filter(Dependency.case_id == case_id).all()
    node_ids = set()
    edges = []
    for d in deps:
        node_ids.add((d.from_node_type, d.from_node_id))
        node_ids.add((d.to_node_type, d.to_node_id))
        edges.append(d.to_dict())
    nodes = [{"type": t, "id": i} for t, i in node_ids]
    return {"nodes": nodes, "edges": edges}
