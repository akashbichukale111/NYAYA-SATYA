"""Legal grounding validation for NYAYA-SATYA Auto-Healer.

Ensures that authority references are distinguished strictly between verified
and unverified authorities. Prohibits automatic authority verification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nyaya_repair.contracts.repair import (
    LegalAuthorityRef,
    LegalGrounding,
    LegalGroundingStatus,
)
from nyaya_repair.contracts.repair_candidate import RepairCandidate


@dataclass
class AuthorityValidationResult:
    """Outcome of validating authority references in a repair."""

    is_valid: bool = True
    grounding_status: LegalGroundingStatus = LegalGroundingStatus.AUTHORITY_UNVERIFIED
    verified_authorities: list[str] = field(default_factory=list)
    unverified_authorities: list[str] = field(default_factory=list)
    missing_authorities: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "grounding_status": self.grounding_status.value,
            "verified_authorities": list(self.verified_authorities),
            "unverified_authorities": list(self.unverified_authorities),
            "missing_authorities": list(self.missing_authorities),
            "warnings": list(self.warnings),
        }


class LegalGroundingValidator:
    """Validates authority citations cited by a repair."""

    def validate_authorities(
        self,
        repair: RepairCandidate,
    ) -> AuthorityValidationResult:
        """Validate legal authorities cited in repair candidate."""
        result = AuthorityValidationResult()

        if not repair.authority_refs:
            result.grounding_status = LegalGroundingStatus.AUTHORITY_MISSING
            result.warnings.append("No legal authority cited for repair proposal")
            return result

        for auth in repair.authority_refs:
            # Prohibit unverified citations from claiming verified status without external verification source
            if auth.status == LegalGroundingStatus.VERIFIED_AUTHORITY:
                if not auth.verification_source:
                    result.unverified_authorities.append(auth.authority_id)
                    result.warnings.append(
                        f"Authority '{auth.citation}' claimed VERIFIED without external verification source. "
                        "Downgraded to AUTHORITY_UNVERIFIED."
                    )
                else:
                    result.verified_authorities.append(auth.authority_id)
            else:
                result.unverified_authorities.append(auth.authority_id)

        if result.verified_authorities and not result.unverified_authorities:
            result.grounding_status = LegalGroundingStatus.VERIFIED_AUTHORITY
        elif result.verified_authorities and result.unverified_authorities:
            result.grounding_status = LegalGroundingStatus.AUTHORITY_REFERENCE_PRESENT
        elif result.unverified_authorities:
            result.grounding_status = LegalGroundingStatus.AUTHORITY_UNVERIFIED
        else:
            result.grounding_status = LegalGroundingStatus.AUTHORITY_MISSING

        return result
