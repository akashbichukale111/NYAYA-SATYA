import os
from app.engine import planner, simulation
from app.models.models import Task, Workflow


def test_simulate_task_failure_does_not_mutate_live_state(db, case):
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap", trigger_type="MANUAL_TRIGGER")
    first = db.query(Task).filter(Task.workflow_id == wf.id).order_by(Task.sequence_index).first()
    assert first.status == "READY"

    result = simulation.simulate_task_failure(wf.id, first.id)
    assert result["scenario"] == "TASK_FAILURE"
    assert result["live_state_mutated"] is False
    assert result["workflow_status_after"] == "BLOCKED"

    db.expire_all()
    live_task = db.query(Task).filter(Task.id == first.id).first()
    live_wf = db.query(Workflow).filter(Workflow.id == wf.id).first()
    assert live_task.status == "READY"        # untouched
    assert live_wf.status == "PLANNED"         # untouched


def test_simulate_reports_correct_blast_radius(db, case):
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap", trigger_type="MANUAL_TRIGGER")
    first = db.query(Task).filter(Task.workflow_id == wf.id).order_by(Task.sequence_index).first()
    result = simulation.simulate_task_failure(wf.id, first.id)
    # All 4 downstream tasks plus the failed one itself should appear in the diff.
    assert len(result["blast_radius"]) == 5
    assert result["blast_radius"][first.id]["after"] == "FAILED"
