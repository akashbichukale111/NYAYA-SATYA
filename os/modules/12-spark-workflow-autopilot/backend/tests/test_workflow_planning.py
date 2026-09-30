from app.engine import planner
from app.core.enums import TaskState
from app.models.models import Task


def test_plan_workflow_creates_full_task_graph(db, case):
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap", trigger_type="MANUAL_TRIGGER")
    tasks = db.query(Task).filter(Task.workflow_id == wf.id).all()
    assert len(tasks) == 5
    # exactly one task (no dependencies) starts READY; the rest wait.
    ready = [t for t in tasks if t.status == TaskState.READY.value]
    todo = [t for t in tasks if t.status == TaskState.TODO.value]
    assert len(ready) == 1
    assert len(todo) == 4


def test_unknown_template_raises(db, case):
    import pytest
    with pytest.raises(ValueError):
        planner.plan_workflow(db, case_id=case.id, workflow_type="not_a_real_template", trigger_type="MANUAL_TRIGGER")


def test_all_five_templates_are_plannable(db, case):
    from app.engine.templates import TEMPLATES
    for wf_type in TEMPLATES:
        wf = planner.plan_workflow(db, case_id=case.id, workflow_type=wf_type, trigger_type="MANUAL_TRIGGER")
        assert wf.id is not None
        assert wf.workflow_type == wf_type
