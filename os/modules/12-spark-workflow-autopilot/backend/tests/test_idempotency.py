import pytest
from app.engine import planner
from app.models.models import Workflow


def test_duplicate_trigger_event_does_not_create_second_workflow(db, case):
    wf1 = planner.plan_workflow(
        db, case_id=case.id, workflow_type="evidence_gap", trigger_type="NEW_EVIDENCE_GAP",
        trigger_event_id="evt-dup-1",
    )
    with pytest.raises(planner.DuplicateEventError) as exc_info:
        planner.plan_workflow(
            db, case_id=case.id, workflow_type="evidence_gap", trigger_type="NEW_EVIDENCE_GAP",
            trigger_event_id="evt-dup-1",
        )
    assert exc_info.value.existing_workflow_id == wf1.id
    count = db.query(Workflow).filter(Workflow.case_id == case.id).count()
    assert count == 1


def test_different_event_ids_create_separate_workflows(db, case):
    wf1 = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap",
                                 trigger_type="NEW_EVIDENCE_GAP", trigger_event_id="evt-a")
    wf2 = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap",
                                 trigger_type="NEW_EVIDENCE_GAP", trigger_event_id="evt-b")
    assert wf1.id != wf2.id
