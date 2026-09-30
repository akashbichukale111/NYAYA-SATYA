from __future__ import annotations

from sqlalchemy import Column, String, ForeignKey, JSON
from app.db import Base
from app.models.mixins import TimestampMixin, gen_id


class Simulation(Base, TimestampMixin):
    """
    Record of a what-if run. The simulated state is NEVER written back
    into the case's live tables -- only this record is persisted, purely
    for audit/history of "what was asked". See services/simulation_engine.py.
    """
    __tablename__ = "simulations"

    id = Column(String, primary_key=True, default=lambda: gen_id("sim"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    hypothesis = Column(JSON, nullable=False)  # list of hypothetical steps applied
    baseline_readiness = Column(JSON, nullable=False)
    simulated_readiness = Column(JSON, nullable=False)
    diff = Column(JSON, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "hypothesis": self.hypothesis,
            "baseline_readiness": self.baseline_readiness,
            "simulated_readiness": self.simulated_readiness,
            "diff": self.diff,
            "label": "SIMULATION ONLY",
        }
