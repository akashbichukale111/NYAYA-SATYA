"""Crash-Test Agent -- wraps the non-destructive simulation engine.
No authority beyond simulate-and-record; see impact_service.run_crash_test."""
from typing import Dict

from sqlalchemy.orm import Session

from app.services.impact_service import run_crash_test


def simulate(db: Session, case_id: str, event_type: str, target_type: str, target_id: str) -> Dict:
    run = run_crash_test(db, case_id, event_type, target_type, target_id, created_by="CrashTestAgent")
    return {
        "id": run.id, "criticality": run.criticality,
        "affected_claims": run.affected_claims, "affected_issues": run.affected_issues,
        "new_gaps": run.new_gaps, "new_conflicts": run.new_conflicts,
        "human_review_required": run.human_review_required,
    }
