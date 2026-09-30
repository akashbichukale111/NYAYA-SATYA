"""
Dependency Agent.

Thin, read-only agent boundary around graph_service -- exists so the
agent mesh has a named, structured place that "builds the dependency
graph" per the spec, without duplicating the traversal logic itself.
"""
from typing import Dict

from sqlalchemy.orm import Session

from app.services.graph_service import coverage_metrics, fragility_report, missing_evidence_report


def report(db: Session, case_id: str) -> Dict:
    return {
        "coverage": coverage_metrics(db, case_id),
        "fragility": fragility_report(db, case_id),
        "missing_evidence": missing_evidence_report(db, case_id),
    }
