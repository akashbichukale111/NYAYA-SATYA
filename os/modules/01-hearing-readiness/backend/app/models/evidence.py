from __future__ import annotations

from sqlalchemy import Column, String, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.mixins import TimestampMixin, gen_id


class Evidence(Base, TimestampMixin):
    """
    A discrete piece of evidence (may be derived from a Document, or
    logged as an event e.g. 'service affidavit filed'). Kept separate
    from Document because one document can yield several evidence items,
    and evidence can also exist without a source file (e.g. a court order
    entry recorded from the case docket).
    """
    __tablename__ = "evidence"

    id = Column(String, primary_key=True, default=lambda: gen_id("evi"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    document_id = Column(String, ForeignKey("documents.id"), nullable=True)

    label = Column(String, nullable=False)
    evidence_type = Column(String, nullable=False)  # document/affidavit/order/service_record/other
    availability = Column(String, nullable=False, default="UNKNOWN")  # AVAILABLE/MISSING/PARTIAL/UNKNOWN
    verification_state = Column(String, nullable=False, default="UNVERIFIED")  # VERIFIED/UNVERIFIED/DISPUTED
    page_ref = Column(String, nullable=True)
    confidence = Column(String, nullable=False, default="UNKNOWN")  # HIGH/MEDIUM/LOW/UNKNOWN
    notes = Column(JSON, default=list)

    case = relationship("Case", back_populates="evidence_items")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "document_id": self.document_id,
            "label": self.label,
            "evidence_type": self.evidence_type,
            "availability": self.availability,
            "verification_state": self.verification_state,
            "page_ref": self.page_ref,
            "confidence": self.confidence,
            "notes": self.notes,
        }
