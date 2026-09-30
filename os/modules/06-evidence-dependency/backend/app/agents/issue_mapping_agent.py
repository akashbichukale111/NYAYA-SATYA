"""
Issue Mapping Agent.

Maps claims to existing case issues. This is listed explicitly in the
master spec as a Human Legal Gate action ("approve issue mapping"), so
this agent never creates the Claim->Issue edge directly -- it always
proposes it via the review queue and a human/advocate must approve it
before the mapping becomes an active relationship in the graph.
"""
from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.orm import Claim, Issue
from app.models.enums import RelationshipType
from app.services.review_service import propose_relationship


def propose_mappings(db: Session, case_id: str, claim_ids: List[str],
                      actor_id: str = "IssueMappingAgent") -> Dict:
    open_issues = db.query(Issue).filter(Issue.case_id == case_id, Issue.status == "OPEN").all()
    if not open_issues:
        return {"ok": True, "review_task_ids": [], "reason": "No open issues in this case to map to."}

    review_task_ids: List[str] = []
    for cid in claim_ids:
        claim = db.query(Claim).filter(Claim.id == cid, Claim.case_id == case_id).first()
        if not claim:
            continue
        # Deterministic, explainable heuristic: map to the first open issue
        # whose question shares a word (length > 3) with the claim text.
        claim_words = {w.lower() for w in claim.text.split() if len(w) > 3}
        best = None
        for issue in open_issues:
            issue_words = {w.lower() for w in issue.question.split() if len(w) > 3}
            if claim_words & issue_words:
                best = issue
                break
        target_issue = best or open_issues[0]

        task = propose_relationship(
            db, case_id, source_type="CLAIM", source_id=claim.id,
            target_type="ISSUE", target_id=target_issue.id,
            relationship_type=RelationshipType.REQUIRES.value,
            explanation=f"Proposed mapping: claim shares vocabulary with issue '{target_issue.question}'."
            if best else "No vocabulary overlap found; proposed default mapping to first open issue.",
            action_type="APPROVE_ISSUE_MAPPING",
            proposing_agent="IssueMappingAgent",
        )
        review_task_ids.append(task.id)

    return {"ok": True, "review_task_ids": review_task_ids}
