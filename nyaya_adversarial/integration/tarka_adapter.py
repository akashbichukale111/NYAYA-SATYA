"""TARKA-VYUH Adapter for NYAYA-SATYA Adversarial Subsystem.

Converts adversarial findings, conflict sets, and missing-evidence candidates
into TARKA-VYUH ReasoningProposals.
STRICT NON-ADJUDICATION: Proposals are strictly advisory and require Human Legal Gate approval.
"""

from __future__ import annotations

import uuid
from typing import Any

from nyaya_adversarial.contracts.conflict import EvidenceConflict
from nyaya_adversarial.contracts.missing_evidence import MissingEvidenceCandidate
from nyaya_adversarial.contracts.result import AdversarialFinding
from tarka_vyuh.contracts.proposal import (
    ProposalStatus,
    ProposedAction,
    ReasoningProposal,
    ReasoningType,
)
from tarka_vyuh.contracts.provenance import ProvenanceRef


class TarkaAdversarialAdapter:
    """Translates adversarial stress-test outputs into standard TARKA-VYUH ReasoningProposals."""

    def finding_to_proposal(self, finding: AdversarialFinding) -> ReasoningProposal:
        """Emits a ReasoningProposal for an adversarial finding."""
        action = ProposedAction(
            action_type="REVIEW_ADVERSARIAL_STRESS_POINT",
            target_id=finding.finding_id,
            parameters={
                "finding_type": finding.finding_type.value,
                "target_id": finding.target_id,
                "severity": finding.severity.value,
                "structural_impact": finding.structural_impact,
                "explanation": finding.explanation,
            },
            is_consequential=True,
        )

        prov = finding.provenance_refs[0] if finding.provenance_refs else ProvenanceRef.create(
            source_id=f"finding_{finding.finding_id}",
            source_type="ADVERSARIAL_FINDING",
            evidence_id=finding.target_id,
            content=finding.finding_id,
            extraction_metadata={"actor": "TARKA_GAUNTLET"},
        )

        return ReasoningProposal(
            proposal_id=f"prop_adv_{uuid.uuid4().hex[:12]}",
            case_id=finding.case_id,
            reasoning_type=ReasoningType.ADVERSARIAL_CHALLENGE,
            input_evidence_ids=finding.evidence_ids or [finding.target_id],
            claims=finding.claim_ids or [finding.target_id],
            assumptions=finding.assumptions,
            uncertainty=finding.uncertainty,
            proposed_action=action,
            provenance_refs=[prov],
            status=ProposalStatus.PROPOSED,
            model_metadata={"finding_id": finding.finding_id, "engine_version": finding.engine_version},
        )

    def conflict_to_proposal(self, conflict: EvidenceConflict) -> ReasoningProposal:
        """Emits a ReasoningProposal for an evidentiary conflict."""
        action = ProposedAction(
            action_type="FLAG_EVIDENCE_CONFLICT",
            target_id=conflict.conflict_id,
            parameters={
                "conflict_type": conflict.conflict_type.value,
                "evidence_a": conflict.evidence_a_id,
                "evidence_b": conflict.evidence_b_id,
                "description": conflict.description,
            },
            is_consequential=True,
        )

        prov = conflict.provenance_refs[0] if conflict.provenance_refs else ProvenanceRef.create(
            source_id=f"conflict_{conflict.conflict_id}",
            source_type="CONFLICT_ARENA",
            evidence_id=conflict.evidence_a_id,
            content=conflict.conflict_id,
            extraction_metadata={"actor": "TARKA_ARENA"},
        )

        return ReasoningProposal(
            proposal_id=f"prop_conf_{uuid.uuid4().hex[:12]}",
            case_id=conflict.case_id,
            reasoning_type=ReasoningType.EVIDENCE_CONFLICT,
            input_evidence_ids=[conflict.evidence_a_id, conflict.evidence_b_id],
            claims=conflict.claim_ids,
            assumptions=[],
            uncertainty=conflict.uncertainty,
            proposed_action=action,
            provenance_refs=[prov],
            status=ProposalStatus.PROPOSED,
            model_metadata={"conflict_id": conflict.conflict_id},
        )

    def missing_evidence_to_proposal(
        self,
        candidate: MissingEvidenceCandidate,
    ) -> ReasoningProposal:
        """Emits a ReasoningProposal for a missing evidence candidate."""
        action = ProposedAction(
            action_type="IDENTIFY_MISSING_EVIDENCE",
            target_id=candidate.candidate_id,
            parameters={
                "question": candidate.question,
                "expected_type": candidate.expected_evidence_type,
                "related_claims": candidate.related_claims,
                "access_constraint": candidate.access_constraint,
            },
            is_consequential=False,
        )

        prov = candidate.provenance[0] if candidate.provenance else ProvenanceRef.create(
            source_id=f"missing_{candidate.candidate_id}",
            source_type="MISSING_EVIDENCE_DETECTOR",
            evidence_id=candidate.candidate_id,
            content=candidate.candidate_id,
            extraction_metadata={"actor": "TARKA_VOI"},
        )

        return ReasoningProposal(
            proposal_id=f"prop_miss_{uuid.uuid4().hex[:12]}",
            case_id=candidate.case_id,
            reasoning_type=ReasoningType.MISSING_EVIDENCE,
            input_evidence_ids=[],
            claims=candidate.related_claims,
            assumptions=[],
            uncertainty=candidate.current_uncertainty,
            proposed_action=action,
            provenance_refs=[prov],
            status=ProposalStatus.PROPOSED,
            model_metadata={"candidate_id": candidate.candidate_id},
        )
