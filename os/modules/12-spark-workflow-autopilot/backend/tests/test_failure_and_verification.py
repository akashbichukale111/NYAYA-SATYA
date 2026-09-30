from app.engine import planner, execution
from app.models.models import Task, Workflow
from app.core.enums import TaskState, WorkflowState


def test_failed_task_blocks_downstream(db, case):
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap", trigger_type="MANUAL_TRIGGER")
    tasks = {t.title: t for t in db.query(Task).filter(Task.workflow_id == wf.id).all()}

    first = tasks["Identify missing evidence"]
    execution.start_task(db, first.id, "worker")
    execution.fail_task(db, first.id, "worker", reason="could not determine what is missing")

    db.refresh(tasks["Request missing evidence"])
    blocked = db.query(Task).filter(Task.id == tasks["Request missing evidence"].id).first()
    assert blocked.status == TaskState.BLOCKED.value

    wf_after = db.query(Workflow).filter(Workflow.id == wf.id).first()
    assert wf_after.status == WorkflowState.BLOCKED.value


def test_workflow_not_completed_until_verification_passes(db, case):
    """A task flagged verification_required must reach VERIFIED, not just COMPLETED,
    before the workflow can be marked COMPLETED — this is the anti-fabrication guarantee."""
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap", trigger_type="MANUAL_TRIGGER")
    tasks = {t.title: t for t in db.query(Task).filter(Task.workflow_id == wf.id).all()}

    t = tasks["Identify missing evidence"]
    execution.start_task(db, t.id, "worker")
    execution.complete_task(db, t.id, "worker")

    t = db.query(Task).filter(Task.id == tasks["Request missing evidence"].id).first()
    execution.start_task(db, t.id, "worker")
    execution.complete_task(db, t.id, "worker")

    t = db.query(Task).filter(Task.id == tasks["Record evidence as received"].id).first()
    execution.start_task(db, t.id, "worker")
    execution.complete_task(db, t.id, "worker")

    # "Validate evidence completeness" requires verification -> must not silently complete
    t = db.query(Task).filter(Task.id == tasks["Validate evidence completeness"].id).first()
    execution.start_task(db, t.id, "worker")
    t = execution.complete_task(db, t.id, "worker")
    assert t.status == TaskState.VERIFICATION_PENDING.value  # not COMPLETED

    wf_after = db.query(Workflow).filter(Workflow.id == wf.id).first()
    assert wf_after.status != WorkflowState.COMPLETED.value
