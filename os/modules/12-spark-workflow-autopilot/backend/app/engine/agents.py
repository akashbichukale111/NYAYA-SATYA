"""
Multi-agent architecture.

Each agent has one responsibility and a narrow interface. They are thin
wrappers with real, distinct logic — not renamed pass-throughs. Each is
independently unit-testable (see tests/test_agents.py) without needing the
others. None of them decides a legal question; each turns a signal or state
into a proposal, a classification, or an action within its lane, per the
core principle in the spec: DETECT -> PLAN -> DECOMPOSE -> CHECK DEPENDENCIES
-> CLASSIFY RISK -> ASK HUMAN WHEN REQUIRED -> EXECUTE -> VERIFY -> AUDIT.
"""
from sqlalchemy.orm import Session

from app.models.models import Task, Workflow, AuditEvent
from app.core.enums import TaskState, WorkflowState, RiskLevel
from app.engine import planner, execution, recovery, conflict as conflict_engine
from app.engine.templates import get_template


class TriggerAgent:
    """Normalizes an inbound (source_engine, trigger_type, case_id) signal into
    a decision of which workflow_type template applies, if any is a direct match."""
    TRIGGER_TO_TEMPLATE = {
        "NEW_EVIDENCE_GAP": "evidence_gap",
        "TRACKED_DATE_APPROACHING": "deadline_preparation",
        "PAST_TRACKED_DATE": "deadline_preparation",
        "REGISTRY_DEFECT_DETECTED": "registry_defect",
        "HEARING_READINESS_BLOCKER": "hearing_readiness",
        "HANDOFF_REQUIRED": "legal_aid_handoff",
    }

    def resolve_template(self, trigger_type: str) -> str | None:
        return self.TRIGGER_TO_TEMPLATE.get(trigger_type)


class WorkflowPlanningAgent:
    """Builds the workflow proposal (delegates to the real planner — this agent's
    job is deciding *whether* and *what*, planner.plan_workflow does the *how*)."""

    def __init__(self, db: Session):
        self.db = db

    def propose_and_create(self, case_id, trigger_type, created_by, trigger_source_engine=None, trigger_event_id=None):
        template_name = TriggerAgent().resolve_template(trigger_type)
        if template_name is None:
            raise ValueError(f"no template mapped for trigger_type {trigger_type}; manual workflow_type required")
        return planner.plan_workflow(
            self.db, case_id=case_id, workflow_type=template_name, trigger_type=trigger_type,
            created_by=created_by, trigger_source_engine=trigger_source_engine, trigger_event_id=trigger_event_id,
        )


class TaskDecompositionAgent:
    """Exposes what a template *would* decompose into, without creating anything —
    useful for previewing a workflow before triggering it for real."""

    def preview(self, workflow_type: str) -> list:
        template = get_template(workflow_type)
        return [
            {"key": k, "title": v["title"], "owner_role": v["owner_role"],
             "risk_level": v["risk_level"].value, "depends_on": v["depends_on"]}
            for k, v in template["tasks"].items()
        ]


class DependencyAgent:
    """Answers dependency-graph questions about an existing workflow."""

    def __init__(self, db: Session):
        self.db = db

    def blocking_chain(self, task_id: str) -> list:
        """What tasks does this task transitively depend on that are not yet satisfied?"""
        from app.models.models import Dependency
        result = []
        seen = set()

        def walk(tid):
            deps = self.db.query(Dependency).filter(Dependency.task_id == tid).all()
            for dep in deps:
                upstream = self.db.query(Task).filter(Task.id == dep.depends_on_task_id).first()
                if upstream and upstream.status not in (TaskState.COMPLETED.value, TaskState.VERIFIED.value):
                    if upstream.id not in seen:
                        seen.add(upstream.id)
                        result.append({"id": upstream.id, "title": upstream.title, "status": upstream.status})
                        walk(upstream.id)
        walk(task_id)
        return result


class RiskAgent:
    """Classifies the risk of a proposed action. Risk levels come from the
    template definition (human-curated), never inferred from free text."""

    def classify(self, task: Task) -> str:
        return task.risk_level

    def requires_human_gate(self, task: Task) -> bool:
        return task.risk_level in (RiskLevel.APPROVAL_REQUIRED.value, RiskLevel.CONSEQUENTIAL.value)


class ApprovalAgent:
    """Determines whether a task may proceed, and if not, what approval is pending."""

    def __init__(self, db: Session):
        self.db = db

    def pending_approval_for(self, task_id: str):
        from app.models.models import ApprovalRequest
        return (
            self.db.query(ApprovalRequest)
            .filter(ApprovalRequest.task_id == task_id, ApprovalRequest.state == "PENDING")
            .first()
        )


class ExecutionAgent:
    """Runs permitted tasks. Refuses (via execution.py's own guards) anything
    that isn't SAFE_REVERSIBLE/LOW_RISK without an approved gate."""

    def __init__(self, db: Session):
        self.db = db

    def run(self, task_id: str, actor: str):
        task = execution.start_task(self.db, task_id, actor)
        try:
            return execution.complete_task(self.db, task.id, actor)
        except execution.ApprovalRequired as e:
            return {"status": "APPROVAL_REQUIRED", "approval_request_id": e.approval_request_id}


class VerificationAgent:
    """Verifies task outcomes. Never marks something verified without an explicit call."""

    def __init__(self, db: Session):
        self.db = db

    def verify(self, task_id: str, actor: str, passed: bool, reason: str = ""):
        return execution.verify_task(self.db, task_id, actor, passed=passed, reason=reason)


class RecoveryAgent:
    """Handles failed/blocked workflows by surfacing real options, never auto-retrying
    a consequential action."""

    def __init__(self, db: Session):
        self.db = db

    def options_for(self, task_id: str) -> dict:
        return recovery.recovery_options(self.db, task_id)

    def retry(self, task_id: str, actor: str):
        return recovery.retry_task(self.db, task_id, actor)


class AttentionAgent:
    """Surfaces workflows/tasks that need a human's attention right now."""

    def __init__(self, db: Session):
        self.db = db

    def attention_items(self, case_id: str) -> dict:
        workflows = self.db.query(Workflow).filter(Workflow.case_id == case_id).all()
        blocked = [w for w in workflows if w.status == WorkflowState.BLOCKED.value]
        approval_required = [w for w in workflows if w.status == WorkflowState.APPROVAL_REQUIRED.value]
        stale_candidates = [
            w for w in workflows
            if w.status not in ("COMPLETED", "FAILED", "CANCELLED")
        ]
        return {
            "blocked_workflow_ids": [w.id for w in blocked],
            "approval_required_workflow_ids": [w.id for w in approval_required],
            "open_workflow_count": len(stale_candidates),
        }


class SimulationAgent:
    """Thin façade over the simulation lab for agent-oriented callers."""

    def what_if_task_fails(self, workflow_id: str, task_id: str) -> dict:
        from app.engine import simulation
        return simulation.simulate_task_failure(workflow_id, task_id)

    def what_if_approval_rejected(self, workflow_id: str, task_id: str) -> dict:
        from app.engine import simulation
        return simulation.simulate_approval_rejection(workflow_id, task_id)


class ConflictAgent:
    """Wraps conflict detection/resolution for agent-oriented callers."""

    def __init__(self, db: Session):
        self.db = db

    def open_conflicts(self, case_id: str) -> list:
        from app.models.models import ConflictRecord
        return self.db.query(ConflictRecord).filter(ConflictRecord.case_id == case_id, ConflictRecord.status == "OPEN").all()

    def resolve(self, conflict_id: str, resolved_by: str, resolution: str):
        return conflict_engine.resolve_conflict(self.db, conflict_id, resolved_by, resolution)


class AuditAgent:
    """Records and queries workflow history. All engine actions already write
    through app.engine.audit.record_event; this agent is the read-side query API."""

    def __init__(self, db: Session):
        self.db = db

    def history_for_case(self, case_id: str) -> list:
        return (
            self.db.query(AuditEvent)
            .filter(AuditEvent.case_id == case_id)
            .order_by(AuditEvent.created_at)
            .all()
        )

    def history_for_workflow(self, workflow_id: str) -> list:
        return (
            self.db.query(AuditEvent)
            .filter(AuditEvent.workflow_id == workflow_id)
            .order_by(AuditEvent.created_at)
            .all()
        )
