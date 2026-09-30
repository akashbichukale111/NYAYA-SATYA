from __future__ import annotations

from sqlalchemy import Column, String, JSON
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.mixins import TimestampMixin, gen_id


class Case(Base, TimestampMixin):
    """
    The Case Digital Twin's root record. All other domain objects hang off
    this via case_id foreign keys. This is the SINGLE source of truth for
    case state -- services read/write through it rather than each agent
    keeping its own copy.
    """
    __tablename__ = "cases"

    id = Column(String, primary_key=True, default=lambda: gen_id("case"))
    title = Column(String, nullable=False)
    case_type = Column(String, nullable=False)  # e.g. "civil", "criminal", "writ"
    current_stage = Column(String, nullable=False, default="UNKNOWN")
    parties = Column(JSON, default=list)  # list[{name, role}]
    is_synthetic = Column(String, default="true")  # "true"/"false" -- demo-data flag

    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    evidence_items = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")
    hearings = relationship("Hearing", back_populates="case", cascade="all, delete-orphan")
    requirements = relationship("Requirement", back_populates="case", cascade="all, delete-orphan")
    blockers = relationship("Blocker", back_populates="case", cascade="all, delete-orphan")
    actions = relationship("Action", back_populates="case", cascade="all, delete-orphan")
    versions = relationship("CaseVersion", back_populates="case", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="case", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "case_type": self.case_type,
            "current_stage": self.current_stage,
            "parties": self.parties,
            "is_synthetic": self.is_synthetic,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
