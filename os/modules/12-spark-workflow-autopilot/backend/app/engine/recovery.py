"""
Failure recovery.

When a task fails, the engine never silently retries a consequential action.
Instead it surfaces real, state-derived recovery options and lets a human
choose. `retry_task` is the only automated path, and it is itself gated:
it refuses to retry a task whose risk is CONSEQUENTIAL or APPROVAL_REQUIRED
without an explicit human actor approving the retry.
"""
from sqlalchemy.orm import Session

from app.models.models import Task, Dependency
from app.core.enums import TaskState, RiskLevel, EventType
from app.engine.audit import record_event


class RecoveryNotAllowed(Exception):
    pass


def recovery_options(db: Session, task_id: str) -> dict:
    """Returns real, derived recovery options for a FAILED task — never fabricated percentages."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise ValueError(f"task {task_id} not found")
    if task.status != TaskState.FAILED.value:
        raise ValueError(f"task {task_id} is {task.status}, not FAILED")

    downstream = _downstream_blocked(db, task)

    options = [
        {
            "option": "RETRY",
            "description": "Re-attempt the same task from TODO.",
            "requires_human_review": task.risk_level in (RiskLevel.CONSEQUENTIAL.value, RiskLevel.APPROVAL_REQUIRED.value),
        },
        {
            "option": "HUMAN_REVIEW",
            "description": "Escalate to human review without retrying automatically.",
            "requires_human_review": True,
        },
        {
            "option": "REPLACE_INPUT",
            "description": "Replace the task's source input (e.g. a corrected document) and retry.",
            "requires_human_review": True,
        },
        {
            "option": "CANCEL_WORKFLOW",
            "description": "Cancel the whole workflow; nothing further executes.",
            "requires_human_review": True,
        },
    ]

    return {
        "task_id": task.id,
        "failure_reason": task.failure_reason,
        "affected_downstream_task_ids": [t.id for t in downstream],
        "workflow_id": task.workflow_id,
        "options": options,
    }


def _downstream_blocked(db: Session, task: Task) -> list:
    result = []
    seen = set()

    def walk(t):
        deps = db.query(Dependency).filter(Dependency.depends_on_task_id == t.id).all()
        for dep in deps:
            child = db.query(Task).filter(Task.id == dep.task_id).first()
            if child and child.id not in seen:
                seen.add(child.id)
                result.append(child)
                walk(child)

    walk(task)
    return result


def retry_task(db: Session, task_id: str, actor: str) -> Task:
    """
    Move a FAILED task back to TODO/READY for another attempt. Refuses for
    CONSEQUENTIAL/APPROVAL_REQUIRED tasks unless actor is an explicit human
    (never 'system'), preventing silent automated retry of a consequential action.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise ValueError(f"task {task_id} not found")
    if task.status != TaskState.FAILED.value:
        raise ValueError(f"task {task_id} is {task.status}, not FAILED")

    if task.risk_level in (RiskLevel.CONSEQUENTIAL.value, RiskLevel.APPROVAL_REQUIRED.value) and actor == "system":
        raise RecoveryNotAllowed(
            f"task {task_id} is {task.risk_level}; retry requires an explicit human actor, not 'system'"
        )

    from app.engine.execution import _dependencies_satisfied  # local import to avoid cycle at module load

    task.status = TaskState.READY.value if _dependencies_satisfied(db, task) else TaskState.TODO.value
    task.failure_reason = None
    record_event(db, task.case_id, "RECOVERY_CHOSEN", actor, workflow_id=task.workflow_id, task_id=task.id,
                 payload={"choice": "RETRY"})
    db.commit()
    db.refresh(task)
    return task
