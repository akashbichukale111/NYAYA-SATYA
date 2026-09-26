"""Evidence-grounded repair candidate generator for NYAYA-SATYA Auto-Healer.

Generates structured, traceable repair candidates addressing adversarial findings,
unsupported claims, timeline ambiguities, or provenance gaps.
Strictly prohibits free-form legal fabrication.
"""

from __future__ import annotations

import uuid
from typing import Any

from nyaya_adversarial.contracts.fragility import FragilityReport
from nyaya_adversarial.contracts.result import AdversarialFinding, FindingType
from nyaya_repair.contracts.repair import (
    AuthorityType,
    LegalAuthorityRef,
    LegalGroundingStatus,
)
from nyaya_repair.contracts.repair_candidate import (
    RepairCandidate,
    RepairCandidateStatus,
    RepairChangeType,
)
from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.contracts.claims import ClaimStatus
from tarka_vyuh.contracts.provenance import ProvenanceRef, compute_sha256


class RepairGenerator:
    """Generates traceable, evidence-grounded repair candidates."""

    def __init__(self, twin: CaseDigitalTwin) -> None:
        self._twin = twin
        self._case_id = twin.case_id

    def generate_repairs_for_finding(
        self,
        finding: AdversarialFinding,
        *,
        available_evidence_ids: list[str] | None = None,
    ) -> list[RepairCandidate]:
        """Generate repair candidates addressing a specific adversarial finding."""
        repairs: list[RepairCandidate] = []
        ftype = finding.finding_type
        target_id = finding.target_id
        original_hash = self._twin.integrity_hash

        if ftype == FindingType.UNSUPPORTED_CLAIM:
            # Check if there is an unattached clean evidence item that can support the claim
            claim = self._twin.claims.get(target_id)
            if claim:
                candidate_evidence = available_evidence_ids or list(self._twin.evidence_refs.keys())
                matching_ev = [
                    ev_id for ev_id in candidate_evidence
                    if ev_id not in claim.supporting_evidence_ids
                    and ev_id in self._twin.evidence_refs
                ]
                if matching_ev:
                    repairs.append(
                        RepairCandidate(
                            repair_id=f"REP_{uuid.uuid4().hex[:12]}",
                            case_id=self._case_id,
                            target_vulnerability_id=finding.finding_id,
                            target_claim_id=target_id,
                            change_type=RepairChangeType.ADD_EVIDENCE_REFERENCE,
                            proposed_change={
                                "claim_id": target_id,
                                "add_evidence_id": matching_ev[0],
                            },
                            original_state_hash=original_hash,
                            evidence_refs=[matching_ev[0]],
                            expected_effects=[f"Claim {target_id} substantiated by {matching_ev[0]}"],
                            rationale=f"Attach verified evidence {matching_ev[0]} to unsupported claim {target_id}",
                        )
                    )
                # Alternative repair: qualify the assertion if unsupported
                repairs.append(
                    RepairCandidate(
                        repair_id=f"REP_{uuid.uuid4().hex[:12]}",
                        case_id=self._case_id,
                        target_vulnerability_id=finding.finding_id,
                        target_claim_id=target_id,
                        change_type=RepairChangeType.QUALIFY_ASSERTION,
                        proposed_change={
                            "claim_id": target_id,
                            "qualified_status": ClaimStatus.UNRESOLVED.value,
                            "qualification_prefix": "Subject to independent verification: ",
                        },
                        original_state_hash=original_hash,
                        expected_effects=[f"Claim {target_id} marked as subject to verification"],
                        rationale=f"Qualify assertion on claim {target_id} to avoid unsupported overstatement",
                    )
                )

        elif ftype == FindingType.TIMELINE_CONFLICT:
            event = self._twin.events.get(target_id)
            if event:
                repairs.append(
                    RepairCandidate(
                        repair_id=f"REP_{uuid.uuid4().hex[:12]}",
                        case_id=self._case_id,
                        target_vulnerability_id=finding.finding_id,
                        change_type=RepairChangeType.CORRECT_TIMELINE_REFERENCE,
                        proposed_change={
                            "event_id": target_id,
                            "clarify_temporal_status": "APPROXIMATE",
                            "note": "Awaiting corroborating timestamp log",
                        },
                        original_state_hash=original_hash,
                        expected_effects=[f"Event {target_id} reconciled to approximate sequence"],
                        rationale=f"Correct timeline reference for event {target_id} to prevent false exactness",
                    )
                )

        elif ftype in (FindingType.SINGLE_SOURCE_DEPENDENCY, FindingType.FRAGILE_EVIDENCE):
            # Propose requesting corroborating evidence
            repairs.append(
                RepairCandidate(
                    repair_id=f"REP_{uuid.uuid4().hex[:12]}",
                    case_id=self._case_id,
                    target_vulnerability_id=finding.finding_id,
                    target_claim_id=finding.claim_ids[0] if finding.claim_ids else None,
                    change_type=RepairChangeType.REQUEST_MISSING_EVIDENCE,
                    proposed_change={
                        "target_node_id": target_id,
                        "request_type": "INDEPENDENT_CORROBORATION",
                        "description": f"Request third-party record corroborating {target_id}",
                    },
                    original_state_hash=original_hash,
                    expected_effects=[f"Formal evidence request issued for {target_id}"],
                    rationale=f"Mitigate single-source fragility on {target_id} by requesting corroboration",
                )
            )

        elif ftype == FindingType.PROVENANCE_GAP:
            repairs.append(
                RepairCandidate(
                    repair_id=f"REP_{uuid.uuid4().hex[:12]}",
                    case_id=self._case_id,
                    target_vulnerability_id=finding.finding_id,
                    change_type=RepairChangeType.ADD_PROVENANCE,
                    proposed_change={
                        "target_id": target_id,
                        "remediation": "ATTACH_HASH_VERIFIED_CUSTODY_RECORD",
                    },
                    original_state_hash=original_hash,
                    expected_effects=[f"Provenance audit chain attached for {target_id}"],
                    rationale=f"Attach verified chain-of-custody hash reference to {target_id}",
                )
            )

        elif ftype == FindingType.ASSUMPTION_EXPOSED:
            repairs.append(
                RepairCandidate(
                    repair_id=f"REP_{uuid.uuid4().hex[:12]}",
                    case_id=self._case_id,
                    target_vulnerability_id=finding.finding_id,
                    change_type=RepairChangeType.MARK_UNCERTAIN,
                    proposed_change={
                        "assumption_id": target_id,
                        "support_status": "EXPLICIT_UNPROVEN",
                    },
                    original_state_hash=original_hash,
                    expected_effects=[f"Assumption {target_id} explicitly isolated"],
                    rationale=f"Explicitly isolate exposed assumption {target_id} to avoid hidden reliance",
                )
            )

        return repairs

    def generate_all_repairs(
        self, findings: list[AdversarialFinding]
    ) -> list[RepairCandidate]:
        """Generate all repair candidates for a collection of adversarial findings."""
        all_repairs: list[RepairCandidate] = []
        for finding in findings:
            repairs = self.generate_repairs_for_finding(finding)
            all_repairs.extend(repairs)
        return all_repairs
