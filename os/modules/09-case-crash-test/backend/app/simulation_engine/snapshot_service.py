from sqlalchemy.orm import Session

from app.models.domain import Case, CaseNode, CaseRelationship, CaseSnapshot


def serialize_case_graph(db: Session, case_id: str) -> dict:
    nodes = db.query(CaseNode).filter(CaseNode.case_id == case_id).all()
    edges = db.query(CaseRelationship).filter(CaseRelationship.case_id == case_id).all()
    return {
        "nodes": [
            {
                "id": n.id, "node_type": n.node_type, "label": n.label,
                "status": n.status, "attributes": n.attributes or {},
                "provenance_ref": n.provenance_ref,
            }
            for n in nodes
        ],
        "relationships": [
            {
                "id": e.id, "source_id": e.source_id, "target_id": e.target_id,
                "rel_type": e.rel_type, "attributes": e.attributes or {},
            }
            for e in edges
        ],
    }


def create_snapshot(db: Session, case_id: str, label: str | None = None, created_by: str = "system") -> CaseSnapshot:
    data = serialize_case_graph(db, case_id)
    last = (
        db.query(CaseSnapshot)
        .filter(CaseSnapshot.case_id == case_id)
        .order_by(CaseSnapshot.version.desc())
        .first()
    )
    next_version = (last.version + 1) if last else 1
    snapshot = CaseSnapshot(
        case_id=case_id, version=next_version, label=label, data=data, created_by=created_by,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def restore_snapshot(db: Session, case_id: str, snapshot: CaseSnapshot, approved_by: str, reason: str) -> dict:
    """
    Time Machine — RESTORE-SAFE-SNAPSHOT.

    This is the ONLY operation in the whole engine that is allowed to
    overwrite the real, live case graph — and only because it is reached
    through an explicit, human-approved action (see app/rbac.py: ADMIN-only,
    and routes.py: reason is required). Simulations themselves NEVER call
    this. It replaces the case's live nodes/relationships with exactly the
    node/relationship set recorded in `snapshot.data`, then records a fresh
    snapshot of the restored state so the restore itself is auditable and
    reversible.
    """
    data = snapshot.data or {"nodes": [], "relationships": []}

    db.query(CaseRelationship).filter(CaseRelationship.case_id == case_id).delete()
    db.query(CaseNode).filter(CaseNode.case_id == case_id).delete()
    db.flush()

    for n in data.get("nodes", []):
        db.add(CaseNode(
            id=n["id"], case_id=case_id, node_type=n["node_type"], label=n["label"],
            status=n["status"], attributes=n.get("attributes") or {},
            provenance_ref=n.get("provenance_ref"),
        ))
    for e in data.get("relationships", []):
        db.add(CaseRelationship(
            id=e["id"], case_id=case_id, source_id=e["source_id"], target_id=e["target_id"],
            rel_type=e["rel_type"], attributes=e.get("attributes") or {},
        ))
    db.commit()

    post_restore_snapshot = create_snapshot(
        db, case_id, label=f"post-restore-of-v{snapshot.version}", created_by=approved_by,
    )
    return {
        "restored_from_version": snapshot.version,
        "restored_from_snapshot_id": snapshot.id,
        "approved_by": approved_by,
        "reason": reason,
        "resulting_snapshot_id": post_restore_snapshot.id,
        "resulting_snapshot_version": post_restore_snapshot.version,
    }


def compare_scenarios(result_a: dict, result_b: dict) -> dict:
    """
    Neutral structural comparison of two simulation results. Never ranks
    scenarios as better/worse in any legal sense — only reports differences
    in what was mutated and what was affected.
    """
    br_a = result_a.get("blast_radius", {})
    br_b = result_b.get("blast_radius", {})

    affected_a = set(a["node_id"] for a in result_a.get("affected_nodes", []))
    affected_b = set(a["node_id"] for a in result_b.get("affected_nodes", []))

    return {
        "mutations_a": result_a.get("mutations_applied", []),
        "mutations_b": result_b.get("mutations_applied", []),
        "affected_only_in_a": list(affected_a - affected_b),
        "affected_only_in_b": list(affected_b - affected_a),
        "affected_in_both": list(affected_a & affected_b),
        "total_affected_a": br_a.get("total_affected_count", 0),
        "total_affected_b": br_b.get("total_affected_count", 0),
        "new_conflicts_a": br_a.get("new_conflicts", []),
        "new_conflicts_b": br_b.get("new_conflicts", []),
        "human_review_items_a": br_a.get("human_review_items", []),
        "human_review_items_b": br_b.get("human_review_items", []),
        "note": "Structural comparison only. No legal or outcome ranking is implied.",
    }
