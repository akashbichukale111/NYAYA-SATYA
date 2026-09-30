"""
Evaluation Lab (section 34). Every number here is computed live from the
database for the given case (or across all cases) -- nothing is a
hard-coded benchmark. Metrics we have not built instrumentation for yet
are explicitly reported as NOT_YET_MEASURED rather than invented, per
section 39's "no fake benchmark values" rule.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.requirement import Requirement
from app.models.blocker import Blocker
from app.models.verification import Verification
from app.models.crash_test import CrashTest
from app.models.action import Action, Approval

router = APIRouter(prefix="/api/eval", tags=["evaluation"])


def _pct(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(100 * numerator / denominator, 1)


@router.get("/summary")
def eval_summary(case_id: str | None = None, db: Session = Depends(get_db)):
    req_q = db.query(Requirement)
    blk_q = db.query(Blocker)
    ver_q = db.query(Verification)
    cts_q = db.query(CrashTest)
    act_q = db.query(Action)
    if case_id:
        req_q = req_q.filter(Requirement.case_id == case_id)
        blk_q = blk_q.filter(Blocker.case_id == case_id)
        ver_q = ver_q.filter(Verification.case_id == case_id)
        cts_q = cts_q.filter(CrashTest.case_id == case_id)
        act_q = act_q.filter(Action.case_id == case_id)

    requirements = req_q.all()
    blockers = blk_q.all()
    verifications = ver_q.all()
    crash_tests = cts_q.all()
    actions = act_q.all()

    unresolved = [r for r in requirements if r.status == "UNRESOLVED"]
    blocked_requirement_ids = {b.requirement_id for b in blockers}
    provenance_backed = [r for r in requirements if r.evidence_refs]

    decided_actions = [a for a in actions if a.approval is not None]
    overridden = [a for a in decided_actions if a.approval.decision in ("EDIT", "REJECT")]

    measured = {
        "blocker_detection_rate_pct": _pct(
            sum(1 for r in unresolved if r.id in blocked_requirement_ids), len(unresolved)
        ),
        "provenance_coverage_pct": _pct(len(provenance_backed), len(requirements)),
        "verification_success_rate_pct": _pct(
            sum(1 for v in verifications if v.result == "PASSED"), len(verifications)
        ),
        "crash_test_pass_rate_pct": _pct(
            sum(1 for c in crash_tests if c.passed == "true"), len(crash_tests)
        ),
        "human_override_rate_pct": _pct(len(overridden), len(decided_actions)),
        "tool_call_success_rate_pct": None,  # see NOT_YET_MEASURED below
    }

    not_yet_measured = {
        "extraction_accuracy": "Requires a labeled ground-truth extraction dataset; not built for this submission.",
        "false_positive_rate": "Requires a labeled blocker dataset distinguishing true/false blockers.",
        "false_negative_rate": "Requires a labeled blocker dataset distinguishing true/false blockers.",
        "latency_ms_p50_p95": "No timing instrumentation wired into the API layer yet.",
        "tool_call_success_rate_pct": "No per-tool-call success/failure counter wired up yet; only end-to-end AgentRun status is recorded.",
        "regression_failures": "Crash-test regression tracking across builds is not implemented; each run is independent.",
    }

    return {
        "scope": {"case_id": case_id} if case_id else {"case_id": "ALL_CASES"},
        "measured": measured,
        "not_yet_measured": not_yet_measured,
        "sample_sizes": {
            "requirements": len(requirements),
            "blockers": len(blockers),
            "verifications": len(verifications),
            "crash_tests": len(crash_tests),
            "decided_actions": len(decided_actions),
        },
    }
