"""
Impact Analysis + Evidence Crash Test.

CRITICAL SAFETY PROPERTY: crash tests are simulations. They compute a
before/after state by reasoning over the existing graph in memory and
persist only a CrashTestRun record. They never mutate EvidenceItem,
Claim, Issue or EvidenceRelationship rows. Any real, destructive change
to case data must go through the Human Legal Gate (review_service).
"""
import uuid
from datetime import datetime
from typing import Dict

from sqlalchemy.orm import Session

from app.models.orm import EvidenceItem, Claim, Issue, CrashTestRun
from app.models.enums import CrashTestEventType, CriticalityLevel
from app.services.graph_service import DependencyGraph, coverage_metrics


def compute_impact(db: Session, case_id: str, node_type: str, node_id: str) -> Dict:
    """Real-time impact query: what depends on this node right now."""
    graph = DependencyGraph(db, case_id)
    impact = graph.downstream_impact(node_type, node_id)

    affected_claims = impact["affected_claims"]
    single_point = False
    for cid in affected_claims:
        if graph.independent_source_count("CLAIM", cid) == 1:
            single_point = True
            break

    total = len(affected_claims) + len(impact["affected_issues"])
    if total == 0:
        criticality = CriticalityLevel.NONE.value
    elif single_point:
        criticality = CriticalityLevel.SINGLE_POINT_DEPENDENCY.value
    elif total >= 3:
        criticality = CriticalityLevel.MODERATE.value
    else:
        criticality = CriticalityLevel.LOW.value

    return {
        "node_type": node_type,
        "node_id": node_id,
        "affected_claims": affected_claims,
        "affected_issues": impact["affected_issues"],
        "criticality": criticality,
        "human_review_required": criticality != CriticalityLevel.NONE.value,
    }


def run_crash_test(
    db: Session,
    case_id: str,
    event_type: str,
    target_type: str,
    target_id: str,
    created_by: str = "SYSTEM",
) -> CrashTestRun:
    """
    Simulate one of the supported crash-test events and persist the
    result as an auditable, non-destructive CrashTestRun row.
    """
    before_coverage = coverage_metrics(db, case_id)
    impact = compute_impact(db, case_id, target_type, target_id)

    new_gaps = []
    new_conflicts = []

    if event_type in (
        CrashTestEventType.REMOVE_EVIDENCE.value,
        CrashTestEventType.EXCLUDE_EVIDENCE.value,
        CrashTestEventType.REMOVE_SOURCE_DOCUMENT.value,
        CrashTestEventType.INVALIDATE_PROVENANCE.value,
        CrashTestEventType.BREAK_CLAIM_DEPENDENCY.value,
    ):
        for cid in impact["affected_claims"]:
            new_gaps.append({"type": "CLAIM_LOSES_ALL_SUPPORT_CANDIDATE", "claim_id": cid})
        for iid in impact["affected_issues"]:
            new_gaps.append({"type": "ISSUE_LOSES_SUPPORTING_CLAIM_CANDIDATE", "issue_id": iid})

    elif event_type == CrashTestEventType.INTRODUCE_CONTRADICTORY_EVIDENCE.value:
        new_conflicts.append({
            "type": "SIMULATED_CONTRADICTION",
            "target_type": target_type,
            "target_id": target_id,
        })

    elif event_type == CrashTestEventType.MARK_UNVERIFIED.value:
        new_gaps.append({
            "type": "SUPPORT_DOWNGRADED_TO_UNVERIFIED",
            "target_type": target_type,
            "target_id": target_id,
        })

    elif event_type == CrashTestEventType.REVERSE_RELATIONSHIP.value:
        new_conflicts.append({
            "type": "RELATIONSHIP_DIRECTION_REVERSED_SIMULATION",
            "target_type": target_type,
            "target_id": target_id,
        })

    elif event_type == CrashTestEventType.SUPERSEDE_DOCUMENT.value:
        new_gaps.append({
            "type": "DOCUMENT_SUPERSEDED_DOWNSTREAM_REVIEW_NEEDED",
            "target_type": target_type,
            "target_id": target_id,
        })

    elif event_type == CrashTestEventType.CREATE_MISSING_EVIDENCE.value:
        new_gaps.append({
            "type": "SIMULATED_MISSING_EVIDENCE",
            "target_type": target_type,
            "target_id": target_id,
        })

    after_coverage = dict(before_coverage)
    after_coverage["claims_without_evidence"] = before_coverage["claims_without_evidence"] + len(
        [g for g in new_gaps if g["type"].startswith("CLAIM")]
    )
    after_coverage["unsupported_issues"] = before_coverage["unsupported_issues"] + len(
        [g for g in new_gaps if g["type"].startswith("ISSUE")]
    )

    run = CrashTestRun(
        id=str(uuid.uuid4()),
        case_id=case_id,
        event_type=event_type,
        target_type=target_type,
        target_id=target_id,
        before_state={"coverage": before_coverage, "impact": impact},
        after_state={"coverage": after_coverage},
        affected_claims=impact["affected_claims"],
        affected_issues=impact["affected_issues"],
        new_gaps=new_gaps,
        new_conflicts=new_conflicts,
        criticality=impact["criticality"],
        human_review_required=True,  # crash test outputs always require human review before acting
        created_by=created_by,
        created_at=datetime.utcnow(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
