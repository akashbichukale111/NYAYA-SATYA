"""
Verification Agent.

Recommends (never applies) a VERIFIED status for claims that have at
least one supporting evidence item with a known source location and no
open contradiction. Missing evidence prevents a claim from becoming
verified -- claims with no support are simply skipped, never
force-verified. Every recommendation goes through the Human Legal Gate
via review_service.propose_action; this agent has no authority to
change verification_status directly.
"""
from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.orm import Claim, EvidenceItem
from app.models.enums import VerificationStatus
from app.services.graph_service import DependencyGraph
from app.services.review_service import propose_action


def recommend_verifications(db: Session, case_id: str, actor_id: str = "VerificationAgent") -> Dict:
    graph = DependencyGraph(db, case_id)
    claims = db.query(Claim).filter(Claim.case_id == case_id).all()
    review_task_ids: List[str] = []

    for claim in claims:
        if claim.verification_status == VerificationStatus.VERIFIED.value:
            continue

        support_edges = graph.support_edges_for("CLAIM", claim.id)
        contradiction_edges = graph.contradiction_edges_for("CLAIM", claim.id)
        if not support_edges:
            continue  # missing evidence -- never becomes a verification candidate
        if contradiction_edges:
            continue  # open contradiction -- requires resolution first, not verification

        has_known_location = False
        for edge in support_edges:
            if edge.source_type != "EVIDENCE":
                continue
            ev = db.query(EvidenceItem).filter(EvidenceItem.id == edge.source_id).first()
            if ev and ev.source_location_known:
                has_known_location = True
                break
        if not has_known_location:
            continue

        task = propose_action(
            db, case_id, action_type="CHANGE_VERIFIED_STATUS", target_type="CLAIM",
            target_id=claim.id,
            proposed_change={"verification_status": VerificationStatus.VERIFIED.value},
            proposing_agent="VerificationAgent",
        )
        review_task_ids.append(task.id)

    return {"ok": True, "review_task_ids": review_task_ids}
