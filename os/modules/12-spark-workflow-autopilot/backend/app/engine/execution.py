import datetime as dt
from sqlalchemy.orm import Session

from app.models.models import Case, Workflow, Task, Dependency, ApprovalRequest
from app.core.enums import (
    WorkflowState, TaskState, ApprovalState, VerificationState, EventType,
    TASK_TERMINAL_STATES, RiskLevel,
)
from app.engine.audit import record_event


class InvalidTransition(Exception):
    pass


class StaleStateError(Exception):
    pass


class ApprovalRequired(Exception):
    def __init__(self, approval_request_id):
        self.approval_request_id = approval_request_id
        super().__init__(f"approval required: {approval_request_id}")


# ---------------------------------------------------------------- helpers

def _get_task(db: Session, task_id: str) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise ValueError(f"task {task_id} not found")
    return task


def check_stale(db: Session, case_id: str, expected_version: int) -> None:
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise ValueError(f"case {case_id} not found")
    if case.state_version != expected_version:
        raise StaleStateError(
            f"case {case_id} is at version {case.state_version}, workflow context expected {expected_version}"
        )


def _dependencies_satisfied(db: Session, task: Task) -> bool:
    deps = db.query(Dependency).filter(Dependency.task_id == task.id).all()
    if not deps:
        return True
    for dep in deps:
        upstream = _get_task(db, dep.depends_on_task_id)
        if dep.kind == "VERIFICATION":
            if upstream.status != TaskState.VERIFIED.value:
                return False
        else:  # BLOCKING / CONDITIONAL treated as: must be completed or verified
            if upstream.status not in (TaskState.COMPLETED.value, TaskState.VERIFIED.value):
                return False
    return True


def _propagate_readiness(db: Session, workflow_id: str, actor: str) -> None:
    """After a task completes/verifies, check sibling tasks for newly-satisfied dependencies."""
    tasks = db.query(Task).filter(Task.workflow_id == workflow_id).all()
    for t in tasks:
        if t.status == TaskState.TODO.value and _dependencies_satisfied(db, t):
            t.status = TaskState.READY.value
            record_event(db, t.case_id, EventType.TASK_READY.value, actor,
                         workflow_id=workflow_id, task_id=t.id)


def recompute_workflow_status(db: Session, workflow_id: str, actor: str = "system") -> Workflow:
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    tasks = db.query(Task).filter(Task.workflow_id == workflow_id).all()

    if not tasks:
        return workflow

    statuses = [t.status for t in tasks]
    prior = workflow.status

    if any(s == TaskState.FAILED.value for s in statuses):
        # A failed task blocks its downstream but the workflow as a whole is
        # PARTIALLY_COMPLETED if some tasks already finished, else BLOCKED.
        if any(s in (TaskState.COMPLETED.value, TaskState.VERIFIED.value) for s in statuses):
            workflow.status = WorkflowState.PARTIALLY_COMPLETED.value
        else:
            workflow.status = WorkflowState.BLOCKED.value
    elif all(s in (TaskState.COMPLETED.value, TaskState.VERIFIED.value, TaskState.CANCELLED.value) for s in statuses):
        # Completion requires actual verification for any task that required it.
        needs_verification_unmet = any(
            t.verification_required and t.status != TaskState.VERIFIED.value and t.status != TaskState.CANCELLED.value
            for t in tasks
        )
        workflow.status = WorkflowState.VERIFICATION_PENDING.value if needs_verification_unmet else WorkflowState.COMPLETED.value
    elif any(s == TaskState.APPROVAL_REQUIRED.value for s in statuses):
        workflow.status = WorkflowState.APPROVAL_REQUIRED.value
    elif any(s == TaskState.IN_PROGRESS.value for s in statuses):
        workflow.status = WorkflowState.RUNNING.value
    elif any(s == TaskState.BLOCKED.value for s in statuses):
        workflow.status = WorkflowState.BLOCKED.value
    elif any(s in (TaskState.READY.value, TaskState.TODO.value) for s in statuses):
        workflow.status = WorkflowState.READY.value if any(s == TaskState.READY.value for s in statuses) else WorkflowState.PLANNED.value
    else:
        workflow.status = WorkflowState.WAITING.value

    if workflow.status != prior:
        event_type = {
            WorkflowState.COMPLETED.value: EventType.WORKFLOW_COMPLETED.value,
            WorkflowState.FAILED.value: EventType.WORKFLOW_FAILED.value,
            WorkflowState.BLOCKED.value: EventType.WORKFLOW_BLOCKED.value,
        }.get(workflow.status, None)
        if event_type:
            record_event(db, workflow.case_id, event_type, actor, workflow_id=workflow.id,
                         payload={"from": prior, "to": workflow.status})
    db.flush()
    return workflow


# ---------------------------------------------------------------- actions

def start_task(db: Session, task_id: str, actor: str) -> Task:
    task = _get_task(db, task_id)
    if task.status != TaskState.READY.value:
        raise InvalidTransition(f"task {task_id} is {task.status}, expected READY")
    task.status = TaskState.IN_PROGRESS.value
    task.started_at = dt.datetime.now(dt.timezone.utc)
    record_event(db, task.case_id, EventType.TASK_STARTED.value, actor, workflow_id=task.workflow_id, task_id=task.id)
    recompute_workflow_status(db, task.workflow_id, actor)
    db.commit()
    db.refresh(task)
    return task


def complete_task(db: Session, task_id: str, actor: str, output: str = None) -> Task:
    """
    Complete a task. If the task requires approval and none has been granted,
    this raises ApprovalRequired instead of completing — the caller must
    resolve the approval first. This is the enforcement point that prevents
    the engine from executing a consequential action on its own.

    For CONSEQUENTIAL / APPROVAL_REQUIRED tasks, this also refuses to proceed
    if the underlying case has changed since the workflow was planned (stale
    context) — the caller must call revalidate_workflow() first.
    """
    task = _get_task(db, task_id)
    if task.status != TaskState.IN_PROGRESS.value:
        raise InvalidTransition(f"task {task_id} is {task.status}, expected IN_PROGRESS")

    if task.risk_level in (RiskLevel.CONSEQUENTIAL.value, RiskLevel.APPROVAL_REQUIRED.value):
        workflow = db.query(Workflow).filter(Workflow.id == task.workflow_id).first()
        case = db.query(Case).filter(Case.id == task.case_id).first()
        if case.state_version != workflow.case_state_version_at_creation:
            record_event(db, task.case_id, EventType.STALE_STATE_DETECTED.value, actor,
                         workflow_id=task.workflow_id, task_id=task.id,
                         payload={"workflow_version": workflow.case_state_version_at_creation,
                                  "current_case_version": case.state_version})
            raise StaleStateError(
                f"case {task.case_id} changed (v{workflow.case_state_version_at_creation} -> "
                f"v{case.state_version}) since this workflow was planned; call revalidate_workflow() first"
            )

    if task.approval_required:
        approval = (
            db.query(ApprovalRequest)
            .filter(ApprovalRequest.task_id == task.id)
            .order_by(ApprovalRequest.created_at.desc())
            .first()
        )
        if approval is None:
            approval = request_approval(
                db, task_id=task.id, actor=actor,
                action_description=f"Complete task: {task.title}",
                reason="Task is flagged approval_required by its template.",
            )
            task.status = TaskState.APPROVAL_REQUIRED.value
            recompute_workflow_status(db, task.workflow_id, actor)
            db.commit()
            raise ApprovalRequired(approval.id)
        if approval.state != ApprovalState.APPROVED.value:
            task.status = TaskState.APPROVAL_REQUIRED.value
            recompute_workflow_status(db, task.workflow_id, actor)
            db.commit()
            raise ApprovalRequired(approval.id)

    if task.expected_output != output and output is not None:
        task.expected_output = output

    if task.verification_required:
        task.status = TaskState.VERIFICATION_PENDING.value
        record_event(db, task.case_id, EventType.VERIFICATION_REQUESTED.value, actor,
                     workflow_id=task.workflow_id, task_id=task.id)
    else:
        task.status = TaskState.COMPLETED.value
        task.completed_at = dt.datetime.now(dt.timezone.utc)
        record_event(db, task.case_id, EventType.TASK_COMPLETED.value, actor,
                     workflow_id=task.workflow_id, task_id=task.id)
        _propagate_readiness(db, task.workflow_id, actor)

    recompute_workflow_status(db, task.workflow_id, actor)
    db.commit()
    db.refresh(task)
    return task


def verify_task(db: Session, task_id: str, actor: str, passed: bool, reason: str = "") -> Task:
    task = _get_task(db, task_id)
    if task.status != TaskState.VERIFICATION_PENDING.value:
        raise InvalidTransition(f"task {task_id} is {task.status}, expected VERIFICATION_PENDING")

    if passed:
        task.status = TaskState.VERIFIED.value
        task.verified_at = dt.datetime.now(dt.timezone.utc)
        task.completed_at = task.completed_at or task.verified_at
        record_event(db, task.case_id, EventType.VERIFICATION_COMPLETED.value, actor,
                     workflow_id=task.workflow_id, task_id=task.id, payload={"result": "passed"})
        _propagate_readiness(db, task.workflow_id, actor)
    else:
        task.status = TaskState.FAILED.value
        task.failure_reason = reason or "verification failed"
        record_event(db, task.case_id, EventType.VERIFICATION_COMPLETED.value, actor,
                     workflow_id=task.workflow_id, task_id=task.id, payload={"result": "failed", "reason": reason})
        _block_downstream(db, task, actor)

    recompute_workflow_status(db, task.workflow_id, actor)
    db.commit()
    db.refresh(task)
    return task


def fail_task(db: Session, task_id: str, actor: str, reason: str) -> Task:
    task = _get_task(db, task_id)
    if task.status in TASK_TERMINAL_STATES:
        raise InvalidTransition(f"task {task_id} already terminal ({task.status})")
    task.status = TaskState.FAILED.value
    task.failure_reason = reason
    record_event(db, task.case_id, EventType.TASK_FAILED.value, actor,
                 workflow_id=task.workflow_id, task_id=task.id, payload={"reason": reason})
    _block_downstream(db, task, actor)
    recompute_workflow_status(db, task.workflow_id, actor)
    db.commit()
    db.refresh(task)
    return task


def _block_downstream(db: Session, upstream: Task, actor: str) -> None:
    deps = db.query(Dependency).filter(Dependency.depends_on_task_id == upstream.id).all()
    for dep in deps:
        downstream = _get_task(db, dep.task_id)
        if downstream.status not in TASK_TERMINAL_STATES:
            downstream.status = TaskState.BLOCKED.value
            record_event(db, downstream.case_id, EventType.TASK_BLOCKED.value, actor,
                         workflow_id=downstream.workflow_id, task_id=downstream.id,
                         payload={"blocked_by": upstream.id})
            _block_downstream(db, downstream, actor)  # cascade


def request_approval(db: Session, task_id: str, actor: str, action_description: str, reason: str,
                      workflow_id: str = None) -> ApprovalRequest:
    task = _get_task(db, task_id) if task_id else None
    approval = ApprovalRequest(
        workflow_id=workflow_id or (task.workflow_id if task else None),
        task_id=task_id,
        case_id=task.case_id if task else None,
        action_description=action_description,
        reason=reason,
        previous_state=task.status if task else None,
        requested_by=actor,
    )
    db.add(approval)
    db.flush()
    record_event(db, approval.case_id, EventType.APPROVAL_REQUESTED.value, actor,
                 workflow_id=approval.workflow_id, task_id=task_id, payload={"approval_id": approval.id})
    return approval


def decide_approval(db: Session, approval_id: str, decided_by: str, approve: bool, reason: str = "") -> ApprovalRequest:
    """
    The engine must never approve its own consequential action: decided_by
    must be a human actor id distinct from the 'system' actor that requested it.
    """
    approval = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    if approval is None:
        raise ValueError(f"approval {approval_id} not found")
    if approval.state != ApprovalState.PENDING.value:
        raise InvalidTransition(f"approval {approval_id} already {approval.state}")
    if decided_by == "system":
        raise InvalidTransition("system cannot decide its own approval request")

    approval.decided_by = decided_by
    approval.decision_reason = reason
    approval.decided_at = dt.datetime.now(dt.timezone.utc)

    if approve:
        approval.state = ApprovalState.APPROVED.value
        record_event(db, approval.case_id, EventType.APPROVAL_GRANTED.value, decided_by,
                     workflow_id=approval.workflow_id, task_id=approval.task_id, payload={"approval_id": approval.id})
        if approval.task_id:
            task = _get_task(db, approval.task_id)
            # Task returns to IN_PROGRESS so complete_task can be called again and proceed.
            if task.status == TaskState.APPROVAL_REQUIRED.value:
                task.status = TaskState.IN_PROGRESS.value
    else:
        approval.state = ApprovalState.REJECTED.value
        record_event(db, approval.case_id, EventType.APPROVAL_REJECTED.value, decided_by,
                     workflow_id=approval.workflow_id, task_id=approval.task_id, payload={"approval_id": approval.id})
        if approval.task_id:
            task = _get_task(db, approval.task_id)
            task.status = TaskState.BLOCKED.value
            _block_downstream(db, task, decided_by)

    if approval.workflow_id:
        recompute_workflow_status(db, approval.workflow_id, decided_by)
    db.commit()
    db.refresh(approval)
    return approval


def bump_case_version(db: Session, case_id: str, actor: str, reason: str = "") -> Case:
    """Simulates an external CASE_CHANGED signal (a real deployment would call this
    from CaseContinuityAdapter whenever another engine reports a material change)."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise ValueError(f"case {case_id} not found")
    case.state_version += 1
    record_event(db, case_id, "CASE_CHANGED", actor, payload={"new_version": case.state_version, "reason": reason})
    db.commit()
    db.refresh(case)
    return case


def revalidate_workflow(db: Session, workflow_id: str, actor: str, notes: str = "") -> Workflow:
    """A human re-reviews a workflow whose case context went stale, and explicitly
    accepts the current case state before consequential execution may proceed."""
    if actor == "system":
        raise InvalidTransition("system cannot revalidate its own stale workflow")
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if workflow is None:
        raise ValueError(f"workflow {workflow_id} not found")
    case = db.query(Case).filter(Case.id == workflow.case_id).first()
    old_version = workflow.case_state_version_at_creation
    workflow.case_state_version_at_creation = case.state_version
    record_event(db, workflow.case_id, "WORKFLOW_REVALIDATED", actor, workflow_id=workflow.id,
                 payload={"from_version": old_version, "to_version": case.state_version, "notes": notes})
    db.commit()
    db.refresh(workflow)
    return workflow


def cancel_workflow(db: Session, workflow_id: str, actor: str, reason: str = "") -> Workflow:
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if workflow is None:
        raise ValueError(f"workflow {workflow_id} not found")
    tasks = db.query(Task).filter(Task.workflow_id == workflow_id).all()
    for t in tasks:
        if t.status not in TASK_TERMINAL_STATES:
            t.status = TaskState.CANCELLED.value
    workflow.status = WorkflowState.CANCELLED.value
    record_event(db, workflow.case_id, EventType.WORKFLOW_FAILED.value, actor,
                 workflow_id=workflow.id, payload={"cancelled": True, "reason": reason})
    db.commit()
    db.refresh(workflow)
    return workflow
