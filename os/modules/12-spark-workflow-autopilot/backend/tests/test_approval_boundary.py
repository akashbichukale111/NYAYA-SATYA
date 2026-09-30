import pytest
from app.engine import planner, execution
from app.models.models import Task, ApprovalRequest
from app.core.enums import TaskState, ApprovalState


def _run_to(db, wf_id, title):
    """Advance the workflow's READY tasks one at a time until `title` is reached; return that task."""
    for _ in range(20):
        tasks = db.query(Task).filter(Task.workflow_id == wf_id).all()
        target = next((t for t in tasks if t.title == title), None)
        if target and target.status in (TaskState.READY.value,):
            return target
        ready = [t for t in tasks if t.status == TaskState.READY.value]
        if not ready:
            break
        for t in ready:
            t = execution.start_task(db, t.id, "worker")
            try:
                t = execution.complete_task(db, t.id, "worker")
            except execution.ApprovalRequired as e:
                execution.decide_approval(db, e.approval_request_id, decided_by="advocate", approve=True)
            db.refresh(t)
            if t.status == TaskState.VERIFICATION_PENDING.value:
                execution.verify_task(db, t.id, "advocate", passed=True)
    raise AssertionError(f"never reached task {title}")


def test_approval_required_task_does_not_complete_without_approval(db, case):
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap", trigger_type="MANUAL_TRIGGER")
    target = _run_to(db, wf.id, "Attach evidence to case record")
    task = execution.start_task(db, target.id, "worker")

    with pytest.raises(execution.ApprovalRequired):
        execution.complete_task(db, task.id, "worker")

    db.refresh(task)
    assert task.status == TaskState.APPROVAL_REQUIRED.value  # NOT completed


def test_system_cannot_approve_its_own_request(db, case):
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap", trigger_type="MANUAL_TRIGGER")
    target = _run_to(db, wf.id, "Attach evidence to case record")
    task = execution.start_task(db, target.id, "worker")
    try:
        execution.complete_task(db, task.id, "worker")
    except execution.ApprovalRequired as e:
        approval_id = e.approval_request_id

    with pytest.raises(execution.InvalidTransition):
        execution.decide_approval(db, approval_id, decided_by="system", approve=True)


def test_rejected_approval_blocks_task_not_completes_it(db, case):
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap", trigger_type="MANUAL_TRIGGER")
    target = _run_to(db, wf.id, "Attach evidence to case record")
    task = execution.start_task(db, target.id, "worker")
    try:
        execution.complete_task(db, task.id, "worker")
    except execution.ApprovalRequired as e:
        approval_id = e.approval_request_id

    execution.decide_approval(db, approval_id, decided_by="advocate", approve=False, reason="not sufficient")
    db.refresh(task)
    assert task.status == TaskState.BLOCKED.value
    approval = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    assert approval.state == ApprovalState.REJECTED.value
