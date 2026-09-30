from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.rbac import Actor, get_actor
from app.core.case_access import require_case_with_access
from app.models.orm import EvidenceItem, Claim, Issue, EvidenceRelationship
from app.services.graph_service import coverage_metrics, fragility_report, missing_evidence_report

router = APIRouter()


@router.get("/cases/{case_id}/dependency-graph")
def get_dependency_graph(case_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    require_case_with_access(db, case_id, actor)

    nodes = []
    for e in db.query(EvidenceItem).filter(EvidenceItem.case_id == case_id).all():
        nodes.append({"id": e.id, "type": "EVIDENCE", "label": e.label, "state": e.state,
                       "verification_status": e.verification_status})
    for c in db.query(Claim).filter(Claim.case_id == case_id).all():
        nodes.append({"id": c.id, "type": "CLAIM", "label": c.text,
                       "verification_status": c.verification_status})
    for i in db.query(Issue).filter(Issue.case_id == case_id).all():
        nodes.append({"id": i.id, "type": "ISSUE", "label": i.question, "status": i.status})

    edges = []
    for r in db.query(EvidenceRelationship).filter(
        EvidenceRelationship.case_id == case_id, EvidenceRelationship.is_active == True  # noqa: E712
    ).all():
        edges.append({
            "id": r.id, "source": r.source_id, "target": r.target_id,
            "relationship_type": r.relationship_type, "support_kind": r.support_kind,
            "verification_status": r.verification_status,
        })

    return {"case_id": case_id, "nodes": nodes, "edges": edges}


@router.get("/cases/{case_id}/coverage")
def get_coverage(case_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    require_case_with_access(db, case_id, actor)
    return coverage_metrics(db, case_id)


@router.get("/cases/{case_id}/fragility")
def get_fragility(case_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    require_case_with_access(db, case_id, actor)
    return fragility_report(db, case_id)


@router.get("/cases/{case_id}/missing-evidence")
def get_missing_evidence(case_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    require_case_with_access(db, case_id, actor)
    return missing_evidence_report(db, case_id)
