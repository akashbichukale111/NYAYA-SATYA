"""
Contradiction Agent (section 13 / 25 #5).

Never assigns fraud, perjury, or guilt. It only records that two sources
disagree, with both sources shown, a confidence, and a possible
(non-accusatory) explanation such as "documents may refer to different
proceedings" or "one source may be outdated".
"""
from sqlalchemy.orm import Session

from app.models import ChangeProposal, Conflict, ConflictType, ReviewStatus
from app.agents.base import run_agent


def check_for_contradictions(db: Session, *, case_id: str, new_proposal: ChangeProposal, correlation_id: str) -> Conflict | None:
    with run_agent(db, case_id=case_id, agent_name="ContradictionAgent", correlation_id=correlation_id,
                    input_summary=f"proposal_id={new_proposal.id}") as result:
        # Look for another PENDING proposal on the same entity_type with a
        # materially different proposed_after value for a shared key field.
        candidates = (
            db.query(ChangeProposal)
            .filter(
                ChangeProposal.case_id == case_id,
                ChangeProposal.entity_type == new_proposal.entity_type,
                ChangeProposal.id != new_proposal.id,
                ChangeProposal.review_status == ReviewStatus.PENDING.value,
            )
            .all()
        )

        conflict_type_by_entity = {
            "deadline": ConflictType.DEADLINE_CONFLICT,
            "hearing": ConflictType.DATE_CONFLICT,
            "order": ConflictType.DOCUMENT_VERSION_CONFLICT,
            "obligation": ConflictType.STATUS_CONFLICT,
        }
        key_field_by_entity = {
            "deadline": "due_date", "hearing": "scheduled_date", "order": "summary", "obligation": "description",
        }

        key_field = key_field_by_entity.get(new_proposal.entity_type)
        if not key_field:
            result["output_summary"] = "no comparable key field for this entity type"
            return None

        for other in candidates:
            other_val = other.proposed_after.get(key_field)
            new_val = new_proposal.proposed_after.get(key_field)
            if other_val and new_val and other_val != new_val:
                conflict = Conflict(
                    case_id=case_id,
                    conflict_type=conflict_type_by_entity.get(new_proposal.entity_type, ConflictType.SOURCE_CONFLICT).value,
                    what_conflicts=(
                        f"Two pending proposals disagree on {new_proposal.entity_type}.{key_field}: "
                        f"'{other_val}' vs '{new_val}'."
                    ),
                    source_a_event_id=other.source_event_id,
                    source_b_event_id=new_proposal.source_event_id,
                    confidence=min(other.confidence, new_proposal.confidence),
                    possible_explanation=(
                        "The two source documents may refer to different stages of the same matter, "
                        "or one may supersede the other. Human review is required to determine which "
                        "applies; neither source is assumed correct."
                    ),
                    human_review_status="pending",
                )
                db.add(conflict)
                # Conflicting proposals both require human review, never auto-commit.
                other.requires_human_review = True
                new_proposal.requires_human_review = True
                db.commit()
                db.refresh(conflict)
                result["output_summary"] = f"conflict_id={conflict.id}"
                return conflict

        result["output_summary"] = "no contradiction found"
        return None
