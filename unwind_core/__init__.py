"""UNWIND Core: Governance, Provenance, Authorization and Audit Layer.

UNWIND Core enforces strict governance, state transitions, and audit trails.
UNWIND Core does NOT independently perform legal reasoning or make autonomous legal decisions.
The Human Legal Gate is the final decision authority.
"""

from unwind_core.execution.executor import GovernedExecutor
from unwind_core.execution.guard import (
    ExecutionBlockedError,
    ExecutionGuard,
    ExecutionVerification,
)
from unwind_core.gate.human_gate import (
    AutomatedApprovalProhibitedError,
    HumanDecisionRecord,
    HumanDecisionType,
    HumanLegalGate,
    assert_is_human_actor,
)
from unwind_core.governance.audit import (
    AuditEventType,
    AuditRecord,
    AuditStore,
    get_audit_store,
)
from unwind_core.governance.state_machine import (
    GovernanceStateMachine,
    InvalidGovernanceTransitionError,
)

__all__ = [
    "AuditEventType",
    "AuditRecord",
    "AuditStore",
    "AutomatedApprovalProhibitedError",
    "ExecutionBlockedError",
    "ExecutionGuard",
    "ExecutionVerification",
    "GovernanceStateMachine",
    "GovernedExecutor",
    "HumanDecisionRecord",
    "HumanDecisionType",
    "HumanLegalGate",
    "InvalidGovernanceTransitionError",
    "assert_is_human_actor",
    "get_audit_store",
]
