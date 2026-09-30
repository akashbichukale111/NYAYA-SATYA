from sqlalchemy.orm import Session

from app.models.models import Case, Workflow, Task, Dependency, ProcessedEvent
from app.core.enums import WorkflowState, TaskState, EventType
from app.engine.templates import get_template
from app.engine.audit import record_event


class DuplicateEventError(Exception):
    """Raised (informationally) when a trigger_event_id was already processed."""
    def __init__(self, existing_workflow_id):
        self.existing_workflow_id = existing_workflow_id
        super().__init__(f"event already processed -> workflow {existing_workflow_id}")


def plan_workflow(
    db: Session,
    case_id: str,
    workflow_type: str,
    trigger_type: str,
    created_by: str = "system",
    trigger_source_engine: str = None,
    trigger_event_id: str = None,
    title: str = None,
    description: str = None,
) -> Workflow:
    """
    Create a workflow + its full task graph from a template.

    Idempotent: if trigger_event_id has already been processed, the existing
    workflow is returned via DuplicateEventError rather than creating a
    duplicate consequential workflow.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise ValueError(f"case {case_id} not found")

    if trigger_event_id:
        existing = db.query(ProcessedEvent).filter(ProcessedEvent.event_id == trigger_event_id).first()
        if existing:
            raise DuplicateEventError(existing.workflow_id)

    template = get_template(workflow_type)

    workflow = Workflow(
        case_id=case_id,
        workflow_type=workflow_type,
        title=title or template["title"],
        description=description or template["description"],
        trigger_type=trigger_type,
        trigger_source_engine=trigger_source_engine,
        trigger_event_id=trigger_event_id,
        status=WorkflowState.PLANNED.value,
        created_by=created_by,
        case_state_version_at_creation=case.state_version,
    )
    db.add(workflow)
    db.flush()

    # First pass: create tasks, key -> Task row
    key_to_task = {}
    for idx, (key, spec) in enumerate(template["tasks"].items()):
        task = Task(
            workflow_id=workflow.id,
            case_id=case_id,
            title=spec["title"],
            task_type=spec["task_type"],
            owner_role=spec["owner_role"],
            sequence_index=idx,
            approval_required=spec["approval_required"],
            verification_required=spec["verification_required"],
            risk_level=spec["risk_level"].value,
            status=TaskState.TODO.value,
        )
        db.add(task)
        db.flush()
        key_to_task[key] = task

    # Second pass: dependencies
    for key, spec in template["tasks"].items():
        task = key_to_task[key]
        for dep_key in spec["depends_on"]:
            dep_task = key_to_task[dep_key]
            db.add(Dependency(task_id=task.id, depends_on_task_id=dep_task.id, kind="BLOCKING"))

    db.flush()

    # Tasks with no dependencies become READY immediately.
    for key, spec in template["tasks"].items():
        task = key_to_task[key]
        if not spec["depends_on"]:
            task.status = TaskState.READY.value
            record_event(db, case_id, EventType.TASK_READY.value, created_by,
                         workflow_id=workflow.id, task_id=task.id)
        record_event(db, case_id, EventType.TASK_CREATED.value, created_by,
                     workflow_id=workflow.id, task_id=task.id, payload={"title": task.title})

    record_event(db, case_id, EventType.WORKFLOW_CREATED.value, created_by,
                 workflow_id=workflow.id, payload={"workflow_type": workflow_type, "trigger_type": trigger_type})

    if trigger_event_id:
        db.add(ProcessedEvent(event_id=trigger_event_id, workflow_id=workflow.id))

    db.commit()
    db.refresh(workflow)

    # Conflict detection runs after commit so the new workflow is visible to the query.
    from app.engine.conflict import detect_conflicts
    detect_conflicts(db, case_id, workflow)
    db.commit()

    return workflow
