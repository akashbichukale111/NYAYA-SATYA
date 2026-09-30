from __future__ import annotations

from sqlalchemy import Column, String, ForeignKey, JSON
from app.db import Base
from app.models.mixins import TimestampMixin, gen_id


class CrashTest(Base, TimestampMixin):
    """
    Adversarial mutation test result. Always run against an in-memory
    CLONE of case state -- see services/crash_test_engine.py -- so real
    evidence is never destructively mutated (section 16).
    """
    __tablename__ = "crash_tests"

    id = Column(String, primary_key=True, default=lambda: gen_id("cts"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    mutation = Column(String, nullable=False)
    expected_effect = Column(String, nullable=False)
    observed_effect = Column(String, nullable=False)
    passed = Column(String, nullable=False)  # "true"/"false"
    explanation = Column(String, nullable=False)
    impacted_state = Column(JSON, default=list)
    regression_status = Column(String, nullable=False, default="NOT_APPLICABLE")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "mutation": self.mutation,
            "expected_effect": self.expected_effect,
            "observed_effect": self.observed_effect,
            "passed": self.passed,
            "explanation": self.explanation,
            "impacted_state": self.impacted_state,
            "regression_status": self.regression_status,
        }
