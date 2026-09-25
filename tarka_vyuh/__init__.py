"""TARKA-VYUH: Adversarial Legal-Reasoning Engine.

TARKA-VYUH is responsible for analytical proposals:
- Contradiction analysis
- Evidence conflict
- Jenga / Achilles-heel analysis
- Causal reasoning
- Counterfactual reasoning
- Missing evidence
- Repair proposals
- Adversarial challenge

TARKA-VYUH generates proposals. It NEVER executes consequential actions directly.
All consequential actions are governed by UNWIND Core and the Human Legal Gate.
"""

from tarka_vyuh.contracts.proposal import (
    ProposalStatus,
    ProposedAction,
    ReasoningProposal,
    ReasoningType,
)
from tarka_vyuh.contracts.provenance import (
    ProvenanceRef,
    ProvenanceType,
    compute_sha256,
)
from tarka_vyuh.validation.validator import (
    ProposalValidationError,
    assert_valid_proposal,
    validate_proposal,
)

__all__ = [
    "ProposalStatus",
    "ProposalValidationError",
    "ProposedAction",
    "ProvenanceRef",
    "ProvenanceType",
    "ReasoningProposal",
    "ReasoningType",
    "assert_valid_proposal",
    "compute_sha256",
    "validate_proposal",
]
