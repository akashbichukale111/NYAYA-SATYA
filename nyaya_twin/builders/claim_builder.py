"""Claim Builder for NYAYA-SATYA Case Digital Twin.

Constructs structured claims and computes initial evidence support states.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from nyaya_twin.contracts.claims import Claim, ClaimStatus, ClaimType
from nyaya_twin.contracts.confidence import assess_claim_confidence
from tarka_vyuh.contracts.provenance import ProvenanceRef


class ClaimBuilder:
    """Builder for structuring and registering claims."""

    def __init__(self, case_id: str) -> None:
        self.case_id = case_id
        self._claims: dict[str, Claim] = {}

    def add_claim(
        self,
        *,
        subject_entity_id: str,
        predicate: str,
        object_value: str,
        claim_id: str | None = None,
        claim_type: ClaimType = ClaimType.FACTUAL,
        source_evidence_ids: list[str] | None = None,
        supporting_evidence_ids: list[str] | None = None,
        contradicting_evidence_ids: list[str] | None = None,
        provenance_refs: list[ProvenanceRef] | None = None,
        created_from: str = "MANUAL_ENTRY",
        notes: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Claim:
        if claim_id is None:
            clean_sub = re.sub(r"[^a-zA-Z0-9]+", "_", subject_entity_id.strip()).strip("_").lower()
            claim_id = f"clm_{clean_sub}_{uuid.uuid4().hex[:6]}"

        sup = list(supporting_evidence_ids or [])
        contra = list(contradicting_evidence_ids or [])
        src = list(source_evidence_ids or [])
        prov = list(provenance_refs or [])

        # Assess confidence explainably
        conf_assessment = assess_claim_confidence(
            supporting_count=len(sup),
            contradicting_count=len(contra),
            has_primary_evidence=bool(src),
            has_unbroken_provenance=bool(prov),
        )

        claim = Claim(
            claim_id=claim_id,
            case_id=self.case_id,
            subject_entity_id=subject_entity_id,
            predicate=predicate.strip(),
            object_value=object_value.strip(),
            claim_type=claim_type,
            source_evidence_ids=src,
            supporting_evidence_ids=sup,
            contradicting_evidence_ids=contra,
            provenance_refs=prov,
            confidence=conf_assessment.level,
            status=ClaimStatus.PENDING_REVIEW,
            created_from=created_from,
            notes=notes,
            metadata=dict(metadata or {}),
        )
        # Evaluate evidence status
        claim.status = claim.evaluate_evidence_status()

        self._claims[claim.claim_id] = claim
        return claim

    def get_claims(self) -> dict[str, Claim]:
        return dict(self._claims)
