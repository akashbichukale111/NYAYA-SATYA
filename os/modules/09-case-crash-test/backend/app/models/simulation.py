import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Boolean, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.enums import SimulationStatus


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SimulationScenario(Base):
    """
    A reusable, named definition of one or more mutations to apply.
    Structure mirrors the spec: preconditions / trigger / mutation(s) /
    (propagation + expected analysis are computed at run time, not stored
    here) / recovery hints.
    """
    __tablename__ = "simulation_scenarios"

    id = Column(String, primary_key=True, default=_uuid)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    preconditions = Column(JSON, default=dict)
    mutations = Column(JSON, nullable=False)  # list[{mutation_type, target_node_id, params}]
    is_technical_resilience_test = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_now)


class Simulation(Base):
    """
    A single run: base_snapshot + scenario -> simulated state + diff + impact.
    Never mutates the real case graph. `result` holds the full computed
    output (simulated_state, diff, blast_radius, failure_tree, recovery_options)
    so every simulation is fully reconstructable from stored data.
    """
    __tablename__ = "simulations"

    id = Column(String, primary_key=True, default=_uuid)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    base_snapshot_id = Column(String, ForeignKey("case_snapshots.id"), nullable=False)
    scenario_id = Column(String, ForeignKey("simulation_scenarios.id"), nullable=True)
    inline_scenario = Column(JSON, nullable=True)  # scenario passed ad hoc, not saved as reusable
    status = Column(String, default=SimulationStatus.PENDING.value)
    created_at = Column(DateTime, default=_now)
    created_by = Column(String, default="system")
    result = Column(JSON, nullable=True)
    human_review_required = Column(Boolean, default=False)
