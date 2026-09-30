from __future__ import annotations

from sqlalchemy import Column, String, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.mixins import TimestampMixin, gen_id


class Verification(Base, TimestampMixin):
    __tablename__ = "verifications"

    id = Column(String, primary_key=True, default=lambda: gen_id("ver"))
    action_id = Column(String, ForeignKey("actions.id"), nullable=False, unique=True)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)

    checks = Column(JSON, default=list)  # [{check_name, expected, observed, passed}]
    result = Column(String, nullable=False, default="PENDING")  # PASSED/VERIFICATION_FAILED/PENDING
    explanation = Column(String, nullable=True)

    action = relationship("Action", back_populates="verification")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action_id": self.action_id,
            "case_id": self.case_id,
            "checks": self.checks,
            "result": self.result,
            "explanation": self.explanation,
        }
