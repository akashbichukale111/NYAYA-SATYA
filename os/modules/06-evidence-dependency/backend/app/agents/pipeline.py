"""
Pipeline orchestrator: Document -> Evidence -> Claim -> Issue.

Runs the agent boundaries in sequence over one already-ingested document.
Each step's output is structured and audited. No step has unrestricted
authority: extraction and claim discovery only ever create new, additive,
UNVERIFIED/REQUIRES_HUMAN_REVIEW data; issue mapping and verification
recommendations are proposed through the Human Legal Gate and require a
human decision before they take effect.
"""
from typing import Dict

from sqlalchemy.orm import Session

from app.agents import (
    evidence_intake_agent,
    evidence_extraction_agent,
    claim_discovery_agent,
    issue_mapping_agent,
    relationship_agent,
    contradiction_agent,
    verification_agent,
    dependency_agent,
)
from app.services.review_service import log_audit_event


def run_pipeline(db: Session, case_id: str, document_id: str, actor_id: str = "Pipeline") -> Dict:
    intake_result = evidence_intake_agent.check_intake(db, document_id)
    if not intake_result.get("ok"):
        return {"ok": False, "step": "intake", "result": intake_result}

    extraction_result = evidence_extraction_agent.extract_evidence(db, document_id, actor_id)
    evidence_ids = extraction_result.get("evidence_ids", [])

    claim_result = claim_discovery_agent.discover_claims(db, case_id, evidence_ids, actor_id)
    claim_ids = claim_result.get("claim_ids", [])

    mapping_result = issue_mapping_agent.propose_mappings(db, case_id, claim_ids, actor_id)
    relationship_result = relationship_agent.classify_support(db, case_id, actor_id)
    contradiction_result = contradiction_agent.detect_contradictions(db, case_id, actor_id)
    verification_result = verification_agent.recommend_verifications(db, case_id, actor_id)
    dependency_result = dependency_agent.report(db, case_id)

    summary = {
        "ok": True,
        "document_id": document_id,
        "case_id": case_id,
        "evidence_created": evidence_ids,
        "claims_created": claim_ids,
        "issue_mapping_review_tasks": mapping_result.get("review_task_ids", []),
        "relationships_upgraded": relationship_result.get("upgraded_relationship_ids", []),
        "conflicts_flagged": contradiction_result.get("conflict_ids", []),
        "verification_review_tasks": verification_result.get("review_task_ids", []),
        "coverage_after": dependency_result["coverage"],
    }

    log_audit_event(
        db, case_id, actor="Pipeline", actor_type="AGENT", action="PIPELINE_RUN_COMPLETE",
        target_type="DOCUMENT", target_id=document_id, detail=summary,
    )
    db.commit()
    return summary
