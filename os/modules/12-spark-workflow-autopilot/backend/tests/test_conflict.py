import pytest
from app.engine import planner, conflict
from app.models.models import ConflictRecord


def test_competing_triggers_create_conflict_record(db, case):
    wf1 = planner.plan_workflow(db, case_id=case.id, workflow_type="deadline_preparation",
                                 trigger_type="TRACKED_DATE_APPROACHING")
    wf2 = planner.plan_workflow(db, case_id=case.id, workflow_type="registry_defect",
                                 trigger_type="REGISTRY_DEFECT_DETECTED")
    records = db.query(ConflictRecord).filter(ConflictRecord.case_id == case.id).all()
    assert len(records) == 1
    assert {records[0].workflow_id_a, records[0].workflow_id_b} == {wf1.id, wf2.id}
    assert records[0].status == "OPEN"


def test_non_competing_triggers_create_no_conflict(db, case):
    planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap", trigger_type="NEW_EVIDENCE_GAP")
    planner.plan_workflow(db, case_id=case.id, workflow_type="legal_aid_handoff", trigger_type="HANDOFF_REQUIRED")
    records = db.query(ConflictRecord).filter(ConflictRecord.case_id == case.id).all()
    assert len(records) == 0


def test_system_cannot_resolve_its_own_conflict(db, case):
    planner.plan_workflow(db, case_id=case.id, workflow_type="deadline_preparation", trigger_type="TRACKED_DATE_APPROACHING")
    planner.plan_workflow(db, case_id=case.id, workflow_type="registry_defect", trigger_type="REGISTRY_DEFECT_DETECTED")
    record = db.query(ConflictRecord).filter(ConflictRecord.case_id == case.id).first()
    with pytest.raises(ValueError):
        conflict.resolve_conflict(db, record.id, resolved_by="system", resolution="auto-resolved")


def test_human_can_resolve_conflict(db, case):
    planner.plan_workflow(db, case_id=case.id, workflow_type="deadline_preparation", trigger_type="TRACKED_DATE_APPROACHING")
    planner.plan_workflow(db, case_id=case.id, workflow_type="registry_defect", trigger_type="REGISTRY_DEFECT_DETECTED")
    record = db.query(ConflictRecord).filter(ConflictRecord.case_id == case.id).first()
    resolved = conflict.resolve_conflict(db, record.id, resolved_by="advocate1",
                                          resolution="Registry defect must be corrected before deadline prep proceeds.")
    assert resolved.status == "RESOLVED"
    assert resolved.resolved_by == "advocate1"
