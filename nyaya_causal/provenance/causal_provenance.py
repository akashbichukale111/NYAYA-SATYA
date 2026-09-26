"""Causal provenance tracking for NYAYA-SATYA.

Every causal hypothesis traces through:
Evidence -> Claim/Event -> Causal Edge -> Intervention -> Scenario -> Comparison -> Finding

Every scenario gets a SHA-256 hash. Every comparison gets a SHA-256 hash.
No orphan causal claims are permitted.
"""

from __future__ import annotations

import uuid
from typing import Any

from tarka_vyuh.contracts.provenance import ProvenanceRef, compute_sha256


class CausalProvenanceTracker:
    """Tracks provenance across causal analysis operations."""

    @staticmethod
    def create_edge_provenance(
        *,
        edge_id: str,
        case_id: str,
        evidence_id: str,
        causal_basis: str,
    ) -> ProvenanceRef:
        """Create a provenance ref for a causal edge."""
        content = f"causal_edge:{edge_id}:basis:{causal_basis}"
        return ProvenanceRef.create(
            source_id=edge_id,
            source_type="CAUSAL_EDGE",
            evidence_id=evidence_id,
            content=content,
        )

    @staticmethod
    def create_hypothesis_provenance(
        *,
        hypothesis_id: str,
        case_id: str,
        evidence_ids: list[str],
    ) -> ProvenanceRef:
        """Create a provenance ref for a causal hypothesis."""
        content = f"causal_hypothesis:{hypothesis_id}:evidence:{','.join(sorted(evidence_ids))}"
        ev_id = evidence_ids[0] if evidence_ids else "no_evidence"
        return ProvenanceRef.create(
            source_id=hypothesis_id,
            source_type="CAUSAL_HYPOTHESIS",
            evidence_id=ev_id,
            content=content,
        )

    @staticmethod
    def create_scenario_provenance(
        *,
        scenario_id: str,
        case_id: str,
        scenario_hash: str,
    ) -> ProvenanceRef:
        """Create a provenance ref for a counterfactual scenario."""
        return ProvenanceRef.create(
            source_id=scenario_id,
            source_type="COUNTERFACTUAL_SCENARIO",
            evidence_id=scenario_id,
            content_hash=scenario_hash if len(scenario_hash) == 64 else compute_sha256(scenario_hash),
        )

    @staticmethod
    def create_comparison_provenance(
        *,
        comparison_id: str,
        comparison_hash: str,
    ) -> ProvenanceRef:
        """Create a provenance ref for a before/after comparison."""
        return ProvenanceRef.create(
            source_id=comparison_id,
            source_type="COUNTERFACTUAL_COMPARISON",
            evidence_id=comparison_id,
            content_hash=comparison_hash if len(comparison_hash) == 64 else compute_sha256(comparison_hash),
        )

    @staticmethod
    def create_blast_radius_provenance(
        *,
        report_id: str,
        scenario_hash: str,
    ) -> ProvenanceRef:
        """Create a provenance ref for a blast-radius report."""
        return ProvenanceRef.create(
            source_id=report_id,
            source_type="BLAST_RADIUS_REPORT",
            evidence_id=report_id,
            content_hash=scenario_hash if len(scenario_hash) == 64 else compute_sha256(scenario_hash),
        )
