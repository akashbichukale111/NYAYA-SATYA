def case_to_dict(c):
    return {
        "id": c.id, "title": c.title, "is_demo": c.is_demo,
        "state_version": c.state_version, "owner_user_id": c.owner_user_id,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def workflow_to_dict(w):
    return {
        "id": w.id, "case_id": w.case_id, "workflow_type": w.workflow_type,
        "title": w.title, "description": w.description,
        "trigger_type": w.trigger_type, "trigger_source_engine": w.trigger_source_engine,
        "trigger_event_id": w.trigger_event_id,
        "status": w.status, "priority": w.priority, "risk_level": w.risk_level,
        "approval_state": w.approval_state, "verification_state": w.verification_state,
        "case_state_version_at_creation": w.case_state_version_at_creation,
        "created_by": w.created_by, "provenance_id": w.provenance_id,
        "created_at": w.created_at.isoformat() if w.created_at else None,
        "updated_at": w.updated_at.isoformat() if w.updated_at else None,
    }


def task_to_dict(t):
    return {
        "id": t.id, "workflow_id": t.workflow_id, "case_id": t.case_id,
        "title": t.title, "description": t.description, "task_type": t.task_type,
        "owner_role": t.owner_role, "status": t.status, "priority": t.priority,
        "sequence_index": t.sequence_index,
        "approval_required": t.approval_required, "verification_required": t.verification_required,
        "risk_level": t.risk_level, "failure_reason": t.failure_reason,
        "provenance_id": t.provenance_id,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "started_at": t.started_at.isoformat() if t.started_at else None,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        "verified_at": t.verified_at.isoformat() if t.verified_at else None,
    }


def dependency_to_dict(d):
    return {
        "id": d.id, "task_id": d.task_id, "depends_on_task_id": d.depends_on_task_id,
        "kind": d.kind,
    }


def approval_to_dict(a):
    return {
        "id": a.id, "workflow_id": a.workflow_id, "task_id": a.task_id, "case_id": a.case_id,
        "action_description": a.action_description, "reason": a.reason,
        "previous_state": a.previous_state, "requested_state": a.requested_state,
        "risk_level": a.risk_level, "state": a.state,
        "requested_by": a.requested_by, "decided_by": a.decided_by,
        "decision_reason": a.decision_reason, "provenance_id": a.provenance_id,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "decided_at": a.decided_at.isoformat() if a.decided_at else None,
    }


def audit_to_dict(e):
    return {
        "id": e.id, "case_id": e.case_id, "workflow_id": e.workflow_id, "task_id": e.task_id,
        "event_type": e.event_type, "actor": e.actor, "payload": e.payload,
        "provenance_id": e.provenance_id,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }
