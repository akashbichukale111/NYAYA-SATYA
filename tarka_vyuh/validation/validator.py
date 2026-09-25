"""Proposal Validation Service for TARKA-VYUH.

Performs deterministic structural and security validation of reasoning proposals.
Rejects malformed data, missing provenance, and prompt injection attempts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from tarka_vyuh.contracts.proposal import (
    ProposalStatus,
    ProposedAction,
    ReasoningProposal,
    ReasoningType,
)
from tarka_vyuh.contracts.provenance import ProvenanceRef

# Prompt injection signatures that attempt to hijack governance or state
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"override\s+(governance|status|approval|decision)", re.IGNORECASE),
    re.compile(r"set\s+status\s*=\s*['\"]?human_approved['\"]?", re.IGNORECASE),
    re.compile(r"bypass\s+(gate|governance|human|authorization)", re.IGNORECASE),
    re.compile(r"system:\s*(authorize|approve|grant)", re.IGNORECASE),
    re.compile(r"as\s+an?\s+admin(istrator)?,\s*(approve|execute)", re.IGNORECASE),
]


class ProposalValidationError(ValueError):
    """Raised when a proposal fails validation."""

    def __init__(self, violations: list[str]) -> None:
        self.violations = violations
        super().__init__(f"Proposal validation failed: {'; '.join(violations)}")


def validate_proposal(proposal: Any) -> list[str]:
    """Inspects a proposal and returns a list of validation violations.

    An empty list indicates the proposal is structurally and security valid.
    """
    violations: list[str] = []

    if not isinstance(proposal, ReasoningProposal):
        violations.append(f"Expected ReasoningProposal instance, got {type(proposal).__name__}")
        return violations

    # 1. Proposal ID checks
    if not proposal.proposal_id or not proposal.proposal_id.strip():
        violations.append("proposal_id is required and cannot be blank")
    elif len(proposal.proposal_id) > 128:
        violations.append("proposal_id exceeds maximum length of 128 chars")
    elif not re.fullmatch(r"^[a-zA-Z0-9_-]+$", proposal.proposal_id):
        violations.append("proposal_id contains invalid characters (must be alphanumeric, hyphens, or underscores)")

    # 2. Case ID checks
    if not proposal.case_id or not proposal.case_id.strip():
        violations.append("case_id is required and cannot be blank")
    elif len(proposal.case_id) > 128:
        violations.append("case_id exceeds maximum length of 128 chars")

    # 3. Reasoning Type
    if not isinstance(proposal.reasoning_type, ReasoningType):
        violations.append(f"Invalid reasoning_type: {proposal.reasoning_type}")

    # 4. Status
    if not isinstance(proposal.status, ProposalStatus):
        violations.append(f"Invalid proposal status: {proposal.status}")

    # 5. Evidence & Claims presence
    if not proposal.input_evidence_ids:
        violations.append("input_evidence_ids cannot be empty")
    else:
        for idx, eid in enumerate(proposal.input_evidence_ids):
            if not isinstance(eid, str) or not eid.strip():
                violations.append(f"input_evidence_ids[{idx}] must be a non-empty string")

    if not proposal.claims:
        violations.append("claims list cannot be empty")
    else:
        for idx, claim in enumerate(proposal.claims):
            if not isinstance(claim, str) or not claim.strip():
                violations.append(f"claims[{idx}] must be a non-empty string")
            elif len(claim) > 10000:
                violations.append(f"claims[{idx}] exceeds 10000 character limit")
            else:
                # Security check for injection attacks
                for pat in _INJECTION_PATTERNS:
                    if pat.search(claim):
                        violations.append(
                            f"claims[{idx}] contains prohibited governance-override or prompt injection pattern: {pat.pattern}"
                        )
                        break

    # 6. Assumptions checks
    if not isinstance(proposal.assumptions, list):
        violations.append("assumptions must be a list")
    else:
        for idx, asm in enumerate(proposal.assumptions):
            if not isinstance(asm, str):
                violations.append(f"assumptions[{idx}] must be a string")
            else:
                for pat in _INJECTION_PATTERNS:
                    if pat.search(asm):
                        violations.append(
                            f"assumptions[{idx}] contains prohibited governance-override pattern: {pat.pattern}"
                        )
                        break

    # 7. Uncertainty bounds
    if not isinstance(proposal.uncertainty, (int, float)) or isinstance(proposal.uncertainty, bool):
        violations.append("uncertainty must be a numeric float")
    elif not 0.0 <= float(proposal.uncertainty) <= 1.0:
        violations.append(f"uncertainty must be between 0.0 and 1.0, got {proposal.uncertainty}")

    # 8. Proposed Action
    if not isinstance(proposal.proposed_action, ProposedAction):
        violations.append("proposed_action must be an instance of ProposedAction")
    else:
        if not proposal.proposed_action.action_type or not proposal.proposed_action.action_type.strip():
            violations.append("proposed_action.action_type cannot be empty")
        if not proposal.proposed_action.target_id or not proposal.proposed_action.target_id.strip():
            violations.append("proposed_action.target_id cannot be empty")

    # 9. Provenance Reference Requirement
    if not proposal.provenance_refs:
        violations.append("provenance_refs is required and cannot be empty; every proposal must have verifiable provenance")
    else:
        for idx, pref in enumerate(proposal.provenance_refs):
            if not isinstance(pref, ProvenanceRef):
                violations.append(f"provenance_refs[{idx}] is not a ProvenanceRef instance")
            else:
                if not pref.source_id or not pref.source_id.strip():
                    violations.append(f"provenance_refs[{idx}] has empty source_id")
                if not pref.evidence_id or not pref.evidence_id.strip():
                    violations.append(f"provenance_refs[{idx}] has empty evidence_id")
                if not pref.content_hash or len(pref.content_hash) != 64:
                    violations.append(f"provenance_refs[{idx}] has invalid SHA-256 content_hash")

    return violations


def assert_valid_proposal(proposal: Any) -> None:
    """Raises ProposalValidationError if any violations exist."""
    violations = validate_proposal(proposal)
    if violations:
        raise ProposalValidationError(violations)


__all__ = [
    "ProposalValidationError",
    "assert_valid_proposal",
    "validate_proposal",
]
