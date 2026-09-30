"""
Workflow Simulation Lab.

Runs a hypothetical mutation (task failure, approval rejection) using the
REAL engine functions (execution.fail_task, execution.complete_task, etc.)
against a dedicated database connection whose outer transaction is *always*
rolled back at the end — regardless of how many times the engine code calls
session.commit() internally. This is the standard SQLAlchemy "join an
external transaction" isolation pattern: the inner session's commit() only
releases a SAVEPOINT, it never reaches the database file, so live state is
provably unmodified.
"""
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker

from app.core.database import DATABASE_URL
from app.models.models import Task, Workflow
from app.engine import execution

# A dedicated engine with NullPool: every checkout is a brand-new physical
# DBAPI connection, so this can never share an in-flight transaction with
# the application's main SessionLocal engine — isolation is guaranteed by
# the database, not by application bookkeeping.
_sim_engine = create_engine(DATABASE_URL, poolclass=NullPool, connect_args={"check_same_thread": False})


# pysqlite's DBAPI driver auto-begins its own transaction only before
# INSERT/UPDATE/DELETE, not before SAVEPOINT — which silently breaks
# SAVEPOINT-based nested-transaction isolation unless disabled and replaced
# with SQLAlchemy's own explicit BEGIN. This is SQLAlchemy's documented
# workaround for pysqlite; without it, rollback of the outer transaction
# below would not actually undo the simulated writes.
@event.listens_for(_sim_engine, "connect")
def _sim_do_connect(dbapi_connection, connection_record):
    dbapi_connection.isolation_level = None


@event.listens_for(_sim_engine, "begin")
def _sim_do_begin(conn):
    conn.exec_driver_sql("BEGIN")


@contextmanager
def _isolated_session():
    connection = _sim_engine.connect()
    outer_txn = connection.begin()
    IsolatedSession = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    session = IsolatedSession()
    try:
        yield session
    finally:
        session.close()
        outer_txn.rollback()
        connection.close()


def _snapshot(session, workflow_id: str) -> dict:
    tasks = session.query(Task).filter(Task.workflow_id == workflow_id).all()
    workflow = session.query(Workflow).filter(Workflow.id == workflow_id).first()
    return {
        "workflow_status": workflow.status,
        "tasks": {t.id: t.status for t in tasks},
    }


def _diff(before: dict, after: dict) -> dict:
    return {
        tid: {"before": before["tasks"].get(tid), "after": after["tasks"].get(tid)}
        for tid in set(before["tasks"]) | set(after["tasks"])
        if before["tasks"].get(tid) != after["tasks"].get(tid)
    }


def simulate_task_failure(workflow_id: str, task_id: str) -> dict:
    """What if `task_id` fails right now? Returns a before/after diff. Live state is untouched."""
    with _isolated_session() as sim_db:
        before = _snapshot(sim_db, workflow_id)
        task = sim_db.query(Task).filter(Task.id == task_id).first()
        if task.status not in ("READY", "IN_PROGRESS"):
            task.status = "IN_PROGRESS"
            sim_db.commit()
        execution.fail_task(sim_db, task_id, "simulation", reason="[SIMULATED] hypothetical failure")
        after = _snapshot(sim_db, workflow_id)

    return {
        "scenario": "TASK_FAILURE",
        "task_id": task_id,
        "workflow_status_before": before["workflow_status"],
        "workflow_status_after": after["workflow_status"],
        "blast_radius": _diff(before, after),
        "live_state_mutated": False,
    }


def simulate_approval_rejection(workflow_id: str, task_id: str) -> dict:
    """What if the approval for this task is rejected? Live state is untouched."""
    with _isolated_session() as sim_db:
        before = _snapshot(sim_db, workflow_id)
        task = sim_db.query(Task).filter(Task.id == task_id).first()
        if task.status != "IN_PROGRESS":
            task.status = "IN_PROGRESS"
            sim_db.commit()
        approval_id = None
        try:
            execution.complete_task(sim_db, task_id, "simulation")
        except execution.ApprovalRequired as e:
            approval_id = e.approval_request_id
        if approval_id:
            execution.decide_approval(sim_db, approval_id, decided_by="simulation-human", approve=False,
                                       reason="[SIMULATED] hypothetical rejection")
        after = _snapshot(sim_db, workflow_id)

    return {
        "scenario": "APPROVAL_REJECTED",
        "task_id": task_id,
        "workflow_status_before": before["workflow_status"],
        "workflow_status_after": after["workflow_status"],
        "blast_radius": _diff(before, after),
        "live_state_mutated": False,
    }
