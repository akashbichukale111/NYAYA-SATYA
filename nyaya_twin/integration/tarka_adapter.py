"""TARKA-VYUH Adapter for NYAYA-SATYA Case Digital Twin.

Exposes structured, sanitized views of the Case Digital Twin to TARKA-VYUH reasoning engines.
Strictly blocks raw quarantined byte access.
Ensures unbuilt reasoning capabilities remain NOT_IMPLEMENTED.
"""

from __future__ import annotations

from typing import Any

from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from tarka_vyuh.contracts.proposal import ReasoningProposal, ReasoningType
from tarka_vyuh.reasoning.registry import (
    CapabilityStatus,
    ReasoningEngineNotImplementedError,
    get_capability,
)


class CaseTwinTarkaAdapter:
    """Adapter providing structured twin context to TARKA-VYUH reasoning engines."""

    @staticmethod
    def extract_reasoning_context(twin: CaseDigitalTwin) -> dict[str, Any]:
        """Extracts sanitized claims, evidence links, and timeline for TARKA-VYUH."""
        return {
            "case_id": twin.case_id,
            "twin_id": twin.twin_id,
            "version": twin.version,
            "claims": [c.to_dict() for c in twin.claims.values()],
            "events": [e.to_dict() for e in twin.events.values()],
            "contradictions": [cand.to_dict() for cand in twin.contradictions],
            "temporal_conflicts": twin.temporal_conflicts,
            "unresolved_items": list(twin.unresolved_items),
            "evidence_summaries": {
                ref.evidence_id: {
                    "content_hash": ref.content_hash,
                    "sanitized_hash": ref.sanitized_hash,
                    "risk_level": ref.risk_level.value,
                }
                for ref in twin.evidence_refs.values()
            },
        }

    @staticmethod
    def verify_capability_available(reasoning_type: ReasoningType) -> None:
        """Verifies if the reasoning capability is implemented or raises NOT_IMPLEMENTED."""
        cap = get_capability(reasoning_type)
        if cap.status is CapabilityStatus.NOT_IMPLEMENTED:
            raise ReasoningEngineNotImplementedError(
                f"Reasoning capability {reasoning_type.value} is NOT_IMPLEMENTED in Phase 3. "
                "Fake or fabricated reasoning results are prohibited."
            )
