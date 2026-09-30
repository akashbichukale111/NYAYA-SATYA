from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import User, Task, TaskDependency
from app.models.enums import TaskStatus
from app.schemas.schemas import TaskOut, TaskCreate, TaskStatusUpdate
from app.core.security import get_current_user
from app.services.access import authorized_case_ids
from app.services.audit import log_audit

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
def my_tasks(
    status_filter: str | None = None,
    case_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ids = authorized_case_ids(db, user)
    q = db.query(Task).filter((Task.assignee_id == user.id) | (Task.case_id.in_(ids)))
    if case_id:
        q = q.filter(Task.case_id == case_id)
    if status_filter:
        q = q.filter(Task.status == status_filter)
    return q.order_by(Task.created_at.desc()).all()


@router.post("", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.case_id:
        ids = authorized_case_ids(db, user)
        if payload.case_id not in ids:
            raise HTTPException(status_code=404, detail="Case not found")
    task = Task(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def _is_blocked_by_incomplete_dependency(db: Session, task_id: str) -> bool:
    deps = db.query(TaskDependency).filter(TaskDependency.task_id == task_id).all()
    for dep in deps:
        dep_task = db.get(Task, dep.depends_on_task_id)
        if dep_task and dep_task.status != TaskStatus.COMPLETED:
            return True
    return False


@router.patch("/{task_id}/status", response_model=TaskOut)
def update_task_status(
    task_id: str, payload: TaskStatusUpdate,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    ids = authorized_case_ids(db, user)
    if task.case_id and task.case_id not in ids and task.assignee_id != user.id:
        raise HTTPException(status_code=404, detail="Task not found")

    if payload.status == TaskStatus.COMPLETED:
        if _is_blocked_by_incomplete_dependency(db, task_id):
            raise HTTPException(status_code=400, detail="Task is blocked by an incomplete dependency")
        if task.requires_verification and not payload.verification_confirmed:
            raise HTTPException(
                status_code=400,
                detail="This task requires explicit human verification confirmation before it can be completed",
            )
        if task.requires_verification and payload.verification_confirmed:
            task.verification_confirmed_by = user.id
            log_audit(db, actor_user_id=user.id, action="task.verification_confirmed",
                      target_type="Task", target_id=task.id)
        task.completed_at = datetime.utcnow()

    task.status = payload.status
    db.commit()
    db.refresh(task)
    return task
