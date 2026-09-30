"""
Core domain model: the Universal Case Graph.

Design decision (documented, not hidden): rather than 20+ near-identical
subtype tables (Evidence, Claim, Issue, Obligation, Deadline, Hearing, Order,
FilingPackage, RegistryDefect, CustodyEvent, Workflow, Action, Verification...)
we implement ONE normalized graph of `CaseNode` (typed via `node_type`) and
`CaseRelationship` (typed via `rel_type`), with type-specific data carried in
a JSON `attributes` column. This is the same pattern real graph-backed legal
systems use, keeps the dependency/propagation engine generic, and lets new
node types be added without a migration. Conflicts, RegistryDefects, and
CustodyEvents are just `node_type` values with their own attribute shapes.

This is a deliberate simplification for Section 1. It does NOT reduce the
required taxonomy or relationship set — see app/enums.py — it only changes
*where* type-specific fields live (attributes JSON vs. dedicated columns).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, JSON, Text, Boolean, Integer
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.enums import NodeStatus


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Case(Base):
    __tablename__ = "cases"

    id = Column(String, primary_key=True, default=_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    nodes = relationship("CaseNode", back_populates="case", cascade="all, delete-orphan")
    relationships = relationship("CaseRelationship", back_populates="case", cascade="all, delete-orphan")
    snapshots = relationship("CaseSnapshot", back_populates="case", cascade="all, delete-orphan")


class CaseNode(Base):
    """
    A single node in the universal case graph.

    node_type: one of enums.NodeType (DOCUMENT, EVIDENCE, CLAIM, ISSUE,
    OBLIGATION, DEADLINE, HEARING, ORDER, FILING_PACKAGE, REGISTRY_DEFECT,
    CUSTODY_EVENT, WORKFLOW, ACTION, VERIFICATION)

    status: one of enums.NodeStatus — the REAL, current, production status.
    Simulations never write here; they operate on an in-memory clone.
    """
    __tablename__ = "case_nodes"

    id = Column(String, primary_key=True, default=_uuid)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    node_type = Column(String, nullable=False, index=True)
    label = Column(String, nullable=False)
    status = Column(String, default=NodeStatus.KNOWN.value, nullable=False)
    attributes = Column(JSON, default=dict)  # type-specific fields, source refs, provenance
    provenance_ref = Column(String, nullable=True)  # free-text pointer to originating source/doc
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    case = relationship("Case", back_populates="nodes")


class CaseRelationship(Base):
    """
    A directed, typed edge between two CaseNodes.

    rel_type: one of enums.RelationshipType.
    Direction convention: source --[rel_type]--> target.
    e.g. Claim --[DEPENDS_ON]--> Evidence
         Evidence --[SUPPORTS]--> Claim
    Both directions may be modeled explicitly; the propagation engine treats
    them symmetrically for blast-radius purposes (see app/graph/traversal.py).
    """
    __tablename__ = "case_relationships"

    id = Column(String, primary_key=True, default=_uuid)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    source_id = Column(String, ForeignKey("case_nodes.id"), nullable=False, index=True)
    target_id = Column(String, ForeignKey("case_nodes.id"), nullable=False, index=True)
    rel_type = Column(String, nullable=False, index=True)
    attributes = Column(JSON, default=dict)
    created_at = Column(DateTime, default=_now)

    case = relationship("Case", back_populates="relationships")


class CaseSnapshot(Base):
    """
    An immutable, point-in-time capture of the full graph (nodes + relationships)
    for a case. Snapshots are the ONLY thing simulations are allowed to read as
    their base state. `data` is a serialized graph: {"nodes": [...], "relationships": [...]}.
    """
    __tablename__ = "case_snapshots"

    id = Column(String, primary_key=True, default=_uuid)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    label = Column(String, nullable=True)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=_now)
    created_by = Column(String, default="system")

    case = relationship("Case", back_populates="snapshots")


class ReviewTask(Base):
    """
    A human-review item raised by a simulation. Approving/rejecting a
    ReviewTask never itself mutates the real case graph in Section 1 —
    consequential application is a governed, explicit action reserved for
    Section 2 (Human Legal Gate).
    """
    __tablename__ = "review_tasks"

    id = Column(String, primary_key=True, default=_uuid)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    simulation_id = Column(String, ForeignKey("simulations.id"), nullable=True, index=True)
    node_id = Column(String, nullable=True)
    reason = Column(Text, nullable=False)
    status = Column(String, default="PENDING", nullable=False)
    created_at = Column(DateTime, default=_now)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, nullable=True)


class User(Base):
    """
    Minimal user record for attribution and RBAC. No auth/session handling
    lives here yet — see app/rbac.py for what is actually enforced today.
    """
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    role = Column(String, default="ANALYST", nullable=False)
    created_at = Column(DateTime, default=_now)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True, default=_uuid)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    actor = Column(String, default="system")
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=_now)
