from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.rbac import Actor, get_actor
from app.core.case_access import require_case_with_access
from app.models.orm import Case, EvidenceItem, Claim, Issue, ReviewTask
from app.schemas.schemas import IntegrationSummary
from app.services.graph_service import coverage_metrics, fragility_report

router = APIRouter()


@router.get("/cases/{case_id}/integration-summary", response_model=IntegrationSummary)
def integration_summary(case_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    """
    Stable, minimal summary contract for downstream NYAYA-SATYA modules
    (Case Bottleneck Engine, Hearing Readiness Engine, TARKA-VYUH, etc).
    This project stays independently runnable -- nothing here imports
    from or depends on any NYAYA-SATYA internals.
    """
    case = require_case_with_access(db, case_id, actor)

    coverage = coverage_metrics(db, case_id)
    fragility = fragility_report(db, case_id)
    critical = [f for f in fragility if f["criticality"] == "SINGLE_POINT_DEPENDENCY"]
    pending_reviews = db.query(ReviewTask).filter(
        ReviewTask.case_id == case_id, ReviewTask.status == "PENDING"
    ).count()
    verification_pending = db.query(EvidenceItem).filter(
        EvidenceItem.case_id == case_id, EvidenceItem.verification_status != "VERIFIED"
    ).count()
    provenance_refs = [
        e.id for e in db.query(EvidenceItem).filter(
            EvidenceItem.case_id == case_id, EvidenceItem.source_location_known == True  # noqa: E712
        ).all()
    ]

    attention_items = []
    for f in critical:
        attention_items.append({
            "type": "SINGLE_POINT_DEPENDENCY_EVIDENCE",
            "evidence_id": f["evidence_id"],
            "affected_claims": f["affected_claims"],
            "affected_issues": f["affected_issues"],
        })
    if pending_reviews:
        attention_items.append({"type": "PENDING_HUMAN_REVIEW", "count": pending_reviews})

    return IntegrationSummary(
        case_id=case_id,
        evidence_count=coverage["evidence_items_total"],
        claim_count=coverage["claims_total"],
        issue_count=coverage["issues_total"],
        unsupported_claims=coverage["claims_without_evidence"],
        unsupported_issues=coverage["unsupported_issues"],
        conflicting_claims=coverage["conflicting_claims"],
        critical_dependencies=critical,
        impact_items=fragility[:10],
        verification_pending=verification_pending,
        provenance_refs=provenance_refs,
        attention_items=attention_items,
        last_updated=datetime.utcnow().isoformat(),
    )
