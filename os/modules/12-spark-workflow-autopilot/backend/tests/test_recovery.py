import pytest
from app.engine import planner, execution, recovery
from app.models.models import Task


def test_recovery_options_for_failed_task(db, case):
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap", trigger_type="MANUAL_TRIGGER")
    first = db.query(Task).filter(Task.workflow_id == wf.id).order_by(Task.sequence_index).first()
    execution.start_task(db, first.id, "worker")
    execution.fail_task(db, first.id, "worker", reason="test failure")

    options = recovery.recovery_options(db, first.id)
    option_names = {o["option"] for o in options["options"]}
    assert {"RETRY", "HUMAN_REVIEW", "REPLACE_INPUT", "CANCEL_WORKFLOW"} <= option_names
    assert len(options["affected_downstream_task_ids"]) == 4  # all downstream tasks blocked


def test_retry_moves_task_back_to_ready(db, case):
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap", trigger_type="MANUAL_TRIGGER")
    first = db.query(Task).filter(Task.workflow_id == wf.id).order_by(Task.sequence_index).first()
    execution.start_task(db, first.id, "worker")
    execution.fail_task(db, first.id, "worker", reason="test failure")

    retried = recovery.retry_task(db, first.id, "worker")
    assert retried.status == "READY"
    assert retried.failure_reason is None


def test_system_cannot_retry_consequential_task(db, case):
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap", trigger_type="MANUAL_TRIGGER")
    tasks = {t.title: t for t in db.query(Task).filter(Task.workflow_id == wf.id).all()}
    last = tasks["Attach evidence to case record"]  # APPROVAL_REQUIRED risk
    last.status = "IN_PROGRESS"
    db.commit()
    execution.fail_task(db, last.id, "worker", reason="test failure")

    with pytest.raises(recovery.RecoveryNotAllowed):
        recovery.retry_task(db, last.id, "system")

    # A named human actor is allowed.
    retried = recovery.retry_task(db, last.id, "advocate1")
    assert retried.status in ("READY", "TODO")
