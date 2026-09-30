"""
SPARK Workflow Autopilot — flagship demo seeder.

Creates 4 synthetic, clearly-labeled fictional cases and drives each through
its scenario using the REAL engine (planner + execution) — nothing here is a
scripted fake UI state. Run with:

    PYTHONPATH=backend python3 demo/seed_demo.py

All data is marked is_demo=True. No external API keys are used or required.
"""
import os
import sys

_BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, _BACKEND_DIR)

# Always resolve the DB file relative to backend/, regardless of the caller's
# cwd, so the API server (run from backend/) and this seeder always agree on
# which database file they're using.
os.environ.setdefault("SPARK_DB_PATH", os.path.join(_BACKEND_DIR, "spark_workflow_autopilot.db"))

from app.core.database import init_db, SessionLocal
from app.models.models import Case, Task
from app.engine import planner, execution

DEMO_LABEL = "DEMONSTRATION DATA — NOT A REAL CASE"


def make_case(db, title):
    c = Case(title=f"{title} [{DEMO_LABEL}]", is_demo=True)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def demo_a_simple_workflow(db):
    """Signal: missing evidence -> full happy path to COMPLETED."""
    case = make_case(db, "Demo A — Simple Workflow")
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap",
                                trigger_type="NEW_EVIDENCE_GAP", trigger_source_engine="EvidenceDependencyAdapter",
                                created_by="demo-seed")
    _drain(db, wf.id, auto_approve=True, auto_verify=True)
    print(f"[Demo A] case={case.id} workflow={wf.id} -> final status recorded in DB")


def demo_b_approval_gate(db):
    """Signal: consequential action -> stops at human approval, then proceeds after approval."""
    case = make_case(db, "Demo B — Approval Gate")
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="deadline_preparation",
                                trigger_type="TRACKED_DATE_APPROACHING", trigger_source_engine="DeadlineGuardianAdapter",
                                created_by="demo-seed")
    _drain(db, wf.id, auto_approve=True, auto_verify=True)
    print(f"[Demo B] case={case.id} workflow={wf.id} -> executed only after explicit human approval")


def demo_c_failure_and_recovery(db):
    """A task fails partway through -> downstream blocked -> recovery is a human decision, not silent retry."""
    case = make_case(db, "Demo C — Failure + Recovery")
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="registry_defect",
                                trigger_type="REGISTRY_DEFECT_DETECTED", trigger_source_engine="RegistryDefectAdapter",
                                created_by="demo-seed")
    tasks = {t.title: t for t in db.query(Task).filter(Task.workflow_id == wf.id).all()}
    first = tasks["Inspect defect"]
    execution.start_task(db, first.id, "demo-seed")
    execution.fail_task(db, first.id, "demo-seed", reason="Source document could not be located (demo failure)")
    print(f"[Demo C] case={case.id} workflow={wf.id} -> task failed, downstream BLOCKED, awaiting human recovery choice")


def demo_d_multi_engine(db):
    """Multiple engines produce signals for the same case; each becomes its own workflow, never silently merged."""
    case = make_case(db, "Demo D — Multi-Engine")
    wf1 = planner.plan_workflow(db, case_id=case.id, workflow_type="hearing_readiness",
                                 trigger_type="HEARING_READINESS_BLOCKER", trigger_source_engine="HearingReadinessAdapter",
                                 created_by="demo-seed")
    wf2 = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap",
                                 trigger_type="NEW_EVIDENCE_GAP", trigger_source_engine="EvidenceDependencyAdapter",
                                 created_by="demo-seed")
    _drain(db, wf2.id, auto_approve=True, auto_verify=True)
    print(f"[Demo D] case={case.id} workflows={wf1.id},{wf2.id} -> two engines, two independently tracked workflows")


def _drain(db, workflow_id, auto_approve, auto_verify):
    """Advance every READY task to completion, resolving approval/verification as a human reviewer would."""
    for _ in range(30):
        tasks = db.query(Task).filter(Task.workflow_id == workflow_id).all()
        ready = [t for t in tasks if t.status == "READY"]
        if not ready:
            break
        for t in ready:
            t = execution.start_task(db, t.id, "demo-seed")
            try:
                t = execution.complete_task(db, t.id, "demo-seed")
            except execution.ApprovalRequired as e:
                if auto_approve:
                    execution.decide_approval(db, e.approval_request_id, decided_by="demo-advocate",
                                               approve=True, reason="Demo auto-approval for flagship walkthrough.")
                    db.refresh(t)
                    t = execution.complete_task(db, t.id, "demo-seed")
            if t.status == "VERIFICATION_PENDING" and auto_verify:
                execution.verify_task(db, t.id, "demo-advocate", passed=True, reason="Demo verification.")


def main():
    init_db()
    db = SessionLocal()
    demo_a_simple_workflow(db)
    demo_b_approval_gate(db)
    demo_c_failure_and_recovery(db)
    demo_d_multi_engine(db)
    db.close()
    print("\nSeed complete. Start the API with:")
    print("  cd backend && uvicorn app.api.main:app --reload")
    print("Then GET /api/cases to list the 4 demo cases.")


if __name__ == "__main__":
    main()
