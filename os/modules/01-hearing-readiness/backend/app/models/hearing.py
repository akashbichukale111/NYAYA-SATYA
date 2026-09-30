from __future__ import annotations

from sqlalchemy import Column, String, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.mixins import TimestampMixin, gen_id


class Hearing(Base, TimestampMixin):
    __tablename__ = "hearings"

    id = Column(String, primary_key=True, default=lambda: gen_id("hrg"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)

    hearing_date = Column(DateTime, nullable=True)
    is_next = Column(String, default="false")
    purpose = Column(String, nullable=True)  # null if uncertain
    purpose_status = Column(String, default="UNCERTAIN")  # DETERMINED/UNCERTAIN
    uncertainty_reasons = Column(JSON, default=list)
    stage_at_hearing = Column(String, nullable=True)
    known_orders_ref = Column(JSON, default=list)
    known_applications_ref = Column(JSON, default=list)

    case = relationship("Case", back_populates="hearings")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "hearing_date": self.hearing_date.isoformat() if self.hearing_date else None,
            "is_next": self.is_next,
            "purpose": self.purpose,
            "purpose_status": self.purpose_status,
            "uncertainty_reasons": self.uncertainty_reasons,
            "stage_at_hearing": self.stage_at_hearing,
        }
