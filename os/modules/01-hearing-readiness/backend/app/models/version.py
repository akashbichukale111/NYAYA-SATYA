from __future__ import annotations

from sqlalchemy import Column, String, ForeignKey, JSON, Integer
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.mixins import TimestampMixin, gen_id


class CaseVersion(Base, TimestampMixin):
    """
    Immutable snapshot of case readiness state. Never updated or deleted
    once written -- the Time Machine (section 15) diffs across these.
    """
    __tablename__ = "case_versions"

    id = Column(String, primary_key=True, default=lambda: gen_id("ver_snap"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    trigger = Column(String, nullable=False)  # what caused this snapshot, e.g. "readiness_audit", "action_verified"
    snapshot = Column(JSON, nullable=False)  # full serialized readiness+blockers+evidence state

    case = relationship("Case", back_populates="versions")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "version_number": self.version_number,
            "trigger": self.trigger,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
