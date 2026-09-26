"""Readiness probes for NYAYA-SATYA Observability Subsystem.

Answers: Can the service safely accept traffic?
Verifies that essential in-memory stores, governance state machines, and file
quarantine subsystems are initialized and operating.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from unwind_core.governance.state_machine import GovernanceStateMachine
from unwind_core.governance.audit import get_audit_store
from nyaya_evidence.registry.store import get_evidence_registry
from nyaya_evidence.quarantine.manager import QuarantineManager


def check_readiness() -> dict[str, Any]:
    """Deep readiness check across internal subsystems."""
    checks: dict[str, bool] = {}
    details: dict[str, str] = {}

    # 1. State machine check
    try:
        sm = GovernanceStateMachine()
        checks["governance_state_machine"] = True
    except Exception as e:
        checks["governance_state_machine"] = False
        details["governance_state_machine"] = str(e)

    # 2. Audit store check
    try:
        audit = get_audit_store()
        checks["audit_store"] = True
    except Exception as e:
        checks["audit_store"] = False
        details["audit_store"] = str(e)

    # 3. Evidence registry check
    try:
        registry = get_evidence_registry()
        checks["evidence_registry"] = True
    except Exception as e:
        checks["evidence_registry"] = False
        details["evidence_registry"] = str(e)

    # 4. Quarantine manager check
    try:
        qm = QuarantineManager()
        checks["quarantine_subsystem"] = True
    except Exception as e:
        checks["quarantine_subsystem"] = False
        details["quarantine_subsystem"] = str(e)

    all_ready = all(checks.values())

    return {
        "status": "ready" if all_ready else "unready",
        "ready": all_ready,
        "timestamp": datetime.now(UTC).isoformat(),
        "subsystems": checks,
        "details": details if not all_ready else {},
    }


__all__ = [
    "check_readiness",
]
