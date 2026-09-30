from app.engine import planner, execution
from app.engine.agents import (
    TriggerAgent, WorkflowPlanningAgent, TaskDecompositionAgent, DependencyAgent,
    RiskAgent, ApprovalAgent, ExecutionAgent, VerificationAgent, RecoveryAgent,
    AttentionAgent, SimulationAgent, ConflictAgent, AuditAgent,
)
from app.models.models import Task


def test_trigger_agent_maps_known_trigger():
    assert TriggerAgent().resolve_template("NEW_EVIDENCE_GAP") == "evidence_gap"


def test_trigger_agent_returns_none_for_unmapped_trigger():
    assert TriggerAgent().resolve_template("SOMETHING_UNKNOWN") is None


def test_workflow_planning_agent_creates_real_workflow(db, case):
    agent = WorkflowPlanningAgent(db)
    wf = agent.propose_and_create(case.id, "NEW_EVIDENCE_GAP", created_by="agent-test")
    assert wf.workflow_type == "evidence_gap"


def test_task_decomposition_agent_previews_without_creating(db, case):
    agent = TaskDecompositionAgent()
    preview = agent.preview("evidence_gap")
    assert len(preview) == 5
    from app.models.models import Workflow
    assert db.query(Workflow).filter(Workflow.case_id == case.id).count() == 0  # nothing was created


def test_dependency_agent_reports_unsatisfied_chain(db, case):
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap", trigger_type="MANUAL_TRIGGER")
    tasks = {t.title: t for t in db.query(Task).filter(Task.workflow_id == wf.id).all()}
    last = tasks["Attach evidence to case record"]
    chain = DependencyAgent(db).blocking_chain(last.id)
    assert len(chain) == 4  # all 4 upstream tasks are unsatisfied


def test_risk_agent_classifies_and_gates():
    class FakeTask:
        risk_level = "CONSEQUENTIAL"
    assert RiskAgent().classify(FakeTask()) == "CONSEQUENTIAL"
    assert RiskAgent().requires_human_gate(FakeTask()) is True


def test_execution_agent_stops_at_approval_gate(db, case):
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap", trigger_type="MANUAL_TRIGGER")
    tasks = {t.title: t for t in db.query(Task).filter(Task.workflow_id == wf.id).all()}
    last = tasks["Attach evidence to case record"]
    last.status = "READY"
    for dep_title in ["Identify missing evidence", "Request missing evidence", "Record evidence as received",
                       "Validate evidence completeness"]:
        tasks[dep_title].status = "VERIFIED"
    db.commit()

    result = ExecutionAgent(db).run(last.id, "agent-test")
    assert result["status"] == "APPROVAL_REQUIRED"


def test_attention_agent_surfaces_blocked_workflow(db, case):
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap", trigger_type="MANUAL_TRIGGER")
    first = db.query(Task).filter(Task.workflow_id == wf.id).order_by(Task.sequence_index).first()
    execution.start_task(db, first.id, "worker")
    execution.fail_task(db, first.id, "worker", reason="test")

    items = AttentionAgent(db).attention_items(case.id)
    assert wf.id in items["blocked_workflow_ids"]


def test_simulation_agent_delegates_to_real_simulation_lab(db, case):
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap", trigger_type="MANUAL_TRIGGER")
    first = db.query(Task).filter(Task.workflow_id == wf.id).order_by(Task.sequence_index).first()
    result = SimulationAgent().what_if_task_fails(wf.id, first.id)
    assert result["live_state_mutated"] is False


def test_audit_agent_returns_real_events(db, case):
    wf = planner.plan_workflow(db, case_id=case.id, workflow_type="evidence_gap", trigger_type="MANUAL_TRIGGER")
    events = AuditAgent(db).history_for_workflow(wf.id)
    assert len(events) > 0
    assert any(e.event_type == "WORKFLOW_CREATED" for e in events)
