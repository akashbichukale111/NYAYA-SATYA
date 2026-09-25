"""Provenance Integrity Validator for NYAYA-SATYA Case Digital Twin.

Enforces unbroken cryptographic and lineage tracking:
SOURCE -> EVIDENCE -> QUARANTINE -> SANITIZATION -> SAFE EVIDENCE REF -> CLAIM -> ISSUE -> REASONING
"""

from __future__ import annotations

import re
from typing import Any

from nyaya_twin.contracts.claims import Claim
from tarka_vyuh.contracts.provenance import ProvenanceRef


class ProvenanceIntegrityError(ValueError):
    """Raised when provenance lineage is violated or missing."""


def validate_provenance_chain(
    claim: Claim,
    safe_evidence_hashes: dict[str, str],
) -> list[str]:
    """Verifies that claim provenance references correspond to registered SafeEvidenceRef hashes.

    Returns a list of provenance violation descriptions.
    """
    violations: list[str] = []

    if not claim.provenance_refs:
        violations.append(f"Claim {claim.claim_id} lacks any provenance references")
        return violations

    for prov in claim.provenance_refs:
        if not prov.ref_id or not prov.source_id:
            violations.append(f"Provenance reference {prov.ref_id} in claim {claim.claim_id} has blank source_id")
            continue

        if not prov.content_hash or len(prov.content_hash) != 64 or not re.fullmatch(r"^[0-9a-fA-F]{64}$", prov.content_hash):
            violations.append(
                f"Provenance reference {prov.ref_id} in claim {claim.claim_id} has invalid SHA-256 hash: {prov.content_hash!r}"
            )
            continue

        # If it points to an evidence_id, check hash match
        if prov.evidence_id and prov.evidence_id in safe_evidence_hashes:
            expected_hash = safe_evidence_hashes[prov.evidence_id]
            if prov.content_hash.lower() != expected_hash.lower():
                violations.append(
                    f"Cryptographic divergence in claim {claim.claim_id}: provenance hash {prov.content_hash} "
                    f"does not match registered safe evidence hash {expected_hash}"
                )

    return violations
