from __future__ import annotations

from sqlalchemy import Column, String, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.mixins import TimestampMixin, gen_id


class Blocker(Base, TimestampMixin):
    __tablename__ = "blockers"

    id = Column(String, primary_key=True, default=lambda: gen_id("blk"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    requirement_id = Column(String, ForeignKey("requirements.id"), nullable=False)

    description = Column(String, nullable=False)
    category = Column(String, nullable=False)
    severity = Column(String, nullable=False, default="MEDIUM")  # LOW/MEDIUM/HIGH/CRITICAL
    evidence_refs = Column(JSON, default=list)
    dependent_requirements = Column(JSON, default=list)  # requirement ids downstream of this blocker
    downstream_impact = Column(String, nullable=False)  # explanation of why it matters for THIS hearing
    responsible_actor = Column(String, nullable=True)
    deadline = Column(String, nullable=True)
    status = Column(String, nullable=False, default="OPEN")  # OPEN/RESOLVED/SIMULATED_RESOLVED
    confidence = Column(String, nullable=False, default="MEDIUM")
    suggested_safe_action = Column(String, nullable=True)
    history = Column(JSON, default=list)  # [{event, timestamp}]

    case = relationship("Case", back_populates="blockers")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "requirement_id": self.requirement_id,
            "description": self.description,
            "category": self.category,
            "severity": self.severity,
            "evidence_refs": self.evidence_refs,
            "dependent_requirements": self.dependent_requirements,
            "downstream_impact": self.downstream_impact,
            "responsible_actor": self.responsible_actor,
            "deadline": self.deadline,
            "status": self.status,
            "confidence": self.confidence,
            "suggested_safe_action": self.suggested_safe_action,
            "history": self.history,
        }


class Dependency(Base, TimestampMixin):
    """An explicit graph edge, kept as rows so the causal graph is queryable
    and every edge carries its own provenance reason (section 8)."""
    __tablename__ = "dependencies"

    id = Column(String, primary_key=True, default=lambda: gen_id("dep"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    from_node_type = Column(String, nullable=False)  # HEARING/REQUIREMENT/EVIDENCE/BLOCKER/ACTOR/ACTION/VERIFICATION/STATE
    from_node_id = Column(String, nullable=False)
    to_node_type = Column(String, nullable=False)
    to_node_id = Column(String, nullable=False)
    reason = Column(String, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "from": {"type": self.from_node_type, "id": self.from_node_id},
            "to": {"type": self.to_node_type, "id": self.to_node_id},
            "reason": self.reason,
        }
