"""Controlled reasoning-type registry for TARKA-VYUH.

Explicitly tracks implementation status for each reasoning capability:
IMPLEMENTED, PARTIAL, NOT_IMPLEMENTED.
Never fabricates results for unbuilt engines.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from tarka_vyuh.contracts.proposal import ReasoningProposal, ReasoningType


class CapabilityStatus(str, Enum):
    IMPLEMENTED = "IMPLEMENTED"
    PARTIAL = "PARTIAL"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    SIMULATED = "SIMULATED"
    TEST_ONLY = "TEST_ONLY"


class ReasoningEngineNotImplementedError(NotImplementedError):
    """Raised when an unbuilt reasoning engine is invoked."""


@dataclass(frozen=True)
class CapabilityDescriptor:
    reasoning_type: ReasoningType
    status: CapabilityStatus
    description: str
    engine_factory: Callable[..., Any] | None = None


_REGISTRY: dict[ReasoningType, CapabilityDescriptor] = {}


def register_capability(
    reasoning_type: ReasoningType,
    status: CapabilityStatus,
    description: str,
    engine_factory: Callable[..., Any] | None = None,
) -> None:
    _REGISTRY[reasoning_type] = CapabilityDescriptor(
        reasoning_type=reasoning_type,
        status=status,
        description=description,
        engine_factory=engine_factory,
    )


def get_capability(reasoning_type: ReasoningType) -> CapabilityDescriptor:
    if reasoning_type not in _REGISTRY:
        raise KeyError(f"Reasoning capability {reasoning_type} is not registered")
    return _REGISTRY[reasoning_type]


def list_capabilities() -> dict[str, dict[str, str]]:
    return {
        rtype.value: {
            "status": descriptor.status.value,
            "description": descriptor.description,
        }
        for rtype, descriptor in sorted(_REGISTRY.items(), key=lambda x: x[0].value)
    }


def execute_reasoning(
    reasoning_type: ReasoningType,
    *args: Any,
    **kwargs: Any,
) -> ReasoningProposal:
    """Dispatches reasoning to the registered engine.

    Fails with ReasoningEngineNotImplementedError for unbuilt engines.
    """
    cap = get_capability(reasoning_type)
    if cap.status is CapabilityStatus.NOT_IMPLEMENTED or cap.engine_factory is None:
        raise ReasoningEngineNotImplementedError(
            f"Reasoning engine for {reasoning_type.value} is NOT_IMPLEMENTED. "
            "Fabricated or mock reasoning results are structurally prohibited."
        )
    engine = cap.engine_factory()
    return engine(*args, **kwargs)


# Initialize default registry mapping
register_capability(
    ReasoningType.ADVERSARIAL_CHALLENGE,
    CapabilityStatus.IMPLEMENTED,
    "Generates adversarial stress-testing challenge against presented claims",
)
register_capability(
    ReasoningType.REPAIR_PROPOSAL,
    CapabilityStatus.PARTIAL,
    "Generates repair proposals from contested resources (adapted from court proceedings)",
)
def _create_contradiction_engine():
    from nyaya_evidence.contradiction.engine import ContradictionAnalysisEngine

    engine = ContradictionAnalysisEngine()

    def _runner(ref_a: Any, ref_b: Any) -> ReasoningProposal:
        cands = engine.analyze_pair(ref_a, ref_b)
        if not cands:
            raise ValueError("No contradiction candidate identified between the provided evidence references")
        return engine.to_reasoning_proposal(cands[0])

    return _runner


register_capability(
    ReasoningType.CONTRADICTION_ANALYSIS,
    CapabilityStatus.IMPLEMENTED,
    "Evidence-grounded contradiction analysis comparing pairs of sanitized evidence references",
    engine_factory=_create_contradiction_engine,
)
register_capability(
    ReasoningType.EVIDENCE_CONFLICT,
    CapabilityStatus.NOT_IMPLEMENTED,
    "Evidence Conflict Arena for dialectical tension resolution (Planned for Phase 2)",
)
register_capability(
    ReasoningType.CAUSAL_ANALYSIS,
    CapabilityStatus.NOT_IMPLEMENTED,
    "Causal DAG analysis and blast-radius quantification (Planned for Phase 3)",
)
register_capability(
    ReasoningType.COUNTERFACTUAL,
    CapabilityStatus.NOT_IMPLEMENTED,
    "Counterfactual Lab simulation under alternate premises (Planned for Phase 3)",
)
register_capability(
    ReasoningType.MISSING_EVIDENCE,
    CapabilityStatus.NOT_IMPLEMENTED,
    "Value-of-information and missing evidence quantification (Planned for Phase 4)",
)

__all__ = [
    "CapabilityDescriptor",
    "CapabilityStatus",
    "ReasoningEngineNotImplementedError",
    "execute_reasoning",
    "get_capability",
    "list_capabilities",
    "register_capability",
]
