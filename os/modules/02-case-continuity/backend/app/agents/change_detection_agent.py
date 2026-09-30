"""
Change Detection Agent (section 10 / 25 #3).

Looks at a new extraction Event plus the case's current twin state and
decides: is this genuinely new, a duplicate, a contradiction, an update, a
correction, stale, ambiguous, unrelated, or does it require human review?

Output: a list of ChangeProposal rows (never a direct write to the twin).
"""
from sqlalchemy.orm import Session

from app.models import Event, Deadline, Order, ChangeProposal, ChangeNature, ReviewStatus, ItemStatus
from app.state_twin import build_snapshot
from app.agents.base import run_agent


def _confidence_bucket(confidence: float) -> bool:
    """Return True if confidence is high enough to be eligible for auto-review."""
    return confidence >= 0.75


def detect_changes(db: Session, *, case_id: str, extraction_event: Event, correlation_id: str) -> list[ChangeProposal]:
    with run_agent(db, case_id=case_id, agent_name="ChangeDetectionAgent", correlation_id=correlation_id,
                    input_summary=f"event_id={extraction_event.event_id}") as result:
        facts = extraction_event.structured_payload.get("extraction", {})
        signals = facts.get("signals", {}) or {}
        confidence = float(facts.get("confidence", 0.5))
        raw_dates = facts.get("raw_dates_found", []) or []
        snapshot = build_snapshot(db, case_id)
        proposals: list[ChangeProposal] = []

        # --- Deadline-related signal -----------------------------------
        if signals.get("deadline") and raw_dates:
            new_date = raw_dates[0]
            existing_open = [d for d in db.query(Deadline).filter(
                Deadline.case_id == case_id, Deadline.status == ItemStatus.OPEN.value).all()]

            if not existing_open:
                nature = ChangeNature.NEW
                before, after = {}, {"label": "Filing/response deadline", "due_date": new_date,
                                      "status": ItemStatus.OPEN.value}
            else:
                target = existing_open[0]
                if target.due_date == new_date:
                    nature = ChangeNature.DUPLICATE
                    before = after = {"label": target.label, "due_date": target.due_date, "status": target.status}
                else:
                    nature = ChangeNature.UPDATE
                    before = {"id": target.id, "label": target.label, "due_date": target.due_date,
                              "status": target.status}
                    after = {"id": target.id, "label": target.label, "due_date": new_date,
                             "status": ItemStatus.OPEN.value}

            requires_review = nature != ChangeNature.DUPLICATE and not (
                nature == ChangeNature.NEW and _confidence_bucket(confidence)
            )
            proposals.append(ChangeProposal(
                case_id=case_id, source_event_id=extraction_event.event_id,
                nature=nature.value, entity_type="deadline",
                proposed_before=before, proposed_after=after,
                reason=f"Detected deadline-related language with date token(s) {raw_dates} "
                       f"(confidence {confidence:.2f}).",
                confidence=confidence,
                requires_human_review=requires_review,
                review_status=ReviewStatus.PENDING.value if requires_review else ReviewStatus.PENDING.value,
            ))

        # --- Order-related signal ----------------------------------------
        if signals.get("order"):
            existing_orders = snapshot.get("orders", {})
            nature = ChangeNature.NEW if not existing_orders else ChangeNature.UPDATE
            proposals.append(ChangeProposal(
                case_id=case_id, source_event_id=extraction_event.event_id,
                nature=nature.value, entity_type="order",
                proposed_before={},
                proposed_after={"order_date": raw_dates[0] if raw_dates else "", "summary": facts.get("excerpt", "")[:200],
                                 "status": ItemStatus.OPEN.value},
                reason=f"Detected court-order language (confidence {confidence:.2f}).",
                confidence=confidence,
                requires_human_review=not _confidence_bucket(confidence),
            ))

        # --- Obligation-related signal -------------------------------------
        if signals.get("obligation"):
            proposals.append(ChangeProposal(
                case_id=case_id, source_event_id=extraction_event.event_id,
                nature=ChangeNature.NEW.value, entity_type="obligation",
                proposed_before={},
                proposed_after={"description": facts.get("excerpt", "")[:200], "owner_party": "unassigned",
                                 "status": ItemStatus.OPEN.value},
                reason=f"Detected obligation-creating language (confidence {confidence:.2f}).",
                confidence=confidence,
                requires_human_review=True,  # new obligations always reviewed - high impact
            ))

        # --- Hearing-related signal ------------------------------------
        if signals.get("hearing"):
            proposals.append(ChangeProposal(
                case_id=case_id, source_event_id=extraction_event.event_id,
                nature=ChangeNature.NEW.value, entity_type="hearing",
                proposed_before={},
                proposed_after={"scheduled_date": raw_dates[0] if raw_dates else "", "occurred": False,
                                 "status": ItemStatus.OPEN.value},
                reason=f"Detected hearing-listing language (confidence {confidence:.2f}).",
                confidence=confidence,
                requires_human_review=not _confidence_bucket(confidence),
            ))

        if not proposals:
            proposals.append(ChangeProposal(
                case_id=case_id, source_event_id=extraction_event.event_id,
                nature=ChangeNature.AMBIGUOUS.value, entity_type="unclassified",
                proposed_before={}, proposed_after={"excerpt": facts.get("excerpt", "")},
                reason="No strong structural signal matched known change categories.",
                confidence=confidence, requires_human_review=True,
            ))

        for p in proposals:
            db.add(p)
        db.commit()
        for p in proposals:
            db.refresh(p)

        result["output_summary"] = f"{len(proposals)} proposal(s): " + ", ".join(p.nature for p in proposals)
        return proposals
