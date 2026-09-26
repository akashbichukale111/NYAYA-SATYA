"""Provenance tracking for NYAYA-SATYA Auto-Healer repairs.

Generates deterministic cryptographic hashes and ProvenanceRef records
for repair candidates, simulated states, and utility evaluations.
"""

from __future__ import annotations

import json
from typing import Any

from nyaya_repair.contracts.repair_candidate import RepairCandidate
from tarka_vyuh.contracts.provenance import ProvenanceRef, compute_sha256


class RepairProvenanceTracker:
    """Manages cryptographic provenance for repair proposals and outcomes."""

    @staticmethod
    def create_repair_provenance(repair: RepairCandidate) -> ProvenanceRef:
        """Generate a ProvenanceRef for a repair candidate."""
        return ProvenanceRef.create(
            source_id=repair.repair_id,
            source_type="REPAIR_CANDIDATE",
            evidence_id=repair.evidence_refs[0] if repair.evidence_refs else repair.repair_id,
            content_hash=repair.fingerprint,
            extraction_metadata={
                "change_type": repair.change_type.value,
                "target_vulnerability": repair.target_vulnerability_id,
                "target_claim": repair.target_claim_id,
            },
        )

    @staticmethod
    def create_simulation_provenance(
        repair_id: str,
        pre_hash: str,
        post_hash: str,
    ) -> ProvenanceRef:
        """Generate a ProvenanceRef for a repair simulation run."""
        payload = f"sim:{repair_id}:{pre_hash}:{post_hash}"
        return ProvenanceRef.create(
            source_id=f"SIM_{repair_id}",
            source_type="REPAIR_SIMULATION",
            evidence_id=repair_id,
            content=payload,
        )

    @staticmethod
    def compute_dossier_fingerprint(dossier_data: dict[str, Any]) -> str:
        """Compute deterministic SHA-256 hash for a judicial review dossier."""
        dumped = json.dumps(dossier_data, sort_keys=True, separators=(",", ":"))
        return compute_sha256(dumped)
