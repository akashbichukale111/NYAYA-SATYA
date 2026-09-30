import pytest
from app.engine import planner, execution
from app.models.models import Task


def _drain_to_consequential(db, wf_id):
    """Advance evidence_gap workflow until the CONSEQUENTIAL/APPROVAL_REQUIRED
    'Attach evidence to case record' task is IN_PROGRESS, without completing it."""
    for _ in range(20):
        tasks = db.query(Task).filter(Task.workflow_id == wf_id).all()
        target = next((t for t in tasks if t.title == "Attach evidence to case record"), None)
        if target.status == "READY":
            return execution.start_task(db, target.id, "worker")
        ready = [t for t in tasks if t.status == "READY"]
        for t in ready:
            t = execution.start_task(db, t.id, "worker")
            try:
                execution.complete_task(db, t.id, "worker")
            except execution.ApprovalRequired:
                pass
            db.refresh(t)
            if t.status == "VERIFICATION_PENDING":
                execution.verify_task(db, t.id, "advocate", passed=True)
    raise AssertionError("did not reach consequential task")


def test_stale_case_blocks_consequential_completion(db, case):
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap", trigger_type="MANUAL_TRIGGER")
    task = _drain_to_consequential(db, wf.id)

    # Simulate an external engine reporting the case changed underneath this workflow.
    execution.bump_case_version(db, case.id, "external-engine", reason="new filing detected")

    with pytest.raises(execution.StaleStateError):
        execution.complete_task(db, task.id, "worker")


def test_revalidate_workflow_clears_staleness(db, case):
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap", trigger_type="MANUAL_TRIGGER")
    task = _drain_to_consequential(db, wf.id)
    execution.bump_case_version(db, case.id, "external-engine", reason="new filing detected")

    with pytest.raises(execution.StaleStateError):
        execution.complete_task(db, task.id, "worker")

    execution.revalidate_workflow(db, wf.id, "advocate1", notes="reviewed the new filing, unrelated to this evidence item")

    # Now it proceeds normally (will raise ApprovalRequired next, not StaleStateError).
    with pytest.raises(execution.ApprovalRequired):
        execution.complete_task(db, task.id, "worker")


def test_system_cannot_revalidate_its_own_stale_workflow(db, case):
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap", trigger_type="MANUAL_TRIGGER")
    with pytest.raises(execution.InvalidTransition):
        execution.revalidate_workflow(db, wf.id, "system")
