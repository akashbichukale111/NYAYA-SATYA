"""
Audit Agent (section 25 #10 / section 30).

Every other agent writes its own audit rows via app/audit.py:log_audit as it
runs (see app/agents/base.py:run_agent). This module is the READ side: it
assembles the append-only audit trail for a case (or system-wide) for the
Audit screen and the Evaluation Lab.
"""
from sqlalchemy.orm import Session

from app.models import AuditEvent, AgentRun


def get_audit_trail(db: Session, *, case_id: str | None = None, limit: int = 500) -> list[dict]:
    q = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc())
    if case_id:
        q = q.filter(AuditEvent.case_id == case_id)
    rows = q.limit(limit).all()
    return [
        {
            "id": r.id, "case_id": r.case_id, "timestamp": r.timestamp.isoformat(), "actor": r.actor,
            "event_type": r.event_type, "correlation_id": r.correlation_id, "source": r.source,
            "result": r.result, "detail": r.detail,
        }
        for r in rows
    ]


def get_agent_runs(db: Session, *, case_id: str | None = None, limit: int = 200) -> list[dict]:
    q = db.query(AgentRun).order_by(AgentRun.started_at.desc())
    if case_id:
        q = q.filter(AgentRun.case_id == case_id)
    rows = q.limit(limit).all()
    return [
        {
            "id": r.id, "case_id": r.case_id, "agent_name": r.agent_name, "correlation_id": r.correlation_id,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "latency_ms": r.latency_ms, "success": r.success, "error": r.error,
            "output_summary": r.output_summary,
        }
        for r in rows
    ]
