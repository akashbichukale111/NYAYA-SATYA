"""First Contradiction Analysis Foundation for TARKA-VYUH / NYAYA-SATYA.

Grounded in paired safe evidence references.
Distinguishes contradiction types (DIRECT_CONTRADICTION, TEMPORAL_CONFLICT,
NUMERIC_CONFLICT, IDENTITY_CONFLICT, LOCATION_CONFLICT, POSSIBLE_CONTRADICTION, UNRESOLVED).
Preserves uncertainty.
NEVER infers perjury, fraud, guilt, innocence, or legal outcomes.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from nyaya_evidence.tarka_integration.safe_refs import SafeEvidenceRef
from tarka_vyuh.contracts.proposal import (
    ProposalStatus,
    ProposedAction,
    ReasoningProposal,
    ReasoningType,
)
from tarka_vyuh.contracts.provenance import ProvenanceRef


class ContradictionType(str, Enum):
    DIRECT_CONTRADICTION = "DIRECT_CONTRADICTION"
    TEMPORAL_CONFLICT = "TEMPORAL_CONFLICT"
    NUMERIC_CONFLICT = "NUMERIC_CONFLICT"
    IDENTITY_CONFLICT = "IDENTITY_CONFLICT"
    LOCATION_CONFLICT = "LOCATION_CONFLICT"
    POSSIBLE_CONTRADICTION = "POSSIBLE_CONTRADICTION"
    UNRESOLVED = "UNRESOLVED"


@dataclass
class ContradictionCandidate:
    contradiction_id: str
    case_id: str
    evidence_a_id: str
    evidence_b_id: str
    claim_a: str
    claim_b: str
    contradiction_type: ContradictionType
    supporting_spans: list[str]
    provenance_refs: list[ProvenanceRef]
    confidence: float  # [0.0, 1.0]
    uncertainty: float  # [0.0, 1.0]
    status: str = "PROPOSED_FOR_REVIEW"
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["contradiction_type"] = self.contradiction_type.value
        data["detected_at"] = self.detected_at.isoformat()
        data["provenance_refs"] = [p.to_dict() for p in self.provenance_refs]
        return data


class ContradictionAnalysisEngine:
    """Deterministic, evidence-grounded baseline contradiction analyzer."""

    def analyze_pair(
        self,
        ref_a: SafeEvidenceRef,
        ref_b: SafeEvidenceRef,
    ) -> list[ContradictionCandidate]:
        """Compares two safe evidence references and detects contradiction candidates."""
        candidates: list[ContradictionCandidate] = []

        if ref_a.evidence_id == ref_b.evidence_id:
            return []  # Cannot contradict self

        text_a = ref_a.sanitized_text
        text_b = ref_b.sanitized_text

        combined_provs = list(ref_a.provenance_refs) + list(ref_b.provenance_refs)

        # 1. Numeric conflict analysis: e.g. "delivery in X days" vs "delivery in Y days"
        num_pattern = re.compile(r"(\b\w+\b)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(days?|hours?|weeks?|months?|usd|eur|dollars?)?", re.IGNORECASE)
        nums_a = {m.group(1).lower(): (float(m.group(2)), m.group(3) or "") for m in num_pattern.finditer(text_a)}
        nums_b = {m.group(1).lower(): (float(m.group(2)), m.group(3) or "") for m in num_pattern.finditer(text_b)}

        common_keys = set(nums_a.keys()) & set(nums_b.keys())
        for k in common_keys:
            val_a, unit_a = nums_a[k]
            val_b, unit_b = nums_b[k]
            if val_a != val_b:
                cid = f"cand_num_{uuid.uuid4().hex[:12]}"
                candidates.append(
                    ContradictionCandidate(
                        contradiction_id=cid,
                        case_id=ref_a.case_id,
                        evidence_a_id=ref_a.evidence_id,
                        evidence_b_id=ref_b.evidence_id,
                        claim_a=f"{k}: {val_a} {unit_a}".strip(),
                        claim_b=f"{k}: {val_b} {unit_b}".strip(),
                        contradiction_type=ContradictionType.NUMERIC_CONFLICT,
                        supporting_spans=[
                            f"[{ref_a.evidence_id}] asserts {k} is {val_a} {unit_a}".strip(),
                            f"[{ref_b.evidence_id}] asserts {k} is {val_b} {unit_b}".strip(),
                        ],
                        provenance_refs=combined_provs,
                        confidence=0.85,
                        uncertainty=0.15,
                    )
                )

        # 2. Direct contradiction: affirmative vs negative statements
        # E.g. "Goods were delivered" vs "Goods were not delivered" / "never received"
        direct_pairs = [
            (re.compile(r"\b(?:(?:was|were|has\s+been|is)\s+)?(delivered|received|paid|signed|executed)\b", re.IGNORECASE),
             re.compile(r"\b(?:(?:was\s+not|were\s+not|never|has\s+not\s+been|not)\s+)?(undelivered|unreceived|unpaid|unsigned|unexecuted)|(?:\b(?:was\s+not|were\s+not|never|has\s+not\s+been|not)\s+(?:delivered|received|paid|signed|executed))\b", re.IGNORECASE)),
            (re.compile(r"\b(approved|consented|agreed)\b", re.IGNORECASE),
             re.compile(r"\b(rejected|disapproved|disagreed|refused)\b", re.IGNORECASE)),
        ]

        for pos_pat, neg_pat in direct_pairs:
            match_a_pos = pos_pat.search(text_a)
            match_b_neg = neg_pat.search(text_b)
            match_b_pos = pos_pat.search(text_b)
            match_a_neg = neg_pat.search(text_a)

            if (match_a_pos and match_b_neg) or (match_b_pos and match_a_neg):
                cid = f"cand_dir_{uuid.uuid4().hex[:12]}"
                span_a = match_a_pos.group(0) if match_a_pos else match_a_neg.group(0)  # type: ignore
                span_b = match_b_neg.group(0) if match_b_neg else match_b_pos.group(0)  # type: ignore

                candidates.append(
                    ContradictionCandidate(
                        contradiction_id=cid,
                        case_id=ref_a.case_id,
                        evidence_a_id=ref_a.evidence_id,
                        evidence_b_id=ref_b.evidence_id,
                        claim_a=f"Asserts: {span_a}",
                        claim_b=f"Asserts: {span_b}",
                        contradiction_type=ContradictionType.DIRECT_CONTRADICTION,
                        supporting_spans=[
                            f"[{ref_a.evidence_id}]: ...{span_a}...",
                            f"[{ref_b.evidence_id}]: ...{span_b}...",
                        ],
                        provenance_refs=combined_provs,
                        confidence=0.80,
                        uncertainty=0.20,
                    )
                )

        return candidates

    def to_reasoning_proposal(
        self,
        candidate: ContradictionCandidate,
    ) -> ReasoningProposal:
        """Converts a detected contradiction candidate into a TARKA-VYUH ReasoningProposal."""
        action = ProposedAction(
            action_type="FLAG_EVIDENCE_CONTRADICTION",
            target_id=candidate.contradiction_id,
            parameters={
                "evidence_a_id": candidate.evidence_a_id,
                "evidence_b_id": candidate.evidence_b_id,
                "contradiction_type": candidate.contradiction_type.value,
                "confidence": candidate.confidence,
            },
            is_consequential=True,
        )

        claims = [
            f"Contradiction identified ({candidate.contradiction_type.value}) between {candidate.evidence_a_id} and {candidate.evidence_b_id}",
            f"Claim A: {candidate.claim_a}",
            f"Claim B: {candidate.claim_b}",
        ]

        return ReasoningProposal(
            proposal_id=f"prop_contra_{uuid.uuid4().hex[:12]}",
            case_id=candidate.case_id,
            reasoning_type=ReasoningType.CONTRADICTION_ANALYSIS,
            input_evidence_ids=[candidate.evidence_a_id, candidate.evidence_b_id],
            claims=claims,
            assumptions=["Documents originate from separate custodians without unified reconciliation"],
            uncertainty=candidate.uncertainty,
            proposed_action=action,
            provenance_refs=candidate.provenance_refs,
            generated_at=datetime.now(UTC),
            model_metadata={"engine": "ContradictionAnalysisEngine@1.0.0"},
            status=ProposalStatus.PROPOSED,
        )


__all__ = [
    "ContradictionAnalysisEngine",
    "ContradictionCandidate",
    "ContradictionType",
]
