from __future__ import annotations

from sqlalchemy import Column, String, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.mixins import TimestampMixin, gen_id


class Action(Base, TimestampMixin):
    """
    An AI-proposed safe action. Nothing consequential runs until an
    Approval record with decision=APPROVE exists (enforced in the
    action_planner/verification services, not just in the UI).
    """
    __tablename__ = "actions"

    id = Column(String, primary_key=True, default=lambda: gen_id("act"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    blocker_id = Column(String, ForeignKey("blockers.id"), nullable=True)

    action_type = Column(String, nullable=False)  # e.g. "prepare_checklist", "draft_reminder", "mark_evidence_reviewed"
    description = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    evidence_refs = Column(JSON, default=list)
    risk = Column(String, nullable=False, default="LOW")
    affected_case_state = Column(JSON, default=list)
    expected_effect = Column(String, nullable=False)
    unknowns = Column(JSON, default=list)

    status = Column(String, nullable=False, default="PENDING_APPROVAL")
    # PENDING_APPROVAL / APPROVED / REJECTED / EDITED / EXECUTED / VERIFICATION_FAILED / VERIFIED

    result = Column(JSON, nullable=True)

    case = relationship("Case", back_populates="actions")
    approval = relationship("Approval", back_populates="action", uselist=False, cascade="all, delete-orphan")
    verification = relationship("Verification", back_populates="action", uselist=False, cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "blocker_id": self.blocker_id,
            "action_type": self.action_type,
            "description": self.description,
            "reason": self.reason,
            "evidence_refs": self.evidence_refs,
            "risk": self.risk,
            "affected_case_state": self.affected_case_state,
            "expected_effect": self.expected_effect,
            "unknowns": self.unknowns,
            "status": self.status,
            "result": self.result,
        }


class Approval(Base, TimestampMixin):
    __tablename__ = "approvals"

    id = Column(String, primary_key=True, default=lambda: gen_id("apr"))
    action_id = Column(String, ForeignKey("actions.id"), nullable=False, unique=True)
    decision = Column(String, nullable=False)  # APPROVE/EDIT/REJECT
    approved_by = Column(String, nullable=False, default="demo_user")
    edited_description = Column(String, nullable=True)
    notes = Column(String, nullable=True)

    action = relationship("Action", back_populates="approval")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action_id": self.action_id,
            "decision": self.decision,
            "approved_by": self.approved_by,
            "edited_description": self.edited_description,
            "notes": self.notes,
        }
