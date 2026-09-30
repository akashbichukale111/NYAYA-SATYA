from __future__ import annotations

from sqlalchemy import Column, String, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.mixins import TimestampMixin, gen_id

# Fixed, explainable categories -- NOT an arbitrary single score.
READINESS_CATEGORIES = (
    "DOCUMENTS", "PROCEDURE", "SERVICE", "EVIDENCE",
    "APPLICATIONS", "ORDERS", "DEADLINES",
)


class Requirement(Base, TimestampMixin):
    """
    A single readiness condition inside a category, e.g.
    'service affidavit filed for defendant 2'.
    """
    __tablename__ = "requirements"

    id = Column(String, primary_key=True, default=lambda: gen_id("req"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    hearing_id = Column(String, ForeignKey("hearings.id"), nullable=True)

    category = Column(String, nullable=False)  # one of READINESS_CATEGORIES
    description = Column(String, nullable=False)
    status = Column(String, nullable=False, default="UNKNOWN")  # SATISFIED/UNRESOLVED/UNKNOWN
    reason = Column(String, nullable=False)
    evidence_refs = Column(JSON, default=list)  # list of evidence ids
    confidence = Column(String, nullable=False, default="UNKNOWN")
    responsible_actor = Column(String, nullable=True)
    recommended_next_step = Column(String, nullable=True)

    case = relationship("Case", back_populates="requirements")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "hearing_id": self.hearing_id,
            "category": self.category,
            "description": self.description,
            "status": self.status,
            "reason": self.reason,
            "evidence_refs": self.evidence_refs,
            "confidence": self.confidence,
            "responsible_actor": self.responsible_actor,
            "recommended_next_step": self.recommended_next_step,
        }
