from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.database import get_db, init_db
from app.core.enums import Role
from app.models.models import Case, Workflow, Task, Dependency, ApprovalRequest, AuditEvent
from app.schemas.schemas import (
    CreateCaseRequest, TriggerWorkflowRequest, ApprovalDecisionRequest,
    VerifyTaskRequest, CompleteTaskRequest, FailTaskRequest,
)
from app.engine import planner, execution
from app.engine.planner import DuplicateEventError
from app.engine.execution import InvalidTransition, StaleStateError, ApprovalRequired
from app.engine.rbac import require, require_case_access, PermissionDenied
from app.engine.templates import list_templates
from app.engine import recovery, simulation as sim_engine, conflict as conflict_engine, crash_test
from app.adapters.adapters import get_adapter, ADAPTERS
from app.api.deps import get_auth_context, AuthContext
from app.api import serializers as ser

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="SPARK Workflow Autopilot", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(PermissionDenied)
def _perm_denied(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(InvalidTransition)
def _invalid_transition(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(StaleStateError)
def _stale(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=409, content={"detail": str(exc), "code": "STALE_STATE"})


@app.exception_handler(ApprovalRequired)
def _approval_required(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=202, content={
        "detail": "approval required before this action can proceed",
        "approval_request_id": exc.approval_request_id,
    })


@app.exception_handler(recovery.RecoveryNotAllowed)
def _recovery_not_allowed(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(ValueError)
def _value_error(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(DuplicateEventError)
def _duplicate_event(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=200, content={
        "detail": "event already processed; no duplicate workflow created",
        "workflow_id": exc.existing_workflow_id,
    })


# ---------------------------------------------------------------- health

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "spark-workflow-autopilot"}


@app.get("/api/templates")
def get_templates(auth: AuthContext = Depends(get_auth_context)):
    return list_templates()


# ---------------------------------------------------------------- cases

@app.post("/api/cases")
def create_case(body: CreateCaseRequest, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    require(auth.role, "case:manage" if not body.is_demo else "workflow:create")
    case = Case(title=body.title, is_demo=body.is_demo, owner_user_id=auth.user_id)
    db.add(case)
    db.commit()
    db.refresh(case)
    return ser.case_to_dict(case)


@app.get("/api/cases/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    require_case_access(auth.case_access, case_id)
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "case not found")
    return ser.case_to_dict(case)


@app.get("/api/cases")
def list_cases(db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    q = db.query(Case)
    if "*" not in auth.case_access:
        q = q.filter(Case.id.in_(auth.case_access))
    return [ser.case_to_dict(c) for c in q.all()]


# ---------------------------------------------------------------- workflows

@app.post("/api/cases/{case_id}/workflows")
def trigger_workflow(case_id: str, body: TriggerWorkflowRequest, db: Session = Depends(get_db),
                      auth: AuthContext = Depends(get_auth_context)):
    require_case_access(auth.case_access, case_id)
    require(auth.role, "workflow:create")
    wf = planner.plan_workflow(
        db, case_id=case_id, workflow_type=body.workflow_type, trigger_type=body.trigger_type,
        created_by=auth.user_id, trigger_source_engine=body.trigger_source_engine,
        trigger_event_id=body.trigger_event_id, title=body.title, description=body.description,
    )
    return ser.workflow_to_dict(wf)


@app.get("/api/cases/{case_id}/workflows")
def list_workflows(case_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    require_case_access(auth.case_access, case_id)
    require(auth.role, "workflow:view")
    wfs = db.query(Workflow).filter(Workflow.case_id == case_id).all()
    return [ser.workflow_to_dict(w) for w in wfs]


@app.get("/api/workflows/{workflow_id}")
def get_workflow(workflow_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(404, "workflow not found")
    require_case_access(auth.case_access, wf.case_id)
    require(auth.role, "workflow:view")
    tasks = db.query(Task).filter(Task.workflow_id == workflow_id).order_by(Task.sequence_index).all()
    deps = db.query(Dependency).join(Task, Dependency.task_id == Task.id).filter(Task.workflow_id == workflow_id).all()
    return {
        "workflow": ser.workflow_to_dict(wf),
        "tasks": [ser.task_to_dict(t) for t in tasks],
        "dependencies": [ser.dependency_to_dict(d) for d in deps],
    }


@app.post("/api/workflows/{workflow_id}/cancel")
def cancel_workflow(workflow_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(404, "workflow not found")
    require_case_access(auth.case_access, wf.case_id)
    require(auth.role, "workflow:cancel")
    wf = execution.cancel_workflow(db, workflow_id, auth.user_id)
    return ser.workflow_to_dict(wf)


# ---------------------------------------------------------------- tasks

def _load_task_or_404(db, task_id):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "task not found")
    return task


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    task = _load_task_or_404(db, task_id)
    require_case_access(auth.case_access, task.case_id)
    require(auth.role, "task:view")
    return ser.task_to_dict(task)


@app.post("/api/tasks/{task_id}/start")
def start_task(task_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    task = _load_task_or_404(db, task_id)
    require_case_access(auth.case_access, task.case_id)
    require(auth.role, "task:execute")
    task = execution.start_task(db, task_id, auth.user_id)
    return ser.task_to_dict(task)


@app.post("/api/tasks/{task_id}/complete")
def complete_task(task_id: str, body: CompleteTaskRequest, db: Session = Depends(get_db),
                   auth: AuthContext = Depends(get_auth_context)):
    task = _load_task_or_404(db, task_id)
    require_case_access(auth.case_access, task.case_id)
    require(auth.role, "task:execute")
    task = execution.complete_task(db, task_id, auth.user_id, output=body.output)
    return ser.task_to_dict(task)


@app.post("/api/tasks/{task_id}/verify")
def verify_task(task_id: str, body: VerifyTaskRequest, db: Session = Depends(get_db),
                 auth: AuthContext = Depends(get_auth_context)):
    task = _load_task_or_404(db, task_id)
    require_case_access(auth.case_access, task.case_id)
    require(auth.role, "task:verify")
    task = execution.verify_task(db, task_id, auth.user_id, passed=body.passed, reason=body.reason)
    return ser.task_to_dict(task)


@app.post("/api/tasks/{task_id}/fail")
def fail_task(task_id: str, body: FailTaskRequest, db: Session = Depends(get_db),
              auth: AuthContext = Depends(get_auth_context)):
    task = _load_task_or_404(db, task_id)
    require_case_access(auth.case_access, task.case_id)
    require(auth.role, "task:execute")
    task = execution.fail_task(db, task_id, auth.user_id, reason=body.reason)
    return ser.task_to_dict(task)


# ---------------------------------------------------------------- approvals

@app.get("/api/cases/{case_id}/approvals")
def list_approvals(case_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    require_case_access(auth.case_access, case_id)
    require(auth.role, "workflow:view")
    approvals = db.query(ApprovalRequest).filter(ApprovalRequest.case_id == case_id).all()
    return [ser.approval_to_dict(a) for a in approvals]


@app.post("/api/approvals/{approval_id}/decide")
def decide_approval(approval_id: str, body: ApprovalDecisionRequest, db: Session = Depends(get_db),
                     auth: AuthContext = Depends(get_auth_context)):
    approval = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    if not approval:
        raise HTTPException(404, "approval not found")
    require_case_access(auth.case_access, approval.case_id)
    require(auth.role, "approval:decide")
    approval = execution.decide_approval(db, approval_id, decided_by=auth.user_id, approve=body.approve, reason=body.reason)
    return ser.approval_to_dict(approval)


# ---------------------------------------------------------------- audit

@app.get("/api/cases/{case_id}/audit")
def get_audit(case_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    require_case_access(auth.case_access, case_id)
    require(auth.role, "audit:view")
    events = db.query(AuditEvent).filter(AuditEvent.case_id == case_id).order_by(AuditEvent.created_at).all()
    return [ser.audit_to_dict(e) for e in events]


# ---------------------------------------------------------------- Spark Personal OS integration

@app.get("/api/cases/{case_id}/workflow-summary")
def workflow_summary(case_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    """Stable summary API for SPARK Personal OS to consume."""
    require_case_access(auth.case_access, case_id)
    require(auth.role, "workflow:view")
    import datetime as dt
    from app.core.enums import WorkflowState, TaskState

    wfs = db.query(Workflow).filter(Workflow.case_id == case_id).all()
    active = [w for w in wfs if w.status not in ("COMPLETED", "FAILED", "CANCELLED", "SUPERSEDED")]
    blocked = [w for w in wfs if w.status == WorkflowState.BLOCKED.value]
    approval_required = [w for w in wfs if w.status == WorkflowState.APPROVAL_REQUIRED.value]

    tasks = db.query(Task).filter(Task.case_id == case_id).all()
    tasks_due = [t for t in tasks if t.status in (TaskState.READY.value, TaskState.TODO.value)]
    verification_pending = [t for t in tasks if t.status == TaskState.VERIFICATION_PENDING.value]

    return {
        "case_id": case_id,
        "active_workflows": [ser.workflow_to_dict(w) for w in active],
        "blocked_workflows": [ser.workflow_to_dict(w) for w in blocked],
        "approval_required": [ser.workflow_to_dict(w) for w in approval_required],
        "tasks_due": [ser.task_to_dict(t) for t in tasks_due],
        "verification_pending": [ser.task_to_dict(t) for t in verification_pending],
        "attention_items": [ser.workflow_to_dict(w) for w in blocked + approval_required],
        "last_updated": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------- command center

@app.get("/api/cases/{case_id}/command-center")
def command_center(case_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    require_case_access(auth.case_access, case_id)
    require(auth.role, "workflow:view")
    from app.core.enums import WorkflowState

    wfs = db.query(Workflow).filter(Workflow.case_id == case_id).all()
    by_status = {}
    for w in wfs:
        by_status.setdefault(w.status, []).append(w)

    return {
        "active_workflows": len([w for w in wfs if w.status not in ("COMPLETED", "FAILED", "CANCELLED")]),
        "requires_approval": [ser.workflow_to_dict(w) for w in by_status.get(WorkflowState.APPROVAL_REQUIRED.value, [])],
        "blocked": [ser.workflow_to_dict(w) for w in by_status.get(WorkflowState.BLOCKED.value, [])],
        "waiting": [ser.workflow_to_dict(w) for w in by_status.get(WorkflowState.WAITING.value, [])],
        "failed": [ser.workflow_to_dict(w) for w in by_status.get(WorkflowState.FAILED.value, [])],
        "verification_pending": [ser.workflow_to_dict(w) for w in by_status.get(WorkflowState.VERIFICATION_PENDING.value, [])],
        "recently_completed": [ser.workflow_to_dict(w) for w in by_status.get(WorkflowState.COMPLETED.value, [])][-10:],
    }


# ---------------------------------------------------------------- recovery (Section 2)

@app.get("/api/tasks/{task_id}/recovery-options")
def get_recovery_options(task_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    task = _load_task_or_404(db, task_id)
    require_case_access(auth.case_access, task.case_id)
    require(auth.role, "task:view")
    return recovery.recovery_options(db, task_id)


@app.post("/api/tasks/{task_id}/retry")
def retry_task(task_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    task = _load_task_or_404(db, task_id)
    require_case_access(auth.case_access, task.case_id)
    require(auth.role, "task:execute")
    task = recovery.retry_task(db, task_id, auth.user_id)
    return ser.task_to_dict(task)


# ---------------------------------------------------------------- simulation lab (Section 2)

@app.post("/api/workflows/{workflow_id}/simulate/task-failure/{task_id}")
def simulate_task_failure(workflow_id: str, task_id: str, db: Session = Depends(get_db),
                           auth: AuthContext = Depends(get_auth_context)):
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(404, "workflow not found")
    require_case_access(auth.case_access, wf.case_id)
    require(auth.role, "workflow:view")
    return sim_engine.simulate_task_failure(workflow_id, task_id)


@app.post("/api/workflows/{workflow_id}/simulate/approval-rejection/{task_id}")
def simulate_approval_rejection(workflow_id: str, task_id: str, db: Session = Depends(get_db),
                                 auth: AuthContext = Depends(get_auth_context)):
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(404, "workflow not found")
    require_case_access(auth.case_access, wf.case_id)
    require(auth.role, "workflow:view")
    return sim_engine.simulate_approval_rejection(workflow_id, task_id)


# ---------------------------------------------------------------- conflicts (Section 2)

@app.get("/api/cases/{case_id}/conflicts")
def list_conflicts(case_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    require_case_access(auth.case_access, case_id)
    require(auth.role, "workflow:view")
    from app.models.models import ConflictRecord
    records = db.query(ConflictRecord).filter(ConflictRecord.case_id == case_id).all()
    return [{
        "id": r.id, "workflow_id_a": r.workflow_id_a, "workflow_id_b": r.workflow_id_b,
        "signal_a": r.signal_a, "signal_b": r.signal_b, "status": r.status,
        "resolution": r.resolution, "resolved_by": r.resolved_by,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in records]


@app.post("/api/conflicts/{conflict_id}/resolve")
def resolve_conflict(conflict_id: str, resolution: str, db: Session = Depends(get_db),
                      auth: AuthContext = Depends(get_auth_context)):
    from app.models.models import ConflictRecord
    record = db.query(ConflictRecord).filter(ConflictRecord.id == conflict_id).first()
    if not record:
        raise HTTPException(404, "conflict not found")
    require_case_access(auth.case_access, record.case_id)
    require(auth.role, "approval:decide")
    record = conflict_engine.resolve_conflict(db, conflict_id, resolved_by=auth.user_id, resolution=resolution)
    return {"id": record.id, "status": record.status, "resolution": record.resolution}


# ---------------------------------------------------------------- stale-state (Section 2)

@app.post("/api/cases/{case_id}/bump-version")
def bump_case_version(case_id: str, reason: str = "", db: Session = Depends(get_db),
                       auth: AuthContext = Depends(get_auth_context)):
    """Simulates (or, wired to a real CaseContinuityAdapter, records) an external
    case-state change, so consequential workflow execution can be tested against it."""
    require_case_access(auth.case_access, case_id)
    require(auth.role, "case:manage")
    case = execution.bump_case_version(db, case_id, auth.user_id, reason=reason)
    return ser.case_to_dict(case)


@app.post("/api/workflows/{workflow_id}/revalidate")
def revalidate_workflow(workflow_id: str, notes: str = "", db: Session = Depends(get_db),
                         auth: AuthContext = Depends(get_auth_context)):
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(404, "workflow not found")
    require_case_access(auth.case_access, wf.case_id)
    require(auth.role, "approval:decide")
    wf = execution.revalidate_workflow(db, workflow_id, auth.user_id, notes=notes)
    return ser.workflow_to_dict(wf)


# ---------------------------------------------------------------- integration adapters (Section 2)

@app.get("/api/adapters")
def list_adapters(auth: AuthContext = Depends(get_auth_context)):
    return [{"name": name, "source_engine": a.source_engine} for name, a in ADAPTERS.items()]


@app.post("/api/adapters/{adapter_name}/ingest")
def ingest_adapter_event(adapter_name: str, event: dict, db: Session = Depends(get_db),
                          auth: AuthContext = Depends(get_auth_context)):
    """
    Generic ingestion endpoint for any of the 10 upstream engine adapters.
    `event` must at minimum contain case_id; adapter-specific fields (kind,
    event_id, occurred_at) are optional. The normalized trigger is then run
    through the same planner + conflict-detection path as any manual trigger.
    """
    adapter = get_adapter(adapter_name)
    normalized = adapter.normalize(event)
    require_case_access(auth.case_access, normalized.case_id)
    require(auth.role, "workflow:create")

    from app.engine.agents import TriggerAgent
    template_name = TriggerAgent().resolve_template(normalized.trigger_type)
    if template_name is None:
        return {
            "detail": f"trigger_type {normalized.trigger_type} has no automated template; "
                      f"a human must create a workflow manually for this signal.",
            "normalized_trigger": normalized.__dict__,
        }

    wf = planner.plan_workflow(
        db, case_id=normalized.case_id, workflow_type=template_name, trigger_type=normalized.trigger_type,
        created_by=auth.user_id, trigger_source_engine=normalized.source_engine,
        trigger_event_id=normalized.source_event_id,
    )
    return ser.workflow_to_dict(wf)


# ---------------------------------------------------------------- crash test (Section 2)

@app.get("/api/crash-test/run")
def run_crash_tests(auth: AuthContext = Depends(get_auth_context)):
    """
    Runs the 12 resilience scenarios against a disposable, isolated database
    (never the live one) and returns the real results. Scenarios this codebase
    does not yet implement protection for are reported as evaluated=false with
    an honest reason, never a fabricated pass.
    """
    require(auth.role, "audit:view")
    results = crash_test.run_all()
    return {
        "total_scenarios": len(results),
        "evaluated": len([r for r in results if r["evaluated"]]),
        "not_evaluated": len([r for r in results if not r["evaluated"]]),
        "confirmed_risks": [r["scenario"] for r in results if r.get("state_corruption_risk") == "CONFIRMED"],
        "results": results,
    }
