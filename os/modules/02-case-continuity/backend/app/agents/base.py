"""
Shared agent plumbing.

Every agent call is wrapped in `run_agent`, which records an AgentRun row
(name, correlation id, timing, success/failure) for the Audit / Evaluation
Lab, and never lets an agent write to the Case Digital Twin directly - each
agent function returns data; only the orchestrator (app/agents/orchestrator.py)
commits state transitions, after verification.
"""
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import AgentRun
from app.audit import log_audit


def new_correlation_id() -> str:
    return uuid.uuid4().hex[:12]


@contextmanager
def run_agent(db: Session, *, case_id: str, agent_name: str, correlation_id: str, input_summary: str = ""):
    run = AgentRun(
        case_id=case_id,
        agent_name=agent_name,
        correlation_id=correlation_id,
        input_summary=input_summary[:500],
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    start = time.perf_counter()
    result_holder = {"output_summary": "", "success": True, "error": ""}
    try:
        yield result_holder
    except Exception as exc:  # noqa: BLE001
        result_holder["success"] = False
        result_holder["error"] = str(exc)
        raise
    finally:
        run.finished_at = datetime.now(timezone.utc)
        run.latency_ms = (time.perf_counter() - start) * 1000
        run.success = result_holder["success"]
        run.error = result_holder["error"]
        run.output_summary = result_holder["output_summary"][:500]
        db.commit()
        log_audit(
            db, case_id=case_id, actor=agent_name, event_type="agent_run",
            correlation_id=correlation_id, source=agent_name,
            result="success" if result_holder["success"] else "failed",
            detail={"latency_ms": run.latency_ms, "output_summary": result_holder["output_summary"][:200]},
        )
