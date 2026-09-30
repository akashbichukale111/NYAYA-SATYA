from __future__ import annotations

from sqlalchemy import Column, String, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.mixins import TimestampMixin, gen_id


class AuditEvent(Base, TimestampMixin):
    """
    Append-only audit log. Application code must only INSERT rows here,
    never UPDATE/DELETE (enforced by convention in audit_service.py --
    there is deliberately no update/delete function exposed).
    """
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True, default=lambda: gen_id("aud"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=True)
    actor = Column(String, nullable=False)  # "user:demo_user" / "agent:readiness_agent" / "system"
    event_type = Column(String, nullable=False)
    action = Column(String, nullable=False)
    input_ref = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    correlation_id = Column(String, nullable=False)

    case = relationship("Case", back_populates="audit_events")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "actor": self.actor,
            "event_type": self.event_type,
            "action": self.action,
            "input_ref": self.input_ref,
            "result": self.result,
            "correlation_id": self.correlation_id,
            "timestamp": self.created_at.isoformat() if self.created_at else None,
        }
