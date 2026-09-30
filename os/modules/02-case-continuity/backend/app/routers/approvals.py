from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Case, ChangeProposal
from app.agents.orchestrator import review_proposal

router = APIRouter(prefix="/api/cases", tags=["approvals"])


class ReviewDecision(BaseModel):
    decision: str  # "approve" | "edit" | "reject"
    reviewer: str = "user"
    edited_after: dict | None = None


@router.get("/{case_id}/proposals")
def list_proposals(case_id: str, status: str | None = None, db: Session = Depends(get_db)):
    if not db.get(Case, case_id):
        raise HTTPException(404, "case not found")
    q = db.query(ChangeProposal).filter(ChangeProposal.case_id == case_id)
    if status:
        q = q.filter(ChangeProposal.review_status == status)
    proposals = q.order_by(ChangeProposal.created_at.desc()).all()
    return [
        {
            "id": p.id, "source_event_id": p.source_event_id, "nature": p.nature, "entity_type": p.entity_type,
            "proposed_before": p.proposed_before, "proposed_after": p.proposed_after, "reason": p.reason,
            "confidence": p.confidence, "requires_human_review": p.requires_human_review,
            "review_status": p.review_status, "reviewer": p.reviewer,
            "resulting_version_number": p.resulting_version_number, "created_at": p.created_at.isoformat(),
        }
        for p in proposals
    ]


@router.post("/{case_id}/proposals/{proposal_id}/review")
def review(case_id: str, proposal_id: str, payload: ReviewDecision, db: Session = Depends(get_db)):
    proposal = db.get(ChangeProposal, proposal_id)
    if not proposal or proposal.case_id != case_id:
        raise HTTPException(404, "proposal not found")
    if proposal.review_status not in ("pending",):
        raise HTTPException(400, f"proposal already {proposal.review_status}")
    if payload.decision not in ("approve", "edit", "reject"):
        raise HTTPException(400, "decision must be approve, edit, or reject")

    result = review_proposal(
        db, proposal=proposal, decision=payload.decision, reviewer=payload.reviewer,
        edited_after=payload.edited_after,
    )
    return result
