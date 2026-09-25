"""Evidence Foundation Adapter for NYAYA-SATYA Case Digital Twin.

Bridges Phase 2 EvidenceRegistry and SafeEvidenceRef into the Case Digital Twin.
Guarantees quarantined, malicious, or unverified evidence cannot enter the twin.
"""

from __future__ import annotations

from nyaya_evidence.contracts.evidence import EvidenceItem, EvidenceStatus
from nyaya_evidence.quarantine.manager import QuarantineViolationError
from nyaya_evidence.tarka_integration.safe_refs import SafeEvidenceRef
from nyaya_twin.builders.twin_builder import CaseTwinBuilder


class CaseTwinEvidenceAdapter:
    """Adapter bridging Phase 2 safe evidence references into Phase 3 Case Digital Twin."""

    @staticmethod
    def attach_safe_evidence(
        builder: CaseTwinBuilder,
        safe_ref: SafeEvidenceRef,
        item: EvidenceItem,
    ) -> None:
        """Attaches a SafeEvidenceRef to the twin builder after verifying quarantine clearance."""
        if not item.is_safe_for_reasoning:
            raise QuarantineViolationError(
                f"Quarantine violation: evidence {item.evidence_id} is in status {item.status.value}. "
                "Only REGISTERED or PARSED evidence may enter the Case Digital Twin."
            )

        if safe_ref.case_id != builder.case_id:
            raise ValueError(
                f"Cross-case contamination: evidence {safe_ref.evidence_id} belongs to {safe_ref.case_id}, "
                f"cannot attach to twin for {builder.case_id}"
            )

        builder.add_evidence_ref(safe_ref)
