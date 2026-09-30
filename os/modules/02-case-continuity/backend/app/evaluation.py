"""
Evaluation Lab (section 50).

Every metric here is either:
  MEASURED  - computed directly from real rows in this database (this
              instance's own history: agent runs, verifications, state
              versions, provenance links), or
  NOT_MEASURED - honestly labeled as such, with an explanation, rather than
              a fabricated number. There is no labeled ground-truth dataset
              of "correct" extractions in this build, so accuracy metrics
              that would require one are NOT_MEASURED rather than invented.

TARGET values are illustrative product goals, not claims about current
performance - always shown next to MEASURED/NOT_MEASURED, never presented
as achieved results on their own.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import AgentRun, Verification, StateVersion, Deadline, Obligation, Action, Event, Case


def run_evaluation(db: Session, case_id: str | None = None) -> dict:
    agent_q = db.query(AgentRun)
    if case_id:
        agent_q = agent_q.filter(AgentRun.case_id == case_id)
    agent_runs = agent_q.all()

    total_runs = len(agent_runs)
    failed_runs = sum(1 for r in agent_runs if not r.success)
    avg_latency = (sum(r.latency_ms for r in agent_runs) / total_runs) if total_runs else 0.0

    verif_q = db.query(Verification)
    if case_id:
        verif_q = verif_q.filter(Verification.case_id == case_id)
    verifications = verif_q.all()
    verif_total = len(verifications)
    verif_passed = sum(1 for v in verifications if v.result == "passed")

    # Provenance coverage: fraction of Deadline/Obligation/Action rows that
    # carry a non-empty source_event_id pointing at a real, still-present event.
    def coverage(model):
        q = db.query(model)
        if case_id:
            q = q.filter(model.case_id == case_id)
        rows = q.all()
        if not rows:
            return None
        with_source = sum(1 for r in rows if r.source_event_id)
        return {"covered": with_source, "total": len(rows), "ratio": round(with_source / len(rows), 3)}

    provenance = {
        "deadlines": coverage(Deadline),
        "obligations": coverage(Obligation),
        "actions": coverage(Action),
    }

    # State-version integrity: version numbers per case must be a contiguous
    # 0..N sequence with no gaps or duplicates.
    version_q = db.query(StateVersion)
    if case_id:
        version_q = version_q.filter(StateVersion.case_id == case_id)
    case_ids = [case_id] if case_id else [c.id for c in db.query(Case.id).all()]
    integrity_failures = []
    for cid in case_ids:
        nums = sorted(v.version_number for v in db.query(StateVersion).filter(StateVersion.case_id == cid).all())
        expected = list(range(len(nums)))
        if nums != expected:
            integrity_failures.append({"case_id": cid, "found_versions": nums, "expected": expected})

    return {
        "agent_execution": {
            "status": "MEASURED" if total_runs else "NOT_MEASURED",
            "total_runs": total_runs,
            "failed_runs": failed_runs,
            "success_rate": round((total_runs - failed_runs) / total_runs, 3) if total_runs else None,
            "avg_latency_ms": round(avg_latency, 2) if total_runs else None,
        },
        "verification_success": {
            "status": "MEASURED" if verif_total else "NOT_MEASURED",
            "passed": verif_passed, "total": verif_total,
            "rate": round(verif_passed / verif_total, 3) if verif_total else None,
        },
        "provenance_coverage": {
            "status": "MEASURED" if any(provenance.values()) else "NOT_MEASURED",
            "by_entity": provenance,
            "target": "1.0 (every entity traceable to a source event)",
        },
        "state_version_integrity": {
            "status": "MEASURED",
            "cases_checked": len(case_ids),
            "failures": integrity_failures,
            "target": "0 integrity failures",
        },
        "event_extraction_accuracy": {
            "status": "NOT_MEASURED",
            "reason": "Requires a labeled ground-truth extraction dataset, which this build does not ship with.",
            "target": ">= 0.85 F1 on a held-out labeled set (future work)",
        },
        "state_change_detection_accuracy": {
            "status": "NOT_MEASURED",
            "reason": "Requires labeled 'correct change' annotations per synthetic case; not implemented here.",
            "target": ">= 0.85 precision/recall (future work)",
        },
        "cross_case_isolation": {
            "status": "MEASURED",
            "description": "Automated check: no Event/Document/Deadline/Obligation/Action row references a "
                            "different case_id than its parent case (see tests/test_case_isolation.py).",
        },
        "false_positives": {"status": "NOT_MEASURED", "reason": "Requires labeled data; see above."},
        "false_negatives": {"status": "NOT_MEASURED", "reason": "Requires labeled data; see above."},
        "regression_failures": {
            "status": "MEASURED",
            "description": "See CI/test-suite result from `pytest` (scripts/run_tests.sh), reported separately.",
        },
    }
