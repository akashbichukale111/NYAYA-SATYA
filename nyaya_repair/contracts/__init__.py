"""Contracts for NYAYA-SATYA Auto-Healer subsystem (Phase 6)."""

from nyaya_repair.contracts.repair import (
    AuthorityType,
    LegalAuthorityRef,
    LegalGrounding,
    LegalGroundingStatus,
)
from nyaya_repair.contracts.repair_action import (
    ActionPrimitive,
    RepairAction,
)
from nyaya_repair.contracts.repair_candidate import (
    RepairCandidate,
    RepairCandidateStatus,
    RepairChangeType,
    compute_repair_fingerprint,
)
from nyaya_repair.contracts.repair_certificate import (
    AdmissibilityGateStatus,
    AdmissibilityReadinessGate,
)
from nyaya_repair.contracts.repair_constraint import (
    ConstraintViolationError,
    RepairConstraints,
)
from nyaya_repair.contracts.repair_result import (
    RepairExecutionResult,
    SimulatedRepairReport,
)
from nyaya_repair.contracts.repair_utility import (
    RepairUtilityVector,
)

__all__ = [
    "ActionPrimitive",
    "AdmissibilityGateStatus",
    "AdmissibilityReadinessGate",
    "AuthorityType",
    "ConstraintViolationError",
    "LegalAuthorityRef",
    "LegalGrounding",
    "LegalGroundingStatus",
    "RepairAction",
    "RepairCandidate",
    "RepairCandidateStatus",
    "RepairChangeType",
    "RepairConstraints",
    "RepairExecutionResult",
    "RepairUtilityVector",
    "SimulatedRepairReport",
    "compute_repair_fingerprint",
]
